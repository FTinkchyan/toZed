# app.py
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import requests
import time
import json
from typing import List, Optional, Dict, Any

app = Flask(__name__)

# Конфигурация
DATABASE = "vacancies.db"

# Словарь с кодами регионов городов-миллионников
MILLION_CITIES = {
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
    24: "Волгоград",
    999: "Несколько регионов"
}


def get_hr_vacancies_hh(region_id: Optional[int] = None, max_pages: int = 15) -> List[Dict[str, Any]]:
    """
    Получает список вакансий в разделе 'Управление персоналом' с hh.ru
    Возвращает список словарей с полной информацией о вакансиях
    """
    hr_category_id = "118"

    if region_id is None:
        region_id = 113  # Россия

    vacancies_data = []
    base_url = "https://api.hh.ru/vacancies"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    for page in range(max_pages):
        params = {
            "professional_role": hr_category_id,
            "area": region_id,
            "page": page,
            "per_page": 100,
            "only_with_salary": False
        }

        try:
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()

            data = response.json()
            vacancies = data.get("items", [])

            if not vacancies:
                break

            for vacancy in vacancies:
                # Сохраняем полную информацию о вакансии
                vacancy_info = {
                    "id": vacancy.get("id"),
                    "name": vacancy.get("name"),
                    "url": vacancy.get("alternate_url"),
                    "salary": vacancy.get("salary"),
                    "employer": vacancy.get("employer"),
                    "snippet": vacancy.get("snippet"),
                    "experience": vacancy.get("experience"),
                    "employment": vacancy.get("employment"),
                    "schedule": vacancy.get("schedule"),
                    "professional_roles": vacancy.get("professional_roles"),
                    "published_at": vacancy.get("published_at"),
                    "created_at": vacancy.get("created_at"),
                    "archived": vacancy.get("archived"),
                    "response_url": vacancy.get("response_url"),
                    "contacts": vacancy.get("contacts")
                }
                vacancies_data.append(vacancy_info)

            print(f"Обработано страница {page + 1}, найдено вакансий: {len(vacancies)}")

            pages = data.get("pages", 0)
            if page >= pages - 1:
                break

            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе: {e}")
            break

    return vacancies_data


