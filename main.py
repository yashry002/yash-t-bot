import os
import telebot
import json
import base64
from groq import Groq
from telebot import types
from flask import Flask
from threading import Thread

# --- WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "yash.t (Vision Edition) is Online! 🚀"

def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

client = Groq(api_key=GROQ_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Database
DATA_FILE = "user_data.json"
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f)

user_gender = load_data()

# Personality Prompts
def get_sys_msg(gender):
    if gender == "male":
        return "You are yash.t, the user's wise Bada Bhai. Speak in simple Hinglish. You are smart and caring. If an image is sent, describe it like a cool brother. Use 😎✨🧠."
    else:
        return "You are yash.t, a sweet and romantic companion. Speak in simple Hinglish. Be very gentle and loving when describing images. Use 😊🌸❤️✨."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    uid = str(message.from_user.id)
    if uid in user_gender:
        msg = "Arre bhai! Main online hoon. Bol kya hua ? koi problem?? 😎" if user_gender[uid] == "male" else "Main aa gaya! Kaisi ho tum? 🌸"
        bot.send_message(message.chat.id, msg)
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Male / Boy 👦", callback_data="m"),
               types.InlineKeyboardButton("Female / Girl 👧", callback_data="f"))
    bot.reply_to(message, "Hello! 😊 I'm yash.t. Are you a boy or a girl? ✨", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["m", "f"])
def set_gender(call):
    uid = str(call.from_user.id)
    user_gender[uid] = "male" if call.data == "m" else "female"
    save_data(user_gender)
    msg = "Accha toh mere bhai jaise dost ho! 😎" if call.data == "m" else "Oh, ek pyaari si dost aayi hai! ❤️"
    bot.send_message(call.message.chat.id, msg)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# --- IMAGE HANDLER (Naya Feature! 📸) ---
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    uid = str(message.from_user.id)
    if uid not in user_gender:
        send_welcome(message)
        return

    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        # Photo download karna
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Image ko base64 mein badalna (Groq ke liye)
        base64_image = base64.b64encode(downloaded_file).decode('utf-8')
        
        # User ka caption (agar kuch likha ho)
        user_caption = message.caption if message.caption else "Is image mein kya hai?"

        # Vision Model ka use (llama-3.2-11b-vision-preview)
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{get_sys_msg(user_gender[uid])}\n\nUser asked: {user_caption}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            model="llama-3.2-11b-vision-preview",
        )
        bot.reply_to(message, response.choices[0].message.content)

    except Exception as e:
        print(f"Vision Error: {e}")
        bot.reply_to(message, "Bhai, meri aankhon mein thoda kachra chala gaya hai (Technical error). Ek baar phir se photo bhejo? 🌸")

# --- TEXT HANDLER ---
@bot.message_handler(func=lambda message: True)
def handle_chat(message):
    uid = str(message.from_user.id)
    if uid not in user_gender:
        send_welcome(message)
        return
    
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": get_sys_msg(user_gender[uid])},
                {"role": "user", "content": message.text}
            ],
            model="llama-3.3-70b-versatile",
        )
        bot.reply_to(message, chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Text Error: {e}")
        bot.reply_to(message, "Bhai thoda connection slow hai, ek baar phir se bolna? 🌸")

if __name__ == "__main__":
    keep_alive()
    print("yash.t (Vision Edition) is ready! 🚀")
    bot.infinity_polling()
