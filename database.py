 # database.py
import sqlite3
DB_PATH = "nutrition_bot.db"  # 若你有這個變數就用，沒有請自行調整

def recommend_meal_by_restaurant(restaurant_keyword):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT restaurant, food, calories FROM Meal WHERE restaurant LIKE ? ORDER BY RANDOM() LIMIT 1",
        (f"%{restaurant_keyword}%",)
    )
    result = cursor.fetchone()
    conn.close()
    return result

def save_user_info(user_id, name, gender, age, height, weight):
    conn = sqlite3.connect('nutrition_bot.db')
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR REPLACE INTO User (id, name, gender, age, height, weight) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, gender, age, height, weight)
    )

    conn.commit()
    print(f"✅ 使用者資料已儲存：{user_id}, {name}, {gender}, {age}, {height}, {weight}")
    conn.close()


def get_user_info(user_id):
    conn = sqlite3.connect("nutrition_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM User WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
def get_exercises_with_mets(limit=3):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, mets FROM exercises_mets ORDER BY RANDOM() LIMIT ?", (limit,))
    results = cursor.fetchall()
    conn.close()
    return results

def get_random_meal():
    conn = sqlite3.connect('nutrition_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT restaurant, food, calories FROM Meal ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result

def recommend_meal(food_type):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT food, calories FROM Meal WHERE food LIKE ?", ('%' + food_type + '%',))
    results = cursor.fetchall()
    conn.close()
    return results

def recommend_meal_by_keyword(keyword):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT restaurant, food, calories FROM Meal WHERE food LIKE ?", ('%' + keyword + '%',))
    results = cursor.fetchall()
    conn.close()
    return results
def recommend_exercise(level):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM exercises_mets ORDER BY ABS(mets - ?) LIMIT 1", (level,))
    result = cursor.fetchone()
    conn.close()
    return result