def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Таблица с основной информацией о вакансиях
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

    # Таблица с полной информацией о вакансиях
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS VacFull (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vacancy_id TEXT NOT NULL UNIQUE,
            vacancy_url TEXT NOT NULL,
            name TEXT,
            salary_data TEXT,
            employer_data TEXT,
            snippet_data TEXT,
            experience_data TEXT,
            employment_data TEXT,
            schedule_data TEXT,
            professional_roles_data TEXT,
            published_at TEXT,
            created_at TEXT,
            archived BOOLEAN,
            response_url TEXT,
            contacts_data TEXT,
            full_data TEXT,
            last_updated TIMESTAMP
        )
    ''')

    cursor.execute('PRAGMA synchronous = NORMAL;')
    cursor.execute('PRAGMA journal_mode = WAL;')
    cursor.execute('PRAGMA cache_size = 10000;')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_region ON vacancies(region)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vacancies_last_updated ON vacancies(last_updated)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vacfull_vacancy_id ON VacFull(vacancy_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_vacfull_vacancy_url ON VacFull(vacancy_url)')

    conn.commit()
    conn.close()


def save_vacancies_to_db(vacancies: List[Dict[str, Any]], region_id: int, timestamp: datetime) -> None:
    """Сохраняет вакансии в базу данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    for vacancy_info in vacancies:
        vacancy_url = vacancy_info.get("url")

        # Сохраняем в основную таблицу
        cursor.execute('SELECT region FROM vacancies WHERE vacancy_url = ?', (vacancy_url,))
        existing_record = cursor.fetchone()

        if existing_record is None:
            cursor.execute('''
                INSERT INTO vacancies (vacancy_url, region, added, last_updated)
                VALUES (?, ?, ?, ?)
            ''', (vacancy_url, region_id, timestamp, timestamp))
        else:
            existing_region = existing_record[0]
            if existing_region == region_id:
                cursor.execute('''
                    UPDATE vacancies 
                    SET last_updated = ? 
                    WHERE vacancy_url = ? AND region = ?
                ''', (timestamp, vacancy_url, region_id))
            elif existing_region != 999:
                cursor.execute('''
                    UPDATE vacancies 
                    SET region = ?, last_updated = ? 
                    WHERE vacancy_url = ? AND region != 999
                ''', (999, timestamp, vacancy_url))

        # Сохраняем в таблицу VacFull
        vacancy_id = vacancy_info.get("id")

        # Преобразуем сложные объекты в JSON строки
        salary_data = json.dumps(vacancy_info.get("salary"), ensure_ascii=False) if vacancy_info.get("salary") else None
        employer_data = json.dumps(vacancy_info.get("employer"), ensure_ascii=False) if vacancy_info.get(
            "employer") else None
        snippet_data = json.dumps(vacancy_info.get("snippet"), ensure_ascii=False) if vacancy_info.get(
            "snippet") else None
        experience_data = json.dumps(vacancy_info.get("experience"), ensure_ascii=False) if vacancy_info.get(
            "experience") else None
        employment_data = json.dumps(vacancy_info.get("employment"), ensure_ascii=False) if vacancy_info.get(
            "employment") else None
        schedule_data = json.dumps(vacancy_info.get("schedule"), ensure_ascii=False) if vacancy_info.get(
            "schedule") else None
        professional_roles_data = json.dumps(vacancy_info.get("professional_roles"),
                                             ensure_ascii=False) if vacancy_info.get("professional_roles") else None
        contacts_data = json.dumps(vacancy_info.get("contacts"), ensure_ascii=False) if vacancy_info.get(
            "contacts") else None
        full_data = json.dumps(vacancy_info, ensure_ascii=False)

        cursor.execute('''
            INSERT OR REPLACE INTO VacFull 
            (vacancy_id, vacancy_url, name, salary_data, employer_data, snippet_data, 
             experience_data, employment_data, schedule_data, professional_roles_data,
             published_at, created_at, archived, response_url, contacts_data, full_data, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            vacancy_id, vacancy_url, vacancy_info.get("name"),
            salary_data, employer_data, snippet_data,
            experience_data, employment_data, schedule_data, professional_roles_data,
            vacancy_info.get("published_at"), vacancy_info.get("created_at"),
            vacancy_info.get("archived"), vacancy_info.get("response_url"),
            contacts_data, full_data, timestamp
        ))

    conn.commit()
    conn.close()


@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', regions=MILLION_CITIES)


