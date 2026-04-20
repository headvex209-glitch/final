#!/usr/bin/python3
import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import datetime
import os
import time
import secrets
import threading
import json
from datetime import timedelta
from threading import Timer
import pytz

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG (Optimized Threading)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=32)

ADMIN_IDS = {"7212246299"} 

ATTACK_API_URL = "http://YOUR_API_DOMAIN_OR_IP/api/attack?ip={ip}&port={port}&time={time}"
DASHBOARD_URL = "https://zeromiss.netlify.app/" 

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PERSISTENT DATA STORAGE 
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATA_DIR = "/data" if os.path.exists("/data") else "data"
os.makedirs(DATA_DIR, exist_ok=True)

USER_FILE        = os.path.join(DATA_DIR, "users.txt")
LOG_FILE         = os.path.join(DATA_DIR, "log.txt")
USER_ACCESS_FILE = os.path.join(DATA_DIR, "users_access.txt")
KEYS_FILE        = os.path.join(DATA_DIR, "keys.txt")
KEY_HISTORY_FILE = os.path.join(DATA_DIR, "key_history.txt") 
RESELLERS_FILE   = os.path.join(DATA_DIR, "resellers.txt") 
BALANCE_FILE     = os.path.join(DATA_DIR, "balances.txt")
ALL_USERS_FILE   = os.path.join(DATA_DIR, "all_users.txt")
TRIAL_KEYS_FILE  = os.path.join(DATA_DIR, "trial_keys.txt")
TRIAL_USERS_FILE = os.path.join(DATA_DIR, "trial_users.txt")

ist = pytz.timezone('Asia/Kolkata')

