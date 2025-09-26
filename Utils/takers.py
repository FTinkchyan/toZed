import requests
import time


def get_all_vacancies_from_hh(area=1, experience=None, salary=None, per_page=100, max_pages=20):
    """
    Получает ВСЕ вакансии для рекрутеров/специалистов по подбору персонала
    """
    base_url = "https://api.hh.ru/vacancies"
    all_vacancies = []
    page = 0

    # Параметры для поиска рекрутеров (ключевые слова в названии)
    recruiter_keywords = [
        'рекрутер',
        'рекрутёр',
        'специалист по подбору персонала',
        'менеджер по подбору персонала',
        'HR-специалист',
        'HR-менеджер',
        'карьерный консультант'
    ]

    # Формируем поисковый запрос
    search_query = " OR ".join(recruiter_keywords)

    params = {
        'text': search_query,
        'area': area,  # 1 - Москва
        'per_page': per_page,
        'page': page
    }

    if experience:
        params['experience'] = experience
    if salary:
        params['salary'] = salary

    try:
        while True:
            params['page'] = page
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            all_vacancies.extend(data['items'])

            # Проверяем, есть ли ещё страницы
            page += 1
            if page >= data['pages'] or page >= max_pages:
                break

            # Задержка для соблюдения лимитов API
            time.sleep(0.5)

        print(f"Всего получено вакансий рекрутеров: {len(all_vacancies)}")
        return all_vacancies

    except requests.exceptions.RequestException as e:
        print(f"Ошибка: {e}")
        return None