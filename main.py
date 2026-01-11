import telebot
from telebot import types
import os
from flask import Flask
from threading import Thread

# --- 1. 網頁監控 (防止 Render 休眠) ---
app = Flask('')
@app.route('/')
def home(): return "Bot is Alive!"

def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- 2. 初始化 ---
TOKEN = os.environ.get('BOT_TOKEN') or '8540965623:AAGI5nUvmYu2UOTMZPgiLqNemI3a7uXlFMg'
bot = telebot.TeleBot(TOKEN)
users = {}

# --- 3. 核心匹配算法 ---
def find_match(user_id):
    u = users[user_id]
    for target_id, t in users.items():
        if target_id == user_id or t['state'] != 'searching':
            continue
        
        # A. 鑰匙匹配 (優先權最高)
        if u['key'] or t['key']:
            if u['key'] == t['key'] and u['key'] is not None:
                return target_id
            else:
                continue # 有一方設了鑰匙但對不上，跳過

        # B. 性向自動匹配邏輯
        can_match = False
        # 同性戀匹配：性別相同 且 雙方都是同志
        if u['interest'] == '同志' and t['interest'] == '同志':
            if u['gender'] == t['gender']: can_match = True
        # 異性戀匹配：性別不同 且 雙方都是異性戀
        elif u['interest'] == '異性戀' and t['interest'] == '異性戀':
            if u['gender'] != t['gender']: can_match = True
        # 不限匹配：只要其中一方不限，或雙方皆不限
        elif u['interest'] == '不限' or t['interest'] == '不限':
            can_match = True
            
        if can_match: return target_id
    return None

# --- 4. 訊息處理器 ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'sticker', 'voice'])
def main_handler(message):
    uid = message.chat.id
    text = message.text if message.text else ""

    # 自動修復/啟動
    if text == '/start' or uid not in users:
        users[uid] = {'gender': None, 'interest': None, 'key': None, 'partner': None, 'state': 'setup'}
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add('男生', '女生', '不分')
        bot.send_message(uid, "👋 歡迎！請先選擇您的【性別】：", reply_markup=markup)
        return

    u = users[uid]

    # 指令：查看狀態
    if text == '/status' or text == '📊 在線人數':
        s = sum(1 for d in users.values() if d['state'] == 'searching')
        c = sum(1 for d in users.values() if d['state'] == 'chatting')
        bot.send_message(uid, f"📈 目前：{s} 人尋找中，{c} 人對話中\n(若等太久，可嘗試用 [🔑 鑰匙匹配] 功能)")
        return

    # 指令：結束對話
    if text == '/stop' or text == '❌ 停止/結束':
        if u['partner']:
            p_id = u['partner']
            for i in [uid, p_id]:
                users[i].update({'partner': None, 'state': 'idle', 'key': None})
                bot.send_message(i, "❌ 對話已結束。你可以重新開始匹配。", reply_markup=main_menu())
        else:
            u.update({'state': 'idle', 'key': None})
            bot.send_message(uid, "已回到主選單。", reply_markup=main_menu())
        return

    # A. 設定流程
    if u['state'] == 'setup':
        if u['gender'] is None:
            if text in ['男生', '女生', '不分']:
                u['gender'] = text
                markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
                markup.add('異性戀', '同志', '不限')
                bot.send_message(uid, f"好的，您是 {text}。接下來請選擇【性向】：", reply_markup=markup)
            return
        elif u['interest'] is None:
            if text in ['異性戀', '同志', '不限']:
                u['interest'] = text
                u['state'] = 'idle'
                bot.send_message(uid, "✅ 設定完成！系統將為您自動匹配。", reply_markup=main_menu())
            return

    # B. 配對動作
    if u['state'] == 'idle':
        if text == '🚀 開始配對':
            u['state'] = 'searching'
            bot.send_message(uid, "🔍 正在搜尋...", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('❌ 停止/結束'))
            target = find_match(uid)
            if target:
                start_chat(uid, target)
        elif text == '🔑 鑰匙匹配':
            u['state'] = 'wait_key'
            bot.send_message(uid, "🔑 請輸入鑰匙 (例如: 健身、台大、123)：")
        return

    # C. 鑰匙輸入
    if u['state'] == 'wait_key':
        u.update({'key': text, 'state': 'searching'})
        bot.send_message(uid, f"⌛ 已設定鑰匙「{text}」，搜尋中...")
        target = find_match(uid)
        if target:
            start_chat(uid, target)
        return

    # D. 聊天轉發
    if u['state'] == 'chatting' and u['partner']:
        p_id = u['partner']
        try:
            if message.content_type == 'text': bot.send_message(p_id, text)
            elif message.content_type == 'photo': bot.send_photo(p_id, message.photo[-1].file_id)
            elif message.content_type == 'sticker': bot.send_sticker(p_id, message.sticker.file_id)
            elif message.content_type == 'voice': bot.send_voice(p_id, message.voice.file_id)
        except:
            bot.send_message(uid, "⚠️ 傳送失敗，對方可能已離線。")

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🚀 開始配對', '🔑 鑰匙匹配')
    markup.add('📊 在線人數')
    return markup

def start_chat(id1, id2):
    for i, j in [(id1, id2), (id2, id1)]:
        users[i].update({'partner': j, 'state': 'chatting'})
        bot.send_message(i, "✨ 匹配成功！現在可以開始匿名聊天了。\n(支援圖片、貼圖、語音，輸入 /stop 結束)")

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()

