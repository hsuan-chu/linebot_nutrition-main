#ngrok http 5050
import gradio as gr
import joblib
model = joblib.load('model.pkl')

import sys
print("目前 Python 路徑：", sys.executable)

from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.v3.webhook import WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from database import (
    save_user_info,
    get_user_info,
    recommend_meal_by_keyword,
    recommend_meal_by_restaurant,
    get_random_meal,
    recommend_meal,
    get_exercises_with_mets
)
import sqlite3
import random
import traceback

app = Flask(__name__)

line_bot_api = LineBotApi('dZhbpYleRBOLn3WvJRxD/8f4uUrEHvbWtEJk5wKMaQ2YjsaqwCxMK8xO/fce2rboDh0CYobx2GbHtmQs2UH8Uha7fxJnKJKipsJqyQWqAHazeS4M3SHhw0sIlsgNBQJ7iVttD2ReuSmhxtlFr37p1wdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('8742c872c62857241a8cbe9f46325429')

user_states = {}
user_inputs = {}

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()
    if user_id not in user_inputs:
        user_inputs[user_id] = {}

    # 不滿意時隨機推薦餐點
    if "不滿意" in msg:
        result = get_random_meal()
        if not result:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("找不到符合的餐點"))
            return
        restaurant, food, cal = result
        user = get_user_info(user_inputs[user_id]["id"])
        if not user:
            line_bot_api.reply_message(event.reply_token, TextSendMessage("查無使用者資料，請重新註冊"))
            return
        gender = user[2]
        weight = user[5]
        height = user[4]
        age = user[3]
        gender_num = 1 if gender == '男' else 0
        features = [[height, weight, age, gender_num, cal]]
        pred = model.predict(features)[0]
        if pred == 2:
            exercises = get_exercises_with_mets()
            if exercises:
                exercise_list = []
                for name, mets in exercises:
                    kcal = weight * mets * 0.5
                    exercise_list.append(f"{name} 30分鐘（約消耗 {kcal:.0f} 大卡）")
                exercise_text = "\n💪".join(exercise_list)
            else:
                exercise_text = "快走 30 分鐘（約消耗 120 大卡）\n💪慢跑 30 分鐘（約消耗 200 大卡）\n💪游泳 30 分鐘（約消耗 250 大卡）"
            status = (
                f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷偏高，\n"
                f"建議多運動！🏃‍♂️推薦運動：\n💪{exercise_text}\n"
                f"請選擇一種運動進行！"
            )
        elif pred == 1:
            status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷屬於正常攝取範圍"
        else:
            status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷熱量攝取過少，請注意營養均衡！"
        reply = f"推薦餐點：{food}（{cal} kcal）\n店家：{restaurant}\n{status}"
        line_bot_api.reply_message(
            event.reply_token, [
                TextSendMessage(reply),
                TextSendMessage("如果對此提供結果不滿意或是想要吃下一餐時，都可以繼續提出想吃的東西呦！")
            ]
        )
        return

    # 滿意時回傳圖片
    if any(kw in msg for kw in ["滿意", "滿意！", "謝謝", "謝啦", "感謝", "結束", "thanks", "thank you", "bye", "再見", "結束對話", "好欸", "謝謝你", "感謝你"]):
        image_url = "https://9fd3-163-14-207-218.ngrok-free.app/static/thank.jpg"  
        line_bot_api.reply_message(
            event.reply_token,
            ImageSendMessage(
                original_content_url=image_url,
                preview_image_url=image_url
            )
        )
        return

    # 新增：判斷老客戶或首次登入
    if msg == "我是老客戶":
        user_states[user_id] = "old_customer_ask_id"
        line_bot_api.reply_message(event.reply_token, TextSendMessage("請輸入你的『學號』或『人事代碼』"))
        return
    elif msg == "首次登入":
        user_states[user_id] = "ask_id"
        user_inputs[user_id] = {}
        line_bot_api.reply_message(event.reply_token, TextSendMessage("請輸入你的『學號』或『人事代碼』"))
        return

    try:
        state = user_states.get(user_id)

        # 老客戶輸入學號/人事代碼後的處理
        if state == "old_customer_ask_id":
            input_id = msg
            conn = sqlite3.connect('nutrition_bot.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM User WHERE id = ?", (input_id,))
            user_row = cursor.fetchone()
            conn.close()
            if user_row:
                user_states[user_id] = "ready"
                user_inputs[user_id] = {"id": input_id}
                user_data = f"學號/代碼：{user_row[0]}\n性別：{user_row[2]}\n年齡：{user_row[3]}\n身高：{user_row[4]} cm\n體重：{user_row[5]} kg"
                line_bot_api.reply_message(event.reply_token, [
                    TextSendMessage(f"🌼已找到您的資料：\n{user_data}"),
                    TextSendMessage("是否需要更改基本資料？（是/否）"),
                ])
                user_states[user_id] = "ask_update_info"
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage("❎查無此學號或人事代碼，請重新輸入或輸入『首次登入』註冊。"))
            return

        # 老客戶選擇是否更新基本資料
        elif state == "ask_update_info":
            if msg == "是":
                user_states[user_id] = "ask_gender"
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage("請問您的性別？（男/女）"))
            elif msg == "否":
                user_states[user_id] = "ready"
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage("✨資料已確認！請輸入您今天想吃的『店家』或『食物種類』，或輸入『隨機』幫您決定。"))
            else:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage("請輸入「是」或「否」。"))
            return

        elif state == "ask_gender":
            if msg not in ["男", "女"]:
                line_bot_api.reply_message(
                    event.reply_token, TextSendMessage("請輸入「男」或「女」"))
                return
            user_inputs[user_id]["gender"] = msg
            user_states[user_id] = "ask_age"
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage("請問您的年齡？"))
            return

        elif state == "ask_age":
            user_inputs[user_id]["age"] = int(msg)
            user_states[user_id] = "ask_height"
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage("請問您的身高（cm）？"))
            return

        elif state == "ask_height":
            user_inputs[user_id]["height"] = float(msg)
            user_states[user_id] = "ask_weight"
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage("請問您的體重（kg）？"))
            return

        elif state == "ask_weight":
            msg_clean = ''.join(filter(lambda c: c.isdigit() or c == '.', msg))
            user_inputs[user_id]["weight"] = float(msg_clean)
            data = user_inputs[user_id]
            save_user_info(
                data["id"], data.get("name", ""), data["gender"],
                data["age"], data["height"], data["weight"]
            )
            user_states[user_id] = "ready"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(
                "✨感謝填寫！請輸入您今天想吃的『店家』或『食物種類』，或輸入『隨機』幫您決定。"))
            return

        # 新客戶註冊流程
        elif state == "ask_id":
            input_id = msg
            conn = sqlite3.connect('nutrition_bot.db')
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM User WHERE id = ?", (input_id,))
            user_row = cursor.fetchone()
            conn.close()
            user_inputs[user_id] = {"id": input_id}
            if user_row:
                user_states[user_id] = "ready"
                user_inputs[user_id] = {"id": input_id}
                user_data = f"學號/代碼：{user_row[0]}\n性別：{user_row[2]}\n年齡：{user_row[3]}\n身高：{user_row[4]} cm\n體重：{user_row[5]} kg"
                line_bot_api.reply_message(event.reply_token, [
                    TextSendMessage(f"🌼已找到您的資料：\n{user_data}"),
                    TextSendMessage("是否需要更改基本資料？（是/否）"),
                ])
                user_states[user_id] = "ask_update_info"
            else:
                user_states[user_id] = "ask_gender"
                line_bot_api.reply_message(event.reply_token, TextSendMessage("請問您的性別？（男/女）"))
            return

        elif state == "ready":
            # 餐廳關鍵字判斷要放在這裡
            restaurant_keywords = [
                "趙班長飯捲","MOMO","趙班長","滷味", "MOMO滷味", "蒲家廚房","蒲家", "四海遊龍","四海","遊龍", "丼物園", "金盃美而美","美而美","金盃", "海羊"
            ]
            for rkw in restaurant_keywords:
                if rkw in msg:
                    result = recommend_meal_by_restaurant(rkw)
                    if result:
                        restaurant, food, cal = result
                        user = get_user_info(user_inputs[user_id]["id"])
                        if not user:
                            line_bot_api.reply_message(event.reply_token, TextSendMessage("查無使用者資料，請重新註冊"))
                            return
                        gender = user[2]
                        weight = user[5]
                        height = user[4]
                        age = user[3]
                        gender_num = 1 if gender == '男' else 0
                        features = [[height, weight, age, gender_num, cal]]
                        pred = model.predict(features)[0]
                        if pred == 2:
                            exercises = get_exercises_with_mets()
                            if exercises:
                                exercise_list = []
                                for name, mets in exercises:
                                    kcal = weight * mets * 0.5
                                    exercise_list.append(f"{name} 30分鐘（約消耗 {kcal:.0f} 大卡）")
                                exercise_text = "\n💪".join(exercise_list)
                            else:
                                exercise_text = "快走 30 分鐘（約消耗 120 大卡）\n💪慢跑 30 分鐘（約消耗 200 大卡）\n💪游泳 30 分鐘（約消耗 250 大卡）"
                            status = (
                                f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷偏高，\n"
                                f"建議多運動！🏃‍♂️推薦運動：\n💪{exercise_text}\n"
                                f"請選擇一種運動進行！"
                            )
                        elif pred == 1:
                            status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷屬於正常攝取範圍"
                        else:
                            status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷熱量攝取過少，請注意營養均衡！"
                        reply = f"推薦餐點：{food}（{cal} kcal）\n店家：{restaurant}\n{status}"
                        line_bot_api.reply_message(
                            event.reply_token, [
                                TextSendMessage(reply),
                                TextSendMessage("如果對此提供結果不滿意或是想要吃下一餐時，都可以繼續提出想吃的東西呦！")
                            ]
                        )
                        return
                    else:
                        reply = "找不到符合的店家或餐點"
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(reply))
                        return

            # 其餘關鍵字與推薦
            keywords = ["飯", "麵", "雞", "牛", "蛋", "豬", "蛋餅","抓餅","水餃","鍋貼","飯捲","冬粉","湯","抄手","漢堡","堡","潛艇堡","乳酪餅","捲","吐司","厚片","咖哩","丼","定食","湯餃","餅"]
            for kw in keywords:
                if kw in msg:
                    result = recommend_meal_by_keyword(kw)
                    if result:
                        restaurant, food, cal = random.choice(result)
                        user = get_user_info(user_inputs[user_id]["id"])
                        if not user:
                            line_bot_api.reply_message(event.reply_token, TextSendMessage("查無使用者資料，請重新註冊"))
                            return
                        gender = user[2]
                        weight = user[5]
                        height = user[4]
                        age = user[3]
                        gender_num = 1 if gender == '男' else 0
                        features = [[height, weight, age, gender_num, cal]]
                        pred = model.predict(features)[0]
                        if pred == 2:
                            exercises = get_exercises_with_mets()
                            if exercises:
                                exercise_list = []
                                for name, mets in exercises:
                                    kcal = weight * mets * 0.5
                                    exercise_list.append(f"{name} 30分鐘（約消耗 {kcal:.0f} 大卡）")
                                exercise_text = "\n💪".join(exercise_list)
                            else:
                                exercise_text = "快走 30 分鐘（約消耗 120 大卡）\n💪慢跑 30 分鐘（約消耗 200 大卡）\n💪游泳 30 分鐘（約消耗 250 大卡）"
                            status = (
                                f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷偏高，\n"
                                f"建議多運動！🏃‍♂️推薦運動：\n💪{exercise_text}\n"
                                f"請選擇一種運動進行！"
                            )
                        elif pred == 1:
                            status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷屬於正常攝取範圍"
                        else:
                            status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷熱量攝取過少，請注意營養均衡！"
                        reply = f"推薦餐點：{food}（{cal} kcal）\n店家：{restaurant}\n{status}"
                        line_bot_api.reply_message(
                            event.reply_token, [
                                TextSendMessage(reply),
                                TextSendMessage("如果對此提供結果不滿意或是想要吃下一餐時，都可以繼續提出想吃的東西呦！")
                            ]
                        )
                        return
                    else:
                        reply = "找不到符合的餐點"
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(reply))
                        return

            if msg == "隨機":
                result = get_random_meal()
            else:
                result = recommend_meal(msg)

            if not result:
                line_bot_api.reply_message(event.reply_token, TextSendMessage("找不到符合的餐點"))
                return

            restaurant, food, cal = result

            user = get_user_info(user_inputs[user_id]["id"])
            if not user:
                line_bot_api.reply_message(event.reply_token, TextSendMessage("查無使用者資料，請重新註冊"))
                return
            gender = user[2]
            weight = user[5]
            height = user[4]
            age = user[3]
            gender_num = 1 if gender == '男' else 0
            features = [[height, weight, age, gender_num, cal]]
            pred = model.predict(features)[0]
            if pred == 2:
                exercises = get_exercises_with_mets()
                if exercises:
                    exercise_list = []
                    for name, mets in exercises:
                        kcal = weight * mets * 0.5
                        exercise_list.append(f"{name} 30分鐘（約消耗 {kcal:.0f} 大卡）")
                    exercise_text = "\n💪".join(exercise_list)
                else:
                    exercise_text = "快走 30 分鐘（約消耗 120 大卡）\n💪慢跑 30 分鐘（約消耗 200 大卡）\n💪游泳 30 分鐘（約消耗 250 大卡）"
                status = (
                    f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷偏高，\n"
                    f"建議多運動！🏃‍♂️推薦運動：\n💪{exercise_text}\n"
                    f"請選擇一種運動進行！"
                )
            elif pred == 1:
                status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷屬於正常攝取範圍"
            else:
                status = f"您的本餐熱量為 {cal:.0f} 大卡，模型判斷熱量攝取過少，請注意營養均衡！"

            reply = f"推薦餐點：{food}（{cal} kcal）\n店家：{restaurant}\n{status}"
            line_bot_api.reply_message(
                event.reply_token, [
                    TextSendMessage(reply),
                    TextSendMessage("如果對此提供結果不滿意或是想要吃下一餐時，都可以繼續提出想吃的東西呦！")
                ]
            )
            return

    except Exception as e:
        print("LINE BOT ERROR:", e)
        traceback.print_exc()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(f"發生錯誤：{str(e)}"))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'



