import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# --- 1. 初始化 Flask (為了讓 Render 保持 Live) ---
app = Flask('')

@app.route('/')
def home():
    return "機器人運行中！"

def run_flask():
    # Render 會自動分配 PORT，若無則預設 8080
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. 初始化 Telegram Bot ---
# 優先讀取環境變數 BOT_TOKEN，若無則填入字串
TOKEN = os.environ.get('BOT_TOKEN') or '8540965623:AAE69xBqJJo1gidq5zZ53kOiS79i302zKfg'
bot = telebot.TeleBot(TOKEN)

# 儲存用戶資料 (記憶體模式，重啟會清空)
# 格式: {user_id: {'gender': None, 'interest': None, 'key': None, 'partner': None, 'state': 'idle'}}
users = {}

# --- 3. 機器人邏輯 ---

# A. 入口點
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    # 初始化用戶狀態
    users[uid] = {'gender': None, 'interest': None, 'key': None, 'partner': None, 'state': 'setup'}
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('男生', '女生', '不分')
    bot.send_message(uid, "👋 歡迎使用匿名聊天！\n請先選擇您的【性別】：", reply_markup=markup)
    print(f"DEBUG: 用戶 {uid} 開始設定")

# B. 處理設定階段 (性別 & 性向)
@bot.message_handler(func=lambda m: users.get(m.chat.id, {}).get('state') == 'setup')
def setup_profile(message):
    uid = message.chat.id
    u = users[uid]
    text = message.text

    # 第一步：設定性別
    if u['gender'] is None:
        if text in ['男生', '女生', '不分']:
            u['gender'] = text
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('異性戀', '同志', '不限')
            bot.send_message(uid, f"好的，您是{text}。\n接下來請選擇您的【性向】：", reply_markup=markup)
            print(f"DEBUG: 用戶 {uid} 設定性別為 {text}")
        else:
            bot.send_message(uid, "請使用下方按鈕選擇性別喔！")

    # 第二步：設定性向
    elif u['interest'] is None:
        if text in ['異性戀', '同志', '不限']:
            u['interest'] = text
            u['state'] = 'idle'  # 設定完成，進入閒置狀態
            markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
            markup.add('使用鑰匙匹配', '隨機配對')
            bot.send_message(uid, "✅ 設定完成！\n您可以開始尋找對象了：", reply_markup=markup)
            print(f"DEBUG: 用戶 {uid} 設定性向為 {text}")
        else:
            bot.send_message(uid, "請使用下方按鈕選擇性向喔！")

# C. 處理鑰匙匹配
@bot.message_handler(func=lambda m: m.text == '使用鑰匙匹配')
def ask_key(message):
    uid = message.chat.id
    users[uid]['state'] = 'wait_key'
    bot.send_message(uid, "🔑 請輸入匹配鑰匙（關鍵字）：\n(例如：運動、123)")

@bot.message_handler(func=lambda m: users.get(m.chat.id, {}).get('state') == 'wait_key')
def match_key(message):
    uid = message.chat.id
    key = message.text
    users[uid].update({'key': key, 'state': 'searching'})
    
    print(f"DEBUG: 用戶 {uid} 正在用鑰匙 [{key}] 搜尋")
    
    # 搜尋邏輯：找一個跟我鑰匙一樣，且也在搜尋中的人
    match_id = None
    for other_id, data in users.items():
        if other_id != uid and data.get('state') == 'searching' and data.get('key') == key:
            match_id = other_id
            break
            
    if match_id:
        # 配對成功
        users[uid].update({'partner': match_id, 'state': 'chatting'})
        users[match_id].update({'partner': uid, 'state': 'chatting'})
        
        bot.send_message(uid, f"✨ 鑰匙 [{key}] 匹配成功！\n現在可以開始聊天了。\n(輸入 /stop 結束對話)")
        bot.send_message(match_id, f"✨ 鑰匙 [{key}] 匹配成功！\n現在可以開始聊天了。\n(輸入 /stop 結束對話)")
        print(f"DEBUG: 用戶 {uid} 與 {match_id} 配對成功")
    else:
        bot.send_message(uid, f"⌛ 正在搜尋同樣使用「{key}」的人，請稍候...")

# D. 處理聊天訊息轉發
@bot.message_handler(func=lambda m: users.get(m.chat.id, {}).get('state') == 'chatting' and not m.text.startswith('/'))
def forward_message(message):
    uid = message.chat.id
    partner_id = users[uid]['partner']
    
    try:
        if message.text:
            bot.send_message(partner_id, message.text)
        elif message.sticker:
            bot.send_sticker(partner_id, message.sticker.file_id)
        # 如果要支持圖片，可以在此加入 photo 的處理
    except Exception as e:
        print(f"DEBUG: 轉發失敗 {e}")

# E. 停止對話
@bot.message_handler(commands=['stop'])
def stop_chat(message):
    uid = message.chat.id
    u = users.get(uid)
    if u and u.get('partner'):
        partner_id = u['partner']
        # 雙方回歸閒置狀態
        users[uid].update({'partner': None, 'state': 'idle', 'key': None})
        users[partner_id].update({'partner': None, 'state': 'idle', 'key': None})
        
        bot.send_message(uid, "❌ 對話已結束。")
        bot.send_message(partner_id, "❌ 對方已結束對話。")
    else:
        bot.send_message(uid, "您目前不在對話中。")

# --- 4. 啟動程序 ---
if __name__ == "__main__":
    # 啟動 Flask 執行緒
    t = Thread(target=run_flask)
    t.start()
    
    print("--- 機器人啟動日誌 ---")
    try:
        me = bot.get_me()
        print(f"連接成功！機器人名稱: @{me.username}")
    except Exception as e:
        print(f"連接失敗: {e}")
        
    # 開始輪詢
    bot.infinity_polling()
