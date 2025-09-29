# app.py
from flask import Flask, render_template, request, jsonify
import sqlite3
from datetime import datetime
import requests
import time
from typing import List, Optional

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

def get_hr_vacancies_hh(region_id: Optional[int] = None, max_pages: int = 15) -> List[str]:
    """
    Получает список ссылок на вакансии в разделе 'Управление персоналом' с hh.ru
    """
    hr_category_id = "118"
    
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
                vacancy_url = vacancy.get("alternate_url")
                if vacancy_url:
                    vacancies_links.append(vacancy_url)

            print(f"Обработано страница {page + 1}, найдено вакансий: {len(vacancies)}")

            pages = data.get("pages", 0)
            if page >= pages - 1:
                break

            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе: {e}")
            break

    return vacancies_links

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE)
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

def save_vacancies_to_db(vacancies: List[str], region_id: int, timestamp: datetime) -> None:
    """Сохраняет вакансии в базу данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    for vacancy_url in vacancies:
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
    per_page = 20
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Получаем общее количество вакансий
    if region_id:
        cursor.execute('SELECT COUNT(*) FROM vacancies WHERE region = ?', (region_id,))
    else:
        cursor.execute('SELECT COUNT(*) FROM vacancies')
    
    total_vacancies = cursor.fetchone()[0]
    
    # Получаем вакансии для текущей страницы
    offset = (page - 1) * per_page
    if region_id:
        cursor.execute('''
            SELECT id, vacancy_url, region, added, last_updated 
            FROM vacancies 
            WHERE region = ?
            ORDER BY last_updated DESC
            LIMIT ? OFFSET ?
        ''', (region_id, per_page, offset))
    else:
        cursor.execute('''
            SELECT id, vacancy_url, region, added, last_updated 
            FROM vacancies 
            ORDER BY last_updated DESC
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
            'updated': vac[4]
        })
    
    total_pages = (total_vacancies + per_page - 1) // per_page
    
    return render_template('vacancies.html', 
                         vacancies=vacancies_list,
                         regions=MILLION_CITIES,
                         current_region=region_id,
                         current_page=page,
                         total_pages=total_pages)

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
        print(max_pages)
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