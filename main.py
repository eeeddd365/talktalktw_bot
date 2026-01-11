import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# --- 1. 網頁監控 (防止 Render 關閉服務) ---
app = Flask('')

@app.route('/')
def home():
    return "機器人穩定運行中！"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. 機器人初始化 ---
# 提示：請確保 Render 的 Environment Variables 裡有設定 BOT_TOKEN
TOKEN = os.environ.get('BOT_TOKEN') or '你的_TOKEN_貼在這裡'
bot = telebot.TeleBot(TOKEN)

# 儲存用戶資料 (記憶體模式)
users = {}

# --- 3. 核心邏輯 ---

@bot.message_handler(func=lambda m: True)
def handle_all_logic(message):
    uid = message.chat.id
    text = message.text
    
    # A. 自動修復狀態：如果 users 裡沒有這個人，或者輸入 /start
    if text == '/start' or uid not in users:
        users[uid] = {'gender': None, 'interest': None, 'key': None, 'partner': None, 'state': 'setup'}
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add('男生', '女生', '不分')
        bot.send_message(uid, "👋 歡迎！請先選擇您的【性別】：", reply_markup=markup)
        print(f"DEBUG: 用戶 {uid} 初始化/啟動")
        return

    u = users[uid]
    print(f"DEBUG: 用戶 {uid} 狀態: {u['state']}, 輸入內容: {text}")

    # B. 設定流程 (處理性別與性向)
    if u['state'] == 'setup':
        if u['gender'] is None:
            if text in ['男生', '女生', '不分']:
                u['gender'] = text
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add('異性戀', '同志', '不限')
                bot.send_message(uid, f"好的，您是{text}。\n請選擇您的【性向】：", reply_markup=markup)
            else:
                bot.send_message(uid, "請使用下方按鈕選擇性別喔！")
        
        elif u['interest'] is None:
            if text in ['異性戀', '同志', '不限']:
                u['interest'] = text
                u['state'] = 'idle'
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add('使用鑰匙匹配', '隨機配對')
                bot.send_message(uid, "✅ 設定完成！請選擇模式開始：", reply_markup=markup)
            else:
                bot.send_message(uid, "請使用按鈕選擇性向喔！")
        return

    # C. 處理聊天中斷 (/stop)
    if text == '/stop':
        if u['partner']:
            p_id = u['partner']
            users[uid].update({'partner': None, 'state': 'idle', 'key': None})
            users[p_id].update({'partner': None, 'state': 'idle', 'key': None})
            bot.send_message(uid, "❌ 對話已結束。")
            bot.send_message(p_id, "❌ 對方已結束對話。")
        else:
            bot.send_message(uid, "你目前不在對話中。")
        return

    # D. 處理匹配邏輯
    if u['state'] == 'idle' and text == '使用鑰匙匹配':
        u['state'] = 'wait_key'
        bot.send_message(uid, "🔑 請輸入匹配鑰匙（關鍵字）：")
        return

    if u['state'] == 'wait_key':
        u.update({'key': text, 'state': 'searching'})
        # 尋找對手
        match_id = next((i for i, d in users.items() if i != uid and d.get('state') == 'searching' and d.get('key') == text), None)
        
        if match_id:
            users[uid].update({'partner': match_id, 'state': 'chatting'})
            users[match_id].update({'partner': uid, 'state': 'chatting'})
            bot.send_message(uid, f"✨ 鑰匙 [{text}] 匹配成功！(輸入 /stop 結束)")
            bot.send_message(match_id, f"✨ 鑰匙 [{text}] 匹配成功！(輸入 /stop 結束)")
        else:
            bot.send_message(uid, f"⌛ 正在搜尋鑰匙「{text}」的人...")
        return

    # E. 訊息轉發
    if u['state'] == 'chatting' and u['partner']:
        try:
            bot.send_message(u['partner'], text)
        except:
            bot.send_message(uid, "⚠️ 訊息發送失敗，對方可能已離線。")

# --- 4. 啟動程序 ---
if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("--- 系統啟動成功 ---")
    bot.infinity_polling()
