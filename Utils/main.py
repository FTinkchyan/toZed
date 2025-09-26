import takers
import time

if __name__ == "__main__":
    # Вызываем функцию для получения вакансий (например, рекрутеры в Москве)
    vacancies = takers.get_all_vacancies_from_hh()

    if vacancies:
        for i, vacancy in enumerate(vacancies, 1):
            print(f"\n{'=' * 50}")
            print(f"Вакансия #{i}")
            print(f"Название: {vacancy.get('name', 'Не указано')}")
            print(f"Компания: {vacancy.get('employer', {}).get('name', 'Не указано')}")
            print(f"Зарплата: {vacancy.get('salary', 'Не указана')}")
            print(f"Требуемый опыт: {vacancy.get('experience', {}).get('name', 'Не указан')}")
            print(f"Город: {vacancy.get('area', {}).get('name', 'Не указан')}")
            print(f"Дата публикации: {vacancy.get('published_at', 'Не указана')}")
            print(f"Ссылка: {vacancy.get('alternate_url', vacancy.get('url', 'Нет ссылки'))}")
            print(f"\nОписание: {vacancy.get('snippet', {}).get('requirement', 'Нет описания')}")
            print('=' * 50)

            # Пауза между вакансиями
            time.sleep(3)
    else:
        print("Не удалось получить вакансии")