@app.route('/vacancies')
def vacancies():
    """Страница со списком вакансий"""
    region_id = request.args.get('region', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 500

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Получаем общее количество вакансий
    if region_id:
        cursor.execute('SELECT COUNT(*) FROM vacancies WHERE region = ?', (region_id,))
    else:
        cursor.execute('SELECT COUNT(*) FROM vacancies')

    total_vacancies = cursor.fetchone()[0]

    # Получаем вакансии для текущей страницы с информацией из VacFull
    offset = (page - 1) * per_page
    if region_id:
        cursor.execute('''
            SELECT v.id, v.vacancy_url, v.region, v.added, v.last_updated, 
                   vf.name, vf.vacancy_id
            FROM vacancies v
            LEFT JOIN VacFull vf ON v.vacancy_url = vf.vacancy_url
            WHERE v.region = ?
            ORDER BY v.last_updated DESC
            LIMIT ? OFFSET ?
        ''', (region_id, per_page, offset))
    else:
        cursor.execute('''
            SELECT v.id, v.vacancy_url, v.region, v.added, v.last_updated, 
                   vf.name, vf.vacancy_id
            FROM vacancies v
            LEFT JOIN VacFull vf ON v.vacancy_url = vf.vacancy_url
            ORDER BY v.last_updated DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))

    vacancies_data = cursor.fetchall()
    conn.close()

    # Преобразуем данные в удобный формат
    vacancies_list = []
    for vac in vacancies_data:
        vacancies_list.append({
            'id': vac[0],
            'url': vac[1],
            'region': MILLION_CITIES.get(vac[2], f"Регион {vac[2]}"),
            'region_id': vac[2],
            'added': vac[3],
            'updated': vac[4],
            'name': vac[5] or 'Название не указано',
            'vacancy_id': vac[6]
        })

    total_pages = (total_vacancies + per_page - 1) // per_page

    return render_template('vacancies.html',
                           min=min,
                           max=max,
                           vacancies=vacancies_list,
                           regions=MILLION_CITIES,
                           current_region=region_id,
                           current_page=page,
                           total_pages=total_pages)


@app.route('/vacancy/<vacancy_id>')
def vacancy_detail(vacancy_id):
    """Страница с подробной информацией о вакансии"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM VacFull WHERE vacancy_id = ?
    ''', (vacancy_id,))

    vacancy_data = cursor.fetchone()
    conn.close()

    if not vacancy_data:
        return render_template('404.html'), 404

    # Преобразуем JSON строки обратно в объекты
    columns = [description[0] for description in cursor.description]
    vacancy_dict = dict(zip(columns, vacancy_data))

    # Парсим JSON данные
    json_fields = ['salary_data', 'employer_data', 'snippet_data', 'experience_data',
                   'employment_data', 'schedule_data', 'professional_roles_data', 'contacts_data']

    for field in json_fields:
        if vacancy_dict[field]:
            vacancy_dict[field] = json.loads(vacancy_dict[field])

    return render_template('vacancy_detail.html', vacancy=vacancy_dict)


@app.route('/stats')
def stats():
    """Страница со статистикой"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Статистика по регионам
    cursor.execute('''
        SELECT region, COUNT(*) as count 
        FROM vacancies 
        GROUP BY region 
        ORDER BY count DESC
    ''')

    stats_data = cursor.fetchall()

    # Общее количество вакансий
    cursor.execute('SELECT COUNT(*) FROM vacancies')
    total_vacancies = cursor.fetchone()[0]

    # Последнее обновление
    cursor.execute('SELECT MAX(last_updated) FROM vacancies')
    last_update = cursor.fetchone()[0]

    conn.close()

    # Форматируем статистику
    stats_list = []
    for region_id, count in stats_data:
        stats_list.append({
            'region': MILLION_CITIES.get(region_id, f"Регион {region_id}"),
            'count': count,
            'percentage': round((count / total_vacancies) * 100, 2) if total_vacancies > 0 else 0
        })

    return render_template('stats.html',
                           stats=stats_list,
                           total_vacancies=total_vacancies,
                           last_update=last_update,
                           regions=MILLION_CITIES)


@app.route('/update', methods=['POST'])
def update_vacancies():
    """Обновление вакансий"""
    try:
        max_pages = request.json.get('max_pages', 15)
        timestamp = datetime.now()

        init_db()

        updated_count = 0
        for region_id, city_name in MILLION_CITIES.items():
            if region_id == 999:  # Пропускаем специальный код
                continue

            print(f"Обрабатываю вакансии для {city_name} (регион {region_id})...")

            try:
                vacancies = get_hr_vacancies_hh(region_id=region_id, max_pages=max_pages)
                print(f"Найдено {len(vacancies)} вакансий")

                save_vacancies_to_db(vacancies, region_id, timestamp)
                updated_count += len(vacancies)

            except Exception as e:
                print(f"Ошибка при обработке региона {region_id} ({city_name}): {e}")
                continue

        return jsonify({
            'success': True,
            'message': f'Обновлено {updated_count} вакансий',
            'updated_count': updated_count
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Ошибка при обновлении: {str(e)}'
        }), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True)