KEY_PLANS = {
    "12hr":  {"duration": timedelta(hours=12), "cost": 30},
    "1day":  {"duration": timedelta(days=1),   "cost": 60},
    "3day":  {"duration": timedelta(days=3),   "cost": 180},
    "7day":  {"duration": timedelta(days=7),   "cost": 300},
    "30day": {"duration": timedelta(days=30),  "cost": 1000},
    "60day": {"duration": timedelta(days=60),  "cost": 1900},
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA HELPERS (IO)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def read_file_lines(filename) -> set:
    try:
        with open(filename, "r") as f: return {l.strip() for l in f if l.strip()}
    except FileNotFoundError: return set()

def save_file_lines(filename, data_set: set):
    with open(filename, "w") as f:
        for item in data_set: f.write(f"{item}\n")

def read_users() -> list:
    try:
        with open(USER_FILE, "r") as f: return [l.strip() for l in f if l.strip()]
    except FileNotFoundError: return []

def save_users(users: list):
    with open(USER_FILE, "w") as f:
        for uid in users: f.write(f"{uid}\n")

def read_user_access() -> dict:
    data = {}
    try:
        with open(USER_ACCESS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    uid, expiry = line.split(":", 1)
                    data[uid] = {"expiry_time": float(expiry)}
    except (FileNotFoundError, ValueError): pass
    return data

def save_user_access(data: dict):
    with open(USER_ACCESS_FILE, "w") as f:
        for uid, info in data.items(): f.write(f"{uid}:{info['expiry_time']}\n")

def read_keys() -> dict:
    keys = {}
    try:
        with open(KEYS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    parts = line.split("|", 1)
                    keys[parts[0].strip()] = parts[1].strip()
    except FileNotFoundError: pass
    return keys

def save_keys(keys: dict):
    with open(KEYS_FILE, "w") as f:
        for key, plan in keys.items(): f.write(f"{key}|{plan}\n")

def read_resellers() -> dict:
    resellers = {}
    try:
        with open(RESELLERS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    parts = line.split("|")
                    resellers[parts[0]] = parts[1] if len(parts) > 1 else "Unknown"
    except FileNotFoundError: pass
    return resellers

def save_resellers(resellers_dict: dict):
    with open(RESELLERS_FILE, "w") as f:
        for uid, username in resellers_dict.items(): f.write(f"{uid}|{username}\n")

def read_key_history() -> dict:
    history = {}
    try:
        with open(KEY_HISTORY_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split("|")
                if len(parts) >= 4:
                    history[parts[0]] = {"plan": parts[1], "creator": parts[2], "status": parts[3]}
    except FileNotFoundError: pass
    return history

def save_key_history(history_dict: dict):
    with open(KEY_HISTORY_FILE, "w") as f:
        for key, data in history_dict.items():
            f.write(f"{key}|{data['plan']}|{data['creator']}|{data['status']}\n")

def read_trial_keys() -> dict:
    keys = {}
    try:
        with open(TRIAL_KEYS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                parts = line.split("|")
                if len(parts) >= 3:
                    keys[parts[0]] = {"duration": float(parts[1]), "max_uses": int(parts[2]), "used_by": parts[3].split(",") if len(parts) > 3 and parts[3] else []}
    except (FileNotFoundError, ValueError): pass
    return keys

def save_trial_keys(keys: dict):
    with open(TRIAL_KEYS_FILE, "w") as f:
        for key, data in keys.items():
            f.write(f"{key}|{data['duration']}|{data['max_uses']}|{','.join(data['used_by'])}\n")

def read_balances() -> dict:
    balances = {}
    try:
        with open(BALANCE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    uid, bal = line.split(":", 1)
                    try: balances[uid.strip()] = int(bal.strip())
                    except ValueError: balances[uid.strip()] = 0
    except FileNotFoundError: pass
    return balances

def save_balances(balances: dict):
    with open(BALANCE_FILE, "w") as f:
        for uid, bal in balances.items(): f.write(f"{uid}:{bal}\n")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATE & CACHE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
all_known_users: set   = read_file_lines(ALL_USERS_FILE)
trial_users: set       = read_file_lines(TRIAL_USERS_FILE)
allowed_user_ids: list = read_users()
user_access: dict      = read_user_access()
active_keys: dict      = read_keys()
key_history: dict      = read_key_history() 
resellers_data: dict   = read_resellers()   
trial_keys: dict       = read_trial_keys()
balances: dict         = read_balances()
bgmi_cooldown = {} 
active_attacks = {} 
active_prompts = {} # Initialized

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UTILITIES & UI HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fmt_expiry(ts: float) -> str: return datetime.datetime.fromtimestamp(ts, tz=ist).strftime('%d %b %Y • %I:%M %p IST')
def generate_key(prefix="KEY-") -> str: return prefix + secrets.token_hex(8).upper()
def is_admin(uid: str) -> bool: return uid in ADMIN_IDS
def is_reseller(uid: str) -> bool: return uid in resellers_data
def is_admin_or_reseller(uid: str) -> bool: return is_admin(uid) or is_reseller(uid)
def get_balance(uid: str) -> int: return balances.get(uid, 0)
def no_access_msg() -> str: return "⛔ <b>𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗</b> ⛔\n\nYou don't have an active subscription!\nPlease use <code>/redeem</code> to activate."
def admin_only_msg() -> str: return "🛑 <b>Error:</b> Restricted to <b>Admins</b> only."
def admin_reseller_only_msg() -> str: return "🛑 <b>Error:</b> Restricted to <b>Admins</b> and <b>Resellers</b>."

def log_action(user_id: str, action: str, message=None):
    username = f"@{message.from_user.username}" if message and message.from_user.username else f"ID:{user_id}"
    now = datetime.datetime.now(ist).strftime("%d-%m-%Y %H:%M:%S")
    with open(LOG_FILE, "a") as f: f.write(f"[{now}] {username} | {action}\n")

def count_keys_generated_by(user_id: str) -> int:
    return sum(1 for k, v in key_history.items() if v["creator"] == user_id)

def update_reseller_username(message):
    uid = str(message.chat.id)
    if uid in resellers_data and message.from_user.username:
        new_username = f"@{message.from_user.username}"
        if resellers_data[uid] != new_username:
            resellers_data[uid] = new_username
            save_resellers(resellers_data)

def build_profile_text(user_id, username_str):
    role = "👑 Admin" if is_admin(user_id) else ("🤝 Reseller" if is_reseller(user_id) else "👤 User")
    expiry = f"⏳ <b>Expires:</b> {fmt_expiry(user_access[user_id]['expiry_time'])}" if user_id in user_access else "⏳ <b>Expires:</b> ❌ No Active Plan"
    bal = f"\n💵 <b>Balance:</b> ₹{get_balance(user_id)}" if is_reseller(user_id) or is_admin(user_id) else ""
    return f"👤 <b>𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗜𝗡𝗙𝗢</b>\n━━━━━━━━━━━━━━━━━━━━━━\n🆔 <b>ID:</b> <code>{user_id}</code>\n📛 <b>Username:</b> {username_str}\n🎭 <b>Role:</b> {role}\n{expiry}{bal}\n━━━━━━━━━━━━━━━━━━━━━━"

def is_cancel(message):
    user_id = str(message.chat.id)
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass

    if not message.text or message.text.startswith('/'):
        if user_id in active_prompts:
            try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
            except: pass
            del active_prompts[user_id]
            
        bot.clear_step_handler_by_chat_id(message.chat.id)
        msg = bot.send_message(message.chat.id, "🚫 <b>Operation cancelled.</b>", parse_mode="HTML")
        animated_delete(message.chat.id, msg.message_id, delay=3)
        return True
    return False

# --- ANIMATED CLEANUP ---
def animated_delete(chat_id, message_id, delay=5):
    def task():
        time.sleep(delay)
        try:
            bot.edit_message_text("⏳ <i>Cleaning up...</i>", chat_id, message_id, parse_mode="HTML")
            time.sleep(0.5)
            bot.delete_message(chat_id, message_id)
        except: pass
    threading.Thread(target=task).start()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MENUS & COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_main_menu(user_id, is_paid):
    markup = InlineKeyboardMarkup(row_width=2)
    if is_paid:
        markup.add(InlineKeyboardButton("🖥️ Launch Web Dashboard", web_app=WebAppInfo(url=DASHBOARD_URL)))
    markup.add(
        InlineKeyboardButton("🚀 Quick Attack", callback_data="ui_attack"),
        InlineKeyboardButton("📊 Live Status", callback_data="ui_status"),
        InlineKeyboardButton("💳 My Profile", callback_data="ui_profile"),
        InlineKeyboardButton("🔑 Redeem Key", callback_data="ui_redeem"),
        InlineKeyboardButton("📜 Rules", callback_data="ui_rules"),
        InlineKeyboardButton("📅 My Plan", callback_data="ui_plan")
    )
    if is_reseller(user_id) or is_admin(user_id):
        markup.add(InlineKeyboardButton("🤝 Open Reseller Panel", callback_data="menu_reseller"))
    if is_admin(user_id):
        markup.add(InlineKeyboardButton("🛠 Open Master Admin Panel", callback_data="menu_admin"))
    return markup

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_file_lines(ALL_USERS_FILE, all_known_users)

    name = message.from_user.first_name
    is_paid = user_id in allowed_user_ids and user_access.get(user_id, {}).get("expiry_time", 0) > time.time()
    
    res = f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲, {name}!</b>\n\n" + ("👑 <b>𝗣𝗿𝗲𝗺𝗶𝘂𝗺 Active</b>" if is_paid else "⛔ <b>𝗡𝗼 Active Plan</b>")
    bot.send_message(user_id, res, reply_markup=get_main_menu(user_id, is_paid), parse_mode="HTML")
    try: bot.delete_message(user_id, message.message_id)
    except: pass

# ... [Keep your other command handlers as written, they are logically sound] ...

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPIRY MANAGEMENT 
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def remove_expired_users():
    current_time = time.time()
    expired = [uid for uid, info in user_access.items() if info["expiry_time"] <= current_time]

    for uid in expired:
        try: bot.send_message(uid, "⏰ <b>Your access plan has expired!</b>", parse_mode="HTML")
        except: pass
        user_access.pop(uid, None)
        if uid in allowed_user_ids: allowed_user_ids.remove(uid)

    if expired:
        save_users(allowed_user_ids)
        save_user_access(user_access)

    Timer(60, remove_expired_users).start()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    remove_expired_users()
    print("✅ Bot is running perfectly!")
    bot.infinity_polling(skip_pending=True)
