import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# --- 1. 網頁監控 ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. 機器人初始化 ---
TOKEN = os.environ.get('BOT_TOKEN') or '8540965623:AAE69xBqJJo1gidq5zZ53kOiS79i302zKfg'
bot = telebot.TeleBot(TOKEN)

# 儲存用戶資料
users = {}

# --- 3. 輔助函數：找尋匹配對象 ---
def find_match(user_id):
    u = users[user_id]
    for target_id, t in users.items():
        if target_id == user_id: continue
        if t['state'] != 'searching': continue
        
        # 配對邏輯
        # 1. 鑰匙匹配優先
        if u['key'] and t['key']:
            if u['key'] == t['key']:
                return target_id
            else:
                continue
        
        # 2. 性向匹配邏輯
        # 如果用戶 A 是同志，對象 B 必須也是同性別且是同志
        if u['interest'] == '同志' and t['interest'] == '同志':
            if u['gender'] == t['gender']:
                return target_id
        
        # 如果用戶 A 是異性戀，對象 B 必須是異性且是異性戀
        if u['interest'] == '異性戀' and t['interest'] == '異性戀':
            if u['gender'] != t['gender']:
                return target_id
                
        # 如果有一方是「不限」，則只看對方是否接受
        if u['interest'] == '不限' or t['interest'] == '不限':
            return target_id
            
    return None

# --- 4. 核心處理邏輯 ---

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'sticker'])
def main_logic(message):
    uid = message.chat.id
    text = message.text if message.text else ""

    # 狀態修復與初始化
    if text == '/start' or uid not in users:
        users[uid] = {'gender': None, 'interest': None, 'key': None, 'partner': None, 'state': 'setup'}
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add('男生', '女生', '不分')
        bot.send_message(uid, "👋 歡迎！為了幫您精準配對，請選擇您的【性別】：", reply_markup=markup)
        return

    u = users[uid]

    # A. 設定流程
    if u['state'] == 'setup':
        if u['gender'] is None:
            if text in ['男生', '女生', '不分']:
                u['gender'] = text
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add('異性戀', '同志', '不限')
                bot.send_message(uid, f"確認性別：{text}\n請選擇您的【性向】：", reply_markup=markup)
            return
        elif u['interest'] is None:
            if text in ['異性戀', '同志', '不限']:
                u['interest'] = text
                u['state'] = 'idle'
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add('🚀 開始隨機配對', '🔑 鑰匙匹配', '📊 查看在線人數')
                bot.send_message(uid, "✅ 設定完成！\n系統會根據您的性向自動篩選對象。", reply_markup=markup)
            return

    # B. 查看狀態
    if text == '📊 查看在線人數':
        searching_count = sum(1 for d in users.values() if d['state'] == 'searching')
        chatting_count = sum(1 for d in users.values() if d['state'] == 'chatting')
        bot.send_message(uid, f"📈 目前系統狀態：\n🔍 尋找中：{searching_count} 人\n💬 對話中：{chatting_count} 人")
        return

    # C. 停止對話
    if text == '/stop' or text == '❌ 結束對話':
        if u['partner']:
            p_id = u['partner']
            users[uid].update({'partner': None, 'state': 'idle', 'key': None})
            users[p_id].update({'partner': None, 'state': 'idle', 'key': None})
            bot.send_message(uid, "❌ 對話已結束。你可以重新開始匹配。", reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(p_id, "❌ 對方已離開對話。", reply_markup=types.ReplyKeyboardRemove())
        else:
            u['state'] = 'idle'
            bot.send_message(uid, "已停止搜尋。")
        return

    # D. 配對邏輯
    if u['state'] == 'idle' and (text == '🚀 開始隨機配對' or text == '🔑 鑰匙匹配'):
        if text == '🔑 鑰匙匹配':
            u['state'] = 'wait_key'
            bot.send_message(uid, "請輸入匹配鑰匙：")
            return
        
        u['state'] = 'searching'
        bot.send_message(uid, "🔍 正在為您尋找適合的對象...", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('❌ 結束對話'))
        
        match_id = find_match(uid)
        if match_id:
            users[uid].update({'partner': match_id, 'state': 'chatting'})
            users[match_id].update({'partner': uid, 'state': 'chatting'})
            msg = "✨ 發現對象！你們現在可以開始聊天了。\n(輸入 /stop 隨時結束)"
            bot.send_message(uid, msg)
            bot.send_message(match_id, msg)
        return

    if u['state'] == 'wait_key':
        u.update({'key': text, 'state': 'searching'})
        match_id = find_match(uid)
        if match_id:
            users[uid].update({'partner': match_id, 'state': 'chatting'})
            users[match_id].update({'partner': uid, 'state': 'chatting'})
            bot.send_message(uid, f"🔑 鑰匙「{text}」匹配成功！")
            bot.send_message(match_id, f"🔑 鑰匙「{text}」匹配成功！")
        else:
            bot.send_message(uid, f"⌛ 已設定鑰匙「{text}」，等待相同對象中...")
        return

    # E. 訊息轉發 (支援圖片與貼圖)
    if u['state'] == 'chatting' and u['partner']:
        p_id = u['partner']
        try:
            if message.content_type == 'text':
                bot.send_message(p_id, text)
            elif message.content_type == 'photo':
                bot.send_photo(p_id, message.photo[-1].file_id, caption=message.caption)
            elif message.content_type == 'sticker':
                bot.send_sticker(p_id, message.sticker.file_id)
        except:
            bot.send_message(uid, "⚠️ 傳送失敗，對方可能已離線。")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()
