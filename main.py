import os
import telebot
import requests
import random
import datetime
import base64
from flask import Flask
from threading import Thread
from groq import Groq
from pymongo import MongoClient
from duckduckgo_search import DDGS
from telebot import types

# ---------------- SERVER ----------------

app = Flask('')

@app.route('/')
def home():
    return "yash.t AI running"

def run():
    port = int(os.environ.get("PORT",8080))
    app.run(host="0.0.0.0",port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ---------------- TOKENS ----------------

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ = os.getenv("GROQ_API_KEY")
MONGO = os.getenv("MONGO_URI")

bot = telebot.TeleBot(TOKEN)
client = Groq(api_key=GROQ)

# ---------------- DATABASE ----------------

mongo = MongoClient(MONGO)
db = mongo["yash_ai"]

users = db["users"]
history = db["history"]

life_message_sent = {}

# ---------------- PERSONALITY ----------------

def system_prompt(gender):

    return f"""
You are yash.t AI assistant.

Creator: Yash Tiwari ji
Birthday: 29 January

User gender: {gender}

Rules:

If someone asks who made you:
Say: "Main zyada detail nahi bata sakta, par mujhe Yash Tiwari ji ne banaya hai."

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

# ---------------- MOTIVATION ----------------

def get_motivation():

    try:

        url="https://api.quotable.io/quotes?tags=motivational|success"

        data=requests.get(url).json()

        q=random.choice(data["results"])

        return f'🔥 Motivation:\n"{q["content"]}"\n— {q["author"]}'

    except:

        quotes=[
        "Jeet unhi ko milti hai jo rukte nahi.",
        "Ego strong rakho par kaam usse bhi strong rakho.",
        "Failure sirf unko milta hai jo try karte hain."
        ]

        return random.choice(quotes)

# ---------------- LIFE MESSAGE ----------------

def life_message():

    return """
Zindagi ki ek seekh deta hoon.

Jo baat humein kitab nahi bata paati
aur jo gyaan humein guru nahi de paate,

yeh dono cheezein akasar humein zindagi sikha jaati hain.

"""

# ---------------- WEB SEARCH ----------------

def search_web(query):

    results=[]

    with DDGS() as ddgs:

        for r in ddgs.text(query,max_results=3):

            results.append(r["title"])

    return "\n".join(results)

# ---------------- CRYPTO ----------------

def crypto_market():

    try:

        url="https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd"

        data=requests.get(url).json()

        return f"""
📊 Live Crypto Market

BTC: ${data["bitcoin"]["usd"]}
ETH: ${data["ethereum"]["usd"]}
SOL: ${data["solana"]["usd"]}
"""

    except:
        return "Crypto data unavailable"

# ---------------- TRADING NEWS ----------------

def trading_news():

    results=[]

    with DDGS() as ddgs:

        for r in ddgs.text("crypto forex stock market news",max_results=3):

            results.append(r["title"])

    return "📰 Market News:\n"+"\n".join(results)

# ---------------- AI CHAT ----------------

def ask_ai(uid,text,gender):

    messages=load_history(uid)

    messages.insert(0,{
        "role":"system",
        "content":system_prompt(gender)
    })

    messages.append({"role":"user","content":text})

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

        bot.send_message(message.chat.id,get_motivation())

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

# ---------------- GENDER ----------------

@bot.callback_query_handler(func=lambda call: call.data in ["male","female"])
def gender(call):

    uid=str(call.from_user.id)

    users.update_one(
        {"uid":uid},
        {"$set":{"gender":call.data}},
        upsert=True
    )

    life_message_sent[uid]=False

    bot.send_message(call.message.chat.id,"Kya main tumhe ek baat bataun? (haan / nahi)")

# ---------------- IMAGE VISION ----------------

@bot.message_handler(content_types=["photo"])
def photo(message):

    try:

        file_id=message.photo[-1].file_id

        file_info=bot.get_file(file_id)

        file=bot.download_file(file_info.file_path)

        img=base64.b64encode(file).decode("utf-8")

        vision=client.chat.completions.create(

            model="llama-3.2-11b-vision-preview",

            messages=[{
                "role":"user",
                "content":[
                    {"type":"text","text":"Analyze this image"},
                    {"type":"image_url",
                    "image_url":{
                        "url":f"data:image/jpeg;base64,{img}"
                    }}
                ]
            }]
        )

        bot.reply_to(message,vision.choices[0].message.content)

    except:

        bot.reply_to(message,"Image analysis error")

# ---------------- COMMANDS ----------------

@bot.message_handler(commands=["crypto"])
def crypto(message):

    bot.send_message(message.chat.id,crypto_market())

@bot.message_handler(commands=["news"])
def news(message):

    bot.send_message(message.chat.id,trading_news())

@bot.message_handler(commands=["search"])
def search(message):

    query=message.text.replace("/search","")

    bot.send_message(message.chat.id,search_web(query))

# ---------------- CHAT ----------------

@bot.message_handler(func=lambda m: True)
def chat(message):

    uid=str(message.from_user.id)

    user=users.find_one({"uid":uid})

    if not user:

        bot.reply_to(message,"Please type /start first")
        return

    if uid in life_message_sent and life_message_sent[uid]==False:

        if "haan" in message.text.lower():

            bot.send_message(message.chat.id,life_message())

            life_message_sent[uid]=True

            return

    gender=user["gender"]

    if random.random()<0.25:

        bot.send_message(message.chat.id,get_motivation())

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