def gradio_predict(height, weight, age, gender, calories):
    # gender 轉成數字
    gender_num = 1 if gender == "男" else 0
    features = [[height, weight, age, gender_num, calories]]
    pred = model.predict(features)[0]
    if pred == 2:
        return "熱量偏高，建議多運動"
    elif pred == 1:
        return "熱量正常"
    else:
        return "熱量偏低，請注意營養均衡"

def launch_gradio():
    gender_dropdown = gr.Dropdown(choices=["男", "女"], label="性別")
    iface = gr.Interface(
        fn=gradio_predict,
        inputs=[
            gr.Number(label="身高(cm)"),
            gr.Number(label="體重(kg)"),
            gr.Number(label="年齡"),
            gender_dropdown,
            gr.Number(label="本餐熱量(kcal)")
        ],
        outputs="text",
        title="熱量攝取預測模型",
        description="輸入個人基本資料與餐點熱量，模型會判斷熱量攝取狀況"
    )
    iface.launch(server_name="0.0.0.0", server_port=7861)

if __name__ == "__main__":
    import threading
    # 同時啟動 Flask 與 Gradio 介面，分別在不同埠口
    threading.Thread(target=launch_gradio).start()
    app.run(port=7861)

if __name__ == "__main__":
    app.run(port=7861)
