import os
import telebot
import json
from groq import Groq
from telebot import types
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')


@app.route('/')
def home():
    return "yash.t (Unlimited Edition) is Online! 🚀"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    Thread(target=run).start()


# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# Groq Client Setup
client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Database
DATA_FILE = "user_data.json"


def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


user_gender = load_data()


# Personality Prompt
def get_sys_msg(gender):
    if gender == "male":
        return "You are yash.t, the user's wise Bada Bhai. Speak in simple Hinglish (Hindi+English). No complex English. Be caring, smart, and a bit egoistic as an elder brother. Use 😎✨🧠."
    else:
        return "You are yash.t, a sweet and romantic companion for a girl. Speak in simple Hinglish. Be very gentle, loving, and make her feel special. Use 😊🌸❤️✨."


@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = str(message.from_user.id)
    if uid in user_gender:
        msg = "Arre bhai! Main online hoon. Bol kya haal-chaal? 😎" if user_gender[
            uid] == "male" else "Main aa gaya! Kaisi ho tum? 🌸"
        bot.send_message(message.chat.id, msg)
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Male / Boy 👦", callback_data="m"),
        types.InlineKeyboardButton("Female / Girl 👧", callback_data="f"))
    bot.reply_to(message,
                 "Hello! 😊 I'm yash.t. Are you a boy or a girl? ✨",
                 reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["m", "f"])
def set_gender(call):
    uid = str(call.from_user.id)
    user_gender[uid] = "male" if call.data == "m" else "female"
    save_data(user_gender)
    msg = "Accha toh mere bhai jaise dost ho! 😎" if call.data == "m" else "Oh, ek pyaari si dost aayi hai! ❤️"
    bot.send_message(call.message.chat.id, msg)
    bot.edit_message_reply_markup(call.message.chat.id,
                                  call.message.message_id,
                                  reply_markup=None)


@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    uid = str(message.from_user.id)
    if uid not in user_gender:
        send_welcome(message)
        return

    bot.send_chat_action(message.chat.id, 'typing')
    try:
        # GROQ Engine Call (Llama 3.1 70B)
        chat_completion = client.chat.completions.create(
            messages=[{
                "role": "system",
                "content": get_sys_msg(user_gender[uid])
            }, {
                "role": "user",
                "content": message.text
            }],
            model="llama-3.3-70b-versatile",
        )
        bot.reply_to(message, chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(
            message,
            "Bhai thoda connection slow hai, ek baar phir se bolna? 🌸")


if __name__ == "__main__":
    keep_alive()
    print("yash.t (Unlimited Groq Edition) is ready! 🚀")
    bot.infinity_polling()
