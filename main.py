import telebot
import psycopg2
from datetime import datetime, timedelta
import time
import threading
import os

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

bot = telebot.TeleBot(TOKEN)

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            phone VARCHAR(20),
            date DATE,
            next_service DATE,
            chat_id BIGINT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, "Привіт 👋 Напиши:\nІм'я, телефон, дата (YYYY-MM-DD)")

@bot.message_handler(func=lambda m: True)
def add_client(msg):
    try:
        name, phone, date = [x.strip() for x in msg.text.split(",")]
        next_service = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=180)).strftime("%Y-%m-%d")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clients (name, phone, date, next_service, chat_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, phone, date, next_service, msg.chat.id))
        conn.commit()
        cursor.close()
        conn.close()
        
        bot.send_message(msg.chat.id, f"✅ Додано. Наступне ТО: {next_service}")
    except:
        bot.send_message(msg.chat.id, "❌ Формат: Ім'я, телефон, 2026-07-12")

def check_reminders():
    while True:
        try:
            conn = get_db()
            cursor = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor.execute("SELECT name, chat_id FROM clients WHERE next_service = %s", (today,))
            clients = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            for name, chat_id in clients:
                try:
                    bot.send_message(chat_id, f"🔔 {name} — час техогляду")
                except:
                    pass
        except:
            pass
        
        time.sleep(86400)

threading.Thread(target=check_reminders, daemon=True).start()
bot.infinity_polling()
