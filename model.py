import sqlite3
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

def train_model():
    conn = sqlite3.connect('nutrition_bot.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            User.height, 
            User.weight, 
            User.age, 
            User.gender, 
            Meal.calories
        FROM history
        JOIN User ON history.user_id = User.id
        JOIN Meal ON history.meal_id = Meal.id
    """)
    data = cursor.fetchall()
    conn.close()

    X = []
    y = []
    for h, w, a, g, cal in data:
        gender = 1 if g == '男' else 0
        # 計算 BMR
        if g == '男':
            bmr = 13.7 * w + 5.0 * h - 6.8 * a + 66
        else:
            bmr = 9.6 * w + 1.8 * h - 4.7 * a + 655
        one_third_bmr = bmr / 3
        # 標註 y
        if cal > one_third_bmr:
            y.append(2)  # 過高
        elif one_third_bmr - 100 <= cal <= one_third_bmr:
            y.append(1)  # 正常
        else:
            y.append(0)  # 過低
        X.append([h, w, a, gender, cal])

    model = LogisticRegression(max_iter=5000)
    model.fit(X, y)
    y_pred = model.predict(X)
    acc = accuracy_score(y, y_pred)
    print(f"訓練集準確率：{acc:.2%}")

    joblib.dump(model, 'model.pkl')
    print("Model trained and saved as model.pkl")

if __name__ == '__main__':
    train_model()