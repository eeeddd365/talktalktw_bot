import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# 1. 建立一個極簡的 Flask 網頁伺服器
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Render 會自動給一個 PORT 環境變數，如果沒有就用 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# 2. 設定你的機器人 Token
# 建議你在 Render 的 Environment 設定名為 BOT_TOKEN 的變數
TOKEN = os.environ.get('BOT_TOKEN') or '8540965623:AAE69xBqJJo1gidq5zZ53kOiS79i302zKfg'
bot = telebot.TeleBot(TOKEN)

# 儲存用戶資料
users = {}

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    users[uid] = {'gender': None, 'interest': None, 'key': None, 'partner': None, 'state': 'setup'}
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('男生', '女生', '不分')
    bot.send_message(uid, "👋 你好！請先選擇性別：", reply_markup=markup)

# ... (中間的性別、性向、鑰匙邏輯保持不變) ...

# 3. 啟動腳本
if __name__ == "__main__":
    # 先啟動網頁伺服器執行緒
    server_thread = Thread(target=run_flask)
    server_thread.start()
    
    print("機器人正在啟動並監聽中...")
    # 使用 infinity_polling 確保連線更穩定
    bot.infinity_polling()