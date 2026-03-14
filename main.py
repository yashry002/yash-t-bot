import os
import telebot
import datetime
import base64
import requests
from flask import Flask
from threading import Thread
from groq import Groq
from telebot import types
from duckduckgo_search import DDGS
from pymongo import MongoClient

# ---------------- SERVER ----------------

app = Flask("")

@app.route("/")
def home():
    return "yash.t AI running 🚀"

def run():
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ---------------- TOKENS ----------------

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.environ.get("GROQ_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ_KEY)

# ---------------- DATABASE ----------------

mongo = MongoClient(MONGO_URI)
db = mongo["yash_ai"]

users = db["users"]
history = db["history"]

# ---------------- PERSONALITY ----------------

def system_prompt(gender):

    return f"""
You are yash.t AI assistant.

Creator: Yash Tiwari ji

Birthday: 29 January
Favorite class: 9th and 10th

User gender: {gender}

Rules:

If someone asks who made you:
Say: "Main zyada details nahi bata sakta, par mujhe Yash Tiwari ji ne banaya hai."

If someone asks about girlfriend:
Say: "Yeh meri personal cheez hai. Itna hint de sakta hoon ki meri bhi feelings hain."

Speak simple Hinglish.
"""

# ---------------- MEMORY ----------------

def save_chat(uid,user,bot_reply):

    history.insert_one({
        "uid":uid,
        "user":user,
        "bot":bot_reply,
        "time":datetime.datetime.now()
    })

def load_history(uid):

    chats = history.find({"uid":uid}).sort("time",-1).limit(6)

    msgs=[]

    for c in chats:

        msgs.append({"role":"user","content":c["user"]})
        msgs.append({"role":"assistant","content":c["bot"]})

    return msgs

# ---------------- SEARCH ----------------

def search_web(query):

    results=[]

    with DDGS() as ddgs:

        for r in ddgs.text(query,max_results=3):

            results.append(
                f"{r['title']}\n{r['body']}\n{r['href']}"
            )

    return "\n\n".join(results)

# ---------------- CRYPTO ----------------

def crypto_price(symbol):

    try:

        url=f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd"

        data=requests.get(url).json()

        price=data[symbol]["usd"]

        return f"{symbol.upper()} price: ${price}"

    except:

        return "Crypto data unavailable"

# ---------------- IMAGE GENERATION ----------------

def generate_image(prompt):

    url="https://image.pollinations.ai/prompt/"+prompt

    img=requests.get(url).content

    return img

# ---------------- AI CHAT ----------------

def ask_ai(uid,text,gender):

    messages=load_history(uid)

    messages.insert(0,{
        "role":"system",
        "content":system_prompt(gender)
    })

    messages.append({
        "role":"user",
        "content":text
    })

    res=client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )

    return res.choices[0].message.content

# ---------------- START ----------------

@bot.message_handler(commands=["start"])
def start(message):

    uid=str(message.from_user.id)

    user=users.find_one({"uid":uid})

    if user:

        bot.send_message(message.chat.id,"Main haazir hoon 😎")

    else:

        markup=types.InlineKeyboardMarkup()

        markup.add(
            types.InlineKeyboardButton("Boy 👦",callback_data="male"),
            types.InlineKeyboardButton("Girl 👧",callback_data="female")
        )

        bot.send_message(
            message.chat.id,
            "Hello! First tell me your gender 😊",
            reply_markup=markup
        )

# ---------------- SAVE GENDER ----------------

@bot.callback_query_handler(func=lambda call: call.data in ["male","female"])
def gender(call):

    uid=str(call.from_user.id)

    users.update_one(
        {"uid":uid},
        {"$set":{"gender":call.data}},
        upsert=True
    )

    bot.send_message(call.message.chat.id,"Identity saved ✅")

# ---------------- SEARCH COMMAND ----------------

@bot.message_handler(commands=["search"])
def search(message):

    query=message.text.replace("/search","")

    bot.send_message(message.chat.id,search_web(query))

# ---------------- CRYPTO ----------------

@bot.message_handler(commands=["crypto"])
def crypto(message):

    coin=message.text.replace("/crypto","")

    bot.send_message(message.chat.id,crypto_price(coin))

# ---------------- IMAGE ----------------

@bot.message_handler(commands=["image"])
def image(message):

    prompt=message.text.replace("/image","")

    bot.send_message(message.chat.id,"Generating image...")

    img=generate_image(prompt)

    bot.send_photo(message.chat.id,img)

# ---------------- PHOTO VISION ----------------

@bot.message_handler(content_types=["photo"])
def photo(message):

    try:

        bot.send_chat_action(message.chat.id,"typing")

        file_id=message.photo[-1].file_id

        file_info=bot.get_file(file_id)

        file=bot.download_file(file_info.file_path)

        img=base64.b64encode(file).decode("utf-8")

        vision=client.chat.completions.create(

            model="llama-3.2-11b-vision-preview",

            messages=[

                {
                    "role":"user",
                    "content":[
                        {"type":"text","text":"Analyze this image and answer user question"},
                        {
                            "type":"image_url",
                            "image_url":{
                                "url":f"data:image/jpeg;base64,{img}"
                            }
                        }
                    ]
                }

            ]

        )

        bot.reply_to(message,vision.choices[0].message.content)

    except:

        bot.reply_to(message,"Image analysis error")

# ---------------- NORMAL CHAT ----------------

@bot.message_handler(func=lambda m: True)
def chat(message):

    uid=str(message.from_user.id)

    user=users.find_one({"uid":uid})

    if not user:

        bot.reply_to(message,"Please type /start first")

        return

    gender=user["gender"]

    reply=ask_ai(uid,message.text,gender)

    bot.reply_to(message,reply)

    save_chat(uid,message.text,reply)

# ---------------- RUN ----------------

if __name__=="__main__":

    keep_alive()

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60,
        skip_pending=True
    )
