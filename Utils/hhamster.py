import requests
import time
from typing import List, Optional
import sqlite3
from datetime import datetime

def get_hr_vacancies_hh(region_id: Optional[int] = None, max_pages: int = 10) -> List[str]:
    """
    Получает список ссылок на вакансии в разделе 'Управление персоналом' с hh.ru

    Args:
        region_id: ID региона (по умолчанию Россия - 113)

        Россия 113
        Москва	1
        Санкт-Петербург	2
        Новосибирск	4
        Екатеринбург	3
        Казань	88
        Нижний Новгород	66
        Челябинск	104
        Красноярск	54
        Самара	78
        Уфа	99
        Ростов-на-Дону	76
        Краснодар	53
        Пермь	72
        Воронеж	26
        Волгоград	24

        max_pages: Максимальное количество страниц для парсинга

    Returns:
        List[str]: Список URL вакансий
    """

    # ID категории "Управление персоналом" на hh.ru
    hr_category_id = "118"

    # Регион по умолчанию - Россия
    if region_id is None:
        region_id = 113  # Россия

    vacancies_links = []
    base_url = "https://api.hh.ru/vacancies"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for page in range(max_pages):
        params = {
            "professional_role": hr_category_id,
            "area": region_id,
            "page": page,
            "per_page": 100,  # Максимальное количество вакансий на странице
            "only_with_salary": False
        }

        try:
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            vacancies = data.get("items", [])

            if not vacancies:
                break  # Больше нет вакансий

            # Собираем ссылки на вакансии
            for vacancy in vacancies:
                vacancy_url = vacancy.get("alternate_url")
                if vacancy_url:
                    vacancies_links.append(vacancy_url)

            print(f"Обработано страница {page + 1}, найдено вакансий: {len(vacancies)}")

            # Проверяем, есть ли следующая страница
            pages = data.get("pages", 0)
            if page >= pages - 1:
                break

            # Задержка чтобы не перегружать сервер
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе: {e}")
            break

    return vacancies_links


def create_vacancies_table(db_path: str = "vacancies.db") -> None:
    """
    Создает таблицу для хранения вакансий в базе данных.

    Args:
        db_path: Путь к файлу базы данных
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vacancy_url TEXT NOT NULL,
            region INTEGER NOT NULL,
            added TIMESTAMP NOT NULL,
            last_updated TIMESTAMP,
            UNIQUE(vacancy_url, region)
        )
    ''')

    conn.commit()
    conn.close()


def process_million_cities_vacancies(db_path: str = "vacancies.db", max_pages: int = 10) -> None:
    """
    Получает вакансии для всех городов-миллионников и сохраняет в базу данных.

    Args:
        db_path: Путь к файлу базы данных
        max_pages: Максимальное количество страниц для парсинга
    """
    # Словарь с кодами регионов городов-миллионников
    million_cities = {
        1: "Москва",
        2: "Санкт-Петербург",
        4: "Новосибирск",
        3: "Екатеринбург",
        88: "Казань",
        66: "Нижний Новгород",
        104: "Челябинск",
        54: "Красноярск",
        78: "Самара",
        99: "Уфа",
        76: "Ростов-на-Дону",
        53: "Краснодар",
        72: "Пермь",
        26: "Воронеж",
        24: "Волгоград"
    }

    # Создаем таблицу если она не существует
    create_vacancies_table(db_path)

    current_timestamp = datetime.now()

    for region_id, city_name in million_cities.items():
        print(f"Обрабатываю вакансии для {city_name} (регион {region_id})...")

        try:
            # Получаем вакансии для текущего региона
            vacancies = get_hr_vacancies_hh(region_id=region_id, max_pages=max_pages)
            print(f"Найдено {len(vacancies)} вакансий")

            # Сохраняем вакансии в базу
            save_vacancies_to_db(vacancies, region_id, db_path, current_timestamp)

        except Exception as e:
            print(f"Ошибка при обработке региона {region_id} ({city_name}): {e}")
            continue


def save_vacancies_to_db(vacancies: List[str], region_id: int, db_path: str, timestamp: datetime) -> None:
    """
    Сохраняет список вакансий в базу данных с обработкой дубликатов.

    Args:
        vacancies: Список ссылок на вакансии
        region_id: Код региона вакансий
        db_path: Путь к файлу базы данных
        timestamp: Временная метка для добавления/обновления
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for vacancy_url in vacancies:
        # Проверяем, существует ли уже такая ссылка в базе
        cursor.execute('''
            SELECT region FROM vacancies WHERE vacancy_url = ?
        ''', (vacancy_url,))

        existing_record = cursor.fetchone()

        if existing_record is None:
            # Новая вакансия - добавляем
            cursor.execute('''
                INSERT INTO vacancies (vacancy_url, region, added, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (vacancy_url, region_id, timestamp, timestamp))

        else:
            existing_region = existing_record[0]

            if existing_region == region_id:
                # Та же ссылка, тот же регион - обновляем last_updated
                cursor.execute('''
                    UPDATE vacancies 
                    SET last_updated = ? 
                    WHERE vacancy_url = ? AND region = ?
                ''', (timestamp, vacancy_url, region_id))

            elif existing_region != 999:
                # Та же ссылка, другой регион (и не 999) - меняем регион на 999
                cursor.execute('''
                    UPDATE vacancies 
                    SET region = ?, last_updated = ? 
                    WHERE vacancy_url = ? AND region != 999
                ''', (999, timestamp, vacancy_url))

    conn.commit()
    conn.close()