import requests
import time
from typing import List, Optional

def get_hr_vacancies_hh(region_id: Optional[int] = None, max_pages: int = 10) -> List[str]:
    """
    Получает список ссылок на вакансии в разделе 'Управление персоналом' с hh.ru

    Args:
        region_id: ID региона (по умолчанию Россия - 113)
        москва 1,
        санкт-петербург 2,
        новосибирск 4,
        екатеринбург 3,
        нижний новгород 66,
        казань 88,
        россия 113
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