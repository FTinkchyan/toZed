import hhamster
import sqlite3

hhamster.process_million_cities_vacancies(max_pages=15)

# Проверяем результаты
conn = sqlite3.connect("vacancies.db")
cursor = conn.cursor()

# Подсчет вакансий по регионам
cursor.execute('''
    SELECT region, COUNT(*) as count 
    FROM vacancies 
    GROUP BY region 
    ORDER BY count DESC
''')

print("\nСтатистика по регионам:")
for region, count in cursor.fetchall():
    print(f"Регион {region}: {count} вакансий")

conn.close()