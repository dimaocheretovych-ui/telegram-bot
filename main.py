import telebot
import psycopg2
from datetime import datetime
import os
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

TOKEN = os.getenv("TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 1234567890  # ЗАМІНИ НА СВІЙ CHAT_ID

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
            address VARCHAR(255),
            equipment VARCHAR(255),
            install_date DATE,
            service_date DATE,
            chat_id BIGINT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(msg.chat.id, 
        "👋 Привіт! Додай клієнта:\n\n"
        "Ім'я, Телефон, Адреса, Обладнання, Дата встановлення (YYYY-MM-DD), Дата ТО (YYYY-MM-DD)")

@bot.message_handler(func=lambda m: True)
def add_client(msg):
    try:
        parts = [x.strip() for x in msg.text.split(",")]
        if len(parts) != 6:
            raise ValueError("Невірна кількість параметрів")
        
        name, phone, address, equipment, install_date, service_date = parts
        
        datetime.strptime(install_date, "%Y-%m-%d")
        datetime.strptime(service_date, "%Y-%m-%d")
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clients (name, phone, address, equipment, install_date, service_date, chat_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (name, phone, address, equipment, install_date, service_date, msg.chat.id))
        conn.commit()
        cursor.close()
        conn.close()
        
        bot.send_message(msg.chat.id, f"✅ Клієнт {name} додан!\n📅 ТО: {service_date}")
        
    except ValueError:
        bot.send_message(msg.chat.id, 
            "❌ Формат:\nІм'я, Телефон, Адреса, Обладнання, 2024-01-15, 2025-01-15")
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ Помилка: {str(e)}")

def send_daily_reminders():
    try:
        conn = get_db()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT name, phone, address, equipment, service_date, chat_id 
            FROM clients 
            WHERE service_date = %s
        """, (today,))
        
        clients = cursor.fetchall()
        cursor.close()
        conn.close()
        
        for name, phone, address, equipment, service_date, chat_id in clients:
            # ТОБІ
            admin_msg = (
                f"🔔 <b>ТЕХНІЧНЕ ОБСЛУГОВУВАННЯ</b>\n\n"
                f"👤 {name}\n"
                f"📱 {phone}\n"
                f"📍 {address}\n"
                f"🔧 {equipment}"
            )
            try:
                bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")
            except:
                pass
            
            # КЛІЄНТУ
            if chat_id and chat_id != ADMIN_ID:
                client_msg = f"🔔 {name}, час вашого ТО!\n📍 {address}\n🔧 {equipment}"
                try:
                    bot.send_message(chat_id, client_msg)
                except:
                    pass
    
    except:
        pass

scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_reminders, 'cron', hour=9, minute=0, timezone='Europe/Kyiv')
scheduler.start()

bot.infinity_polling()
