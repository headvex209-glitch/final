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
#  CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

ADMIN_IDS = {"7212246299"} # Ensure your ID is here

ATTACK_API_URL = "http://YOUR_API_DOMAIN_OR_IP/api/attack?ip={ip}&port={port}&time={time}"
DASHBOARD_URL = "https://core.telegram.org/bots/webapps" 

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PERSISTENT DATA STORAGE (PREVENTS WIPING)
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
#  FILE HELPERS
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
                uid = parts[0]
                username = parts[1] if len(parts) > 1 else "Unknown"
                resellers[uid] = username
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
                    key = parts[0]
                    duration = float(parts[1])
                    max_uses = int(parts[2])
                    used_by = parts[3].split(",") if len(parts) > 3 and parts[3] else []
                    keys[key] = {"duration": duration, "max_uses": max_uses, "used_by": used_by}
    except FileNotFoundError: pass
    return keys

def save_trial_keys(keys: dict):
    with open(TRIAL_KEYS_FILE, "w") as f:
        for key, data in keys.items():
            used_str = ",".join(data["used_by"])
            f.write(f"{key}|{data['duration']}|{data['max_uses']}|{used_str}\n")

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
#  STATE & DATA
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
#  UTILITIES & CONVERSATION HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def fmt_expiry(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=ist).strftime('%d %b %Y • %I:%M %p IST')

def generate_key(prefix="KEY-") -> str:
    return prefix + secrets.token_hex(8).upper()

def is_admin(uid: str) -> bool:
    return uid in ADMIN_IDS

def is_reseller(uid: str) -> bool:
    return uid in resellers_data

def is_admin_or_reseller(uid: str) -> bool:
    return is_admin(uid) or is_reseller(uid)

def get_balance(uid: str) -> int:
    return balances.get(uid, 0)

def log_action(user_id: str, action: str, message=None):
    username = f"@{message.from_user.username}" if message and message.from_user.username else f"ID:{user_id}"
    now = datetime.datetime.now(ist).strftime("%d-%m-%Y %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] {username} | {action}\n")

def count_keys_generated_by(user_id: str) -> int:
    return sum(1 for k, v in key_history.items() if v["creator"] == user_id)

def no_access_msg() -> str:
    return "⛔ <b>𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗</b> ⛔\n\nYou don't have an active subscription!\nPlease use <code>/redeem</code> to activate."

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

# THIS PROTECTS THE BOT IF A USER CHANGES THEIR MIND MID-CONVERSATION
def is_cancel(message):
    if not message.text:
        bot.reply_to(message, "🚫 <b>Invalid input. Operation cancelled.</b>", parse_mode="HTML")
        return True
    if message.text.startswith('/'):
        bot.reply_to(message, "🚫 <b>Operation cancelled.</b>", parse_mode="HTML")
        return True
    return False

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    bot.reply_to(message, "✅ There is no active operation to cancel.", parse_mode="HTML")

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
#  UI & MENU HANDLERS
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
        btn_webapp = InlineKeyboardButton("🖥️ Launch Dashboard", web_app=WebAppInfo(url=DASHBOARD_URL))
        markup.add(btn_webapp)
    
    btn_attack = InlineKeyboardButton("🚀 Quick Attack", callback_data="ui_attack")
    btn_profile = InlineKeyboardButton("💳 My Profile", callback_data="ui_profile")
    btn_status = InlineKeyboardButton("📊 Live Status", callback_data="ui_status")
    btn_redeem = InlineKeyboardButton("🔑 Redeem Key", callback_data="ui_redeem")
    
    markup.add(btn_attack, btn_status)
    markup.add(btn_profile, btn_redeem)

    if is_paid:
        res = f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗯𝗮𝗰𝗸, {name}!</b> 🚀\n\n👑 <b>𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗔𝗰𝗰𝗲𝘀𝘀 𝗔𝗰𝘁𝗶𝘃𝗲</b>\n\n<i>Use the buttons below to control your account, or open your exclusive Web Dashboard!</i>"
    else:
        res = f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗕𝗼𝘁, {name}!</b> 🚀\n\n⛔ <b>𝗡𝗼 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻</b>\n\n<i>You need a premium key to use the attack dashboard. Please click 'Redeem Key' below to activate your access!</i>"

    bot.reply_to(message, res, reply_markup=markup, parse_mode="HTML")

@bot.callback_query_handler(func=lambda call: True)
def handle_inline_buttons(call):
    user_id = str(call.message.chat.id)
    username_str = f"@{call.from_user.username}" if call.from_user.username else "—"

    if call.data == "ui_profile":
        bot.send_message(user_id, build_profile_text(user_id, username_str), parse_mode="HTML")
        bot.answer_callback_query(call.id)
        
    elif call.data == "ui_status":
        attack_status(call.message) 
        bot.answer_callback_query(call.id)
        
    elif call.data == "ui_redeem":
        msg = bot.send_message(user_id, "🔑 <b>How to redeem a key:</b>\nSimply reply to this message with your key!\n\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, redeem_step)
        bot.answer_callback_query(call.id)
        
    elif call.data == "ui_attack":
        is_paid = user_id in allowed_user_ids and user_id in user_access and user_access[user_id]["expiry_time"] > time.time()
        if not is_paid:
            bot.send_message(user_id, no_access_msg(), parse_mode="HTML")
        else:
            msg = bot.send_message(user_id, "🎯 <b>Let's launch an attack!</b>\n\nPlease enter the <b>Target IP</b>:\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
            bot.register_next_step_handler(msg, attack_step_ip)
        bot.answer_callback_query(call.id)

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids or user_id not in user_access or user_access[user_id]["expiry_time"] < time.time():
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")

    try:
        data = json.loads(message.web_app_data.data)
        execute_attack(message, data.get("ip"), int(data.get("port")), int(data.get("time")))
    except Exception as e:
        bot.reply_to(message, f"❌ Error processing Web App data. Please check your dashboard setup.", parse_mode="HTML")

@bot.message_handler(commands=['help'])
def show_help(message):
    update_reseller_username(message)
    bot.reply_to(message,
        "📋 <b>𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦 𝗠𝗘𝗡𝗨</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 <b>USER COMMANDS</b>\n"
        "🔹 /start    → Open Control Panel\n"
        "🔹 /id       → Account info\n"
        "🔹 /plan     → Plan expiry\n"
        "🔹 /redeem   → Activate a key\n"
        "🔹 /mylogs   → Your activity\n"
        "🔹 /rules    → Usage rules\n"
        "🔹 /status   → Bot status\n\n"
        "🤝 <b>RESELLER & ADMIN</b>\n"
        "🔸 /prices   → Key price list\n"
        "🔸 /genkey   → Gen key(s)\n"
        "🔸 /listkeys → List unused keys\n"
        "🔸 /deletekey→ Delete a key\n"
        "🔸 /balance  → Check balance\n\n"
        "🛠 <b>ADMIN ONLY</b>\n"
        "⚙️ /admincmd → Admin panel\n"
        "━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['rules', 'prices', 'id', 'plan', 'myplan', 'mylogs'])
def handle_basic_commands(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    cmd = message.text.split()[0].lower()
    
    if cmd == '/rules':
        bot.reply_to(message, "📜 <b>𝗥𝗨𝗟𝗘𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━\n1️⃣ Do not share your key.\n2️⃣ One key = one account.\n3️⃣ Keys are non-refundable.\n━━━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")
    elif cmd == '/prices':
        if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
        lines = ["💰 <b>𝗞𝗘𝗬 𝗣𝗥𝗜𝗖𝗘 𝗟𝗜𝗦𝗧</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for plan, info in KEY_PLANS.items(): lines.append(f"📦 <b>{plan.ljust(8)}</b> - ₹{info['cost']}")
        bot.reply_to(message, "\n".join(lines), parse_mode="HTML")
    elif cmd == '/id':
        username_str = f"@{message.from_user.username}" if message.from_user.username else "—"
        bot.reply_to(message, build_profile_text(user_id, username_str), parse_mode="HTML")
    elif cmd in ['/plan', '/myplan']:
        if user_id not in allowed_user_ids: return bot.reply_to(message, no_access_msg(), parse_mode="HTML")
        if user_id in user_access: bot.reply_to(message, f"📅 <b>𝗬𝗢𝗨𝗥 𝗣𝗟𝗔𝗡</b>\n━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>Status:</b> Active\n⏳ <b>Expires:</b> {fmt_expiry(user_access[user_id]['expiry_time'])}", parse_mode="HTML")
        else: bot.reply_to(message, "⚠️ No expiry info found.")
    elif cmd == '/mylogs':
        if user_id not in allowed_user_ids: return bot.reply_to(message, no_access_msg(), parse_mode="HTML")
        try:
            with open(LOG_FILE, "r") as f: lines = f.readlines()
            user_logs = [l.strip() for l in lines if f"ID:{user_id}" in l or (message.from_user.username and f"@{message.from_user.username}" in l)]
            if user_logs:
                bot.reply_to(message, f"📋 <b>𝗬𝗢𝗨𝗥 𝗔𝗖𝗧𝗜𝗩𝗜𝗧𝗬</b>\n━━━━━━━━━━━━━━━━━━━━━━\n{chr(10).join(user_logs[-15:])}\n━━━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")
            else: bot.reply_to(message, "📝 No activity found.")
        except FileNotFoundError: bot.reply_to(message, "📝 No logs found.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL REDEEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['redeem'])
def redeem_cmd(message):
    parts = message.text.split()
    if len(parts) > 1:
        execute_redeem(message, parts[1].strip().upper())
    else:
        msg = bot.reply_to(message, "🔑 <b>Please enter the key you want to redeem:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, redeem_step)

def redeem_step(message):
    if is_cancel(message): return
    execute_redeem(message, message.text.strip().upper())

def execute_redeem(message, key):
    user_id = str(message.chat.id)
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_file_lines(ALL_USERS_FILE, all_known_users)

    plan_label = ""
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
        if user_id in t_data["used_by"]:
            return bot.reply_to(message, "❌ <b>You have already used this trial key!</b>", parse_mode="HTML")
        if len(t_data["used_by"]) >= t_data["max_uses"]:
            return bot.reply_to(message, "❌ <b>This trial key has reached its maximum uses!</b>", parse_mode="HTML")
            
        duration_sec = t_data["duration"]
        t_data["used_by"].append(user_id)
        save_trial_keys(trial_keys)
        trial_users.add(user_id)
        save_file_lines(TRIAL_USERS_FILE, trial_users)
        plan_label = "Free Trial"
    else:
        return bot.reply_to(message, "❌ <b>𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗞𝗘𝗬</b>\nThe key is incorrect or has already been used.", parse_mode="HTML")

    if user_id in user_access and user_access[user_id]["expiry_time"] > now.timestamp():
        current_exp = datetime.datetime.fromtimestamp(user_access[user_id]["expiry_time"])
        expiry_ts = (current_exp + timedelta(seconds=duration_sec)).timestamp()
    else:
        expiry_ts = (now + timedelta(seconds=duration_sec)).timestamp()

    if user_id not in allowed_user_ids:
        allowed_user_ids.append(user_id)
        save_users(allowed_user_ids)

    user_access[user_id] = {"expiry_time": expiry_ts}
    save_user_access(user_access)

    log_action(user_id, f"Redeemed key | plan={plan_label}", message)
    bot.reply_to(message, f"✅ <b>𝗞𝗘𝗬 𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n📦 <b>Plan:</b> {plan_label}\n⏳ <b>Expires:</b> {fmt_expiry(expiry_ts)}\n\n<i>Enjoy your access! Click /start to launch the dashboard.</i> 🎉", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL GENKEY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['genkey'])
def genkey_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
    
    parts = message.text.split()
    if len(parts) >= 2:
        amount = parts[2] if len(parts) >= 3 else "1"
        execute_genkey(message, parts[1], amount)
    else:
        plans = ", ".join(KEY_PLANS.keys())
        msg = bot.reply_to(message, f"📦 <b>Which plan do you want to generate?</b>\nAvailable: {plans}\n\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, genkey_plan_step)

def genkey_plan_step(message):
    if is_cancel(message): return
    plan = message.text.strip()
    if plan not in KEY_PLANS:
        return bot.reply_to(message, "❌ Invalid plan. Operation cancelled.", parse_mode="HTML")
    
    msg = bot.reply_to(message, "🔢 <b>How many keys do you want to generate?</b> (Enter 1 to 50)", parse_mode="HTML")
    bot.register_next_step_handler(msg, genkey_amount_step, plan)

def genkey_amount_step(message, plan):
    if is_cancel(message): return
    execute_genkey(message, plan, message.text.strip())

def execute_genkey(message, plan, amount_str):
    user_id = str(message.chat.id)
    if plan not in KEY_PLANS:
        return bot.reply_to(message, f"❌ Invalid Plan. Available: {', '.join(KEY_PLANS.keys())}", parse_mode="HTML")
    try:
        amount = int(amount_str)
        if amount < 1 or amount > 50: raise ValueError
    except ValueError:
        return bot.reply_to(message, "❌ Amount must be between 1 and 50.", parse_mode="HTML")

    total_cost = KEY_PLANS[plan]["cost"] * amount

    if is_reseller(user_id) and not is_admin(user_id):
        current_bal = get_balance(user_id)
        if current_bal < total_cost:
            return bot.reply_to(message, f"❌ <b>𝗜𝗡𝗦𝗨𝗙𝗙𝗜𝗖𝗜𝗘𝗡𝗧 𝗕𝗔𝗟𝗔𝗡𝗖𝗘</b>\n━━━━━━━━━━━━━━━━━━━━━━\n💰 <b>Needed:</b> ₹{total_cost}\n💵 <b>Balance:</b> ₹{current_bal}", parse_mode="HTML")
        balances[user_id] = current_bal - total_cost
        save_balances(balances)

    generated_keys = []
    for _ in range(amount):
        k = generate_key()
        active_keys[k] = plan
        key_history[k] = {"plan": plan, "creator": user_id, "status": "UNUSED"}
        generated_keys.append(k)
        
    save_keys(active_keys)
    save_key_history(key_history)
    
    log_action(user_id, f"Generated {amount} key(s) | plan={plan} | cost=₹{total_cost}", message)
    
    keys_gen = count_keys_generated_by(user_id)
    bal_info = f"\n💵 <b>Remaining Bal:</b> ₹{get_balance(user_id)}" if is_reseller(user_id) else ""
    keys_str = "\n".join([f"<code>{k}</code>" for k in generated_keys])
    
    res = (
        f"🔑 <b>𝗞𝗘𝗬(𝗦) 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗗!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟️ <b>Keys:</b>\n{keys_str}\n\n"
        f"📦 <b>Plan:</b> {plan}\n"
        f"💰 <b>Total Cost:</b> ₹{total_cost}{bal_info}\n"
        f"📊 <b>Total Keys Generated:</b> {keys_gen}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Tap the keys to copy them!</i>"
    )
    bot.reply_to(message, res, parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL RESELLER COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['deletekey'])
def delete_key_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) > 1:
        execute_deletekey(message, parts[1])
    else:
        msg = bot.reply_to(message, "🗑️ <b>Please enter the key you want to delete:</b>", parse_mode="HTML")
        bot.register_next_step_handler(msg, deletekey_step)

def deletekey_step(message):
    if is_cancel(message): return
    execute_deletekey(message, message.text.strip())

def execute_deletekey(message, key_str):
    user_id = str(message.chat.id)
    key = key_str.upper()
    if not is_admin(user_id) and key in key_history and key_history[key]["creator"] != user_id:
        return bot.reply_to(message, "❌ You can only delete keys that you generated.", parse_mode="HTML")
    
    if key in active_keys:
        del active_keys[key]
        save_keys(active_keys)
        if key in key_history:
            key_history[key]["status"] = "DELETED"
            save_key_history(key_history)
        bot.reply_to(message, f"✅ <b>Key successfully deleted.</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, "❌ Key not found or already used.", parse_mode="HTML")

@bot.message_handler(commands=['addbalance'])
def addbalance_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) >= 3:
        execute_balance_change(message, '/addbalance', parts[1], parts[2])
    else:
        msg = bot.reply_to(message, "👤 <b>Enter the Reseller's Telegram ID:</b>", parse_mode="HTML")
        bot.register_next_step_handler(msg, balance_step_id, '/addbalance')

def balance_step_id(message, cmd_type):
    if is_cancel(message): return
    target_id = message.text.strip()
    msg = bot.reply_to(message, "💰 <b>Enter the amount to add:</b>", parse_mode="HTML")
    bot.register_next_step_handler(msg, balance_step_amount, cmd_type, target_id)

def balance_step_amount(message, cmd_type, target_id):
    if is_cancel(message): return
    execute_balance_change(message, cmd_type, target_id, message.text.strip())

def execute_balance_change(message, cmd, target, amount_str):
    user_id = str(message.chat.id)
    try: amount = int(amount_str)
    except ValueError: return bot.reply_to(message, "❌ Amount must be a valid number.", parse_mode="HTML")

    if target not in resellers_data: return bot.reply_to(message, "❌ This user is not a reseller.", parse_mode="HTML")

    if amount <= 0: return bot.reply_to(message, "❌ Amount must be greater than 0.", parse_mode="HTML")
    balances[target] = get_balance(target) + amount
    
    save_balances(balances)
    new_bal = get_balance(target)
    target_username = resellers_data.get(target, "Unknown")
    
    log_action(user_id, f"Added ₹{amount} balance for reseller={target}", message)
    bot.reply_to(message, f"✅ <b>𝗕𝗮𝗹𝗮𝗻𝗰𝗲 Added!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n👤 <b>Reseller:</b> {target_username} (<code>{target}</code>)\n➕ <b>Added:</b> ₹{amount}\n💵 <b>New Balance:</b> ₹{new_bal}", parse_mode="HTML")
    try: bot.send_message(target, f"💰 <b>𝗬𝗼𝘂𝗿 𝗕𝗮𝗹𝗮𝗻𝗰𝗲 𝗛𝗮𝘀 𝗕𝗲𝗲𝗻 𝗨𝗽𝗱𝗮𝘁𝗲𝗱!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n➕ <b>Added:</b> ₹{amount}\n💵 <b>Current Balance:</b> ₹{new_bal}\n\n<i>You can now generate more keys using /genkey</i>", parse_mode="HTML")
    except: pass

@bot.message_handler(commands=['broadcast', 'bcpaid', 'bcreseller'])
def broadcast_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    parts = message.text.split(maxsplit=1)
    
    if len(parts) > 1:
        execute_broadcast(message, cmd, parts[1])
    else:
        msg = bot.reply_to(message, "📢 <b>Enter the message you want to broadcast:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        bot.register_next_step_handler(msg, broadcast_step, cmd)

def broadcast_step(message, cmd):
    if is_cancel(message): return
    execute_broadcast(message, cmd, message.text)

def execute_broadcast(message, cmd, text_content):
    if cmd == '/bcreseller': targets = list(resellers_data.keys())
    elif cmd == '/bcpaid': targets = allowed_user_ids
    else: targets = list(all_known_users | set(allowed_user_ids) | set(resellers_data.keys()) | ADMIN_IDS)
    
    text = f"📢 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗠𝗘𝗦𝗦𝗔𝗚𝗘</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n{text_content}\n\n━━━━━━━━━━━━━━━━━━━━━━"
    success, fail = 0, 0
    bot.reply_to(message, "⏳ <i>Broadcasting in progress...</i>", parse_mode="HTML")
    for t in targets:
        try:
            bot.send_message(t, text, parse_mode="HTML")
            success += 1
            time.sleep(0.1) 
        except: fail += 1

    bot.reply_to(message, f"📢 <b>Broadcast Done</b>\n✅ Sent: {success}\n❌ Failed: {fail}", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL ATTACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['attack'])
def attack_cmd(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    
    if user_id not in allowed_user_ids or user_id not in user_access or user_access[user_id]["expiry_time"] < time.time():
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")

    parts = message.text.split()
    if len(parts) == 4:
        execute_attack(message, parts[1], parts[2], parts[3])
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
    if user_id not in allowed_user_ids or user_id not in user_access or user_access[user_id]["expiry_time"] < time.time():
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")

    if not is_admin(user_id):
        if user_id in bgmi_cooldown:
            time_passed = (datetime.datetime.now() - bgmi_cooldown[user_id]).total_seconds()
            if time_passed < 60:
                return bot.reply_to(message, f"⏳ <b>Cooldown!</b> Wait {int(60 - time_passed)}s.", parse_mode="HTML")

    try: 
        port = int(port_str)
        time_val = int(time_str)
    except ValueError: return bot.reply_to(message, "❌ Port and Time must be valid numbers.", parse_mode="HTML")

    if time_val > 600: return bot.reply_to(message, "❌ Max time is 600s.", parse_mode="HTML")

    bgmi_cooldown[user_id] = datetime.datetime.now()
    active_attacks[user_id] = {"target": f"{target}:{port}", "start_time": time.time(), "duration": time_val}
    log_action(user_id, f"Attack → IP: {target} | Port: {port} | Time: {time_val}s", message)
    
    bot.reply_to(message, f"⚡ <b>𝗔𝘁𝘁𝗮𝗰𝗸 𝗦𝘁𝗮𝗿𝘁!</b> ⚡\n\n🎯 <b>Target:</b> <code>{target}:{port}</code>\n⏱️ <b>Time:</b> {time_val}s\n⏳ <b>Cooldown:</b> 60s\n\n📊 <i>Check progress with /status</i>", parse_mode="HTML")
    threading.Thread(target=run_attack_api, args=(message.chat.id, user_id, target, port, time_val)).start()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MISC ADMIN COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['admincmd'])
def admin_commands(message):
    if not is_admin(str(message.chat.id)): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    bot.reply_to(message,
        "🛠 <b>𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>USERS</b>\n"
        "🔹 <code>/add &lt;id&gt; &lt;plan&gt;</code> | <code>/remove &lt;id&gt;</code>\n"
        "🔹 <code>/paidusers</code> | <code>/freeusers</code>\n"
        "🔹 <code>/extendall &lt;num&gt; &lt;unit&gt;</code>\n"
        "🔹 <code>/trialkey &lt;num&gt; &lt;unit&gt; &lt;uses&gt;</code>\n"
        "🔹 <code>/killtrial</code>\n\n"
        "🤝 <b>RESELLERS</b>\n"
        "🔸 <code>/addreseller &lt;id&gt; [bal] [@user]</code>\n"
        "🔸 <code>/rmreseller &lt;id&gt;</code>\n"
        "🔸 <code>/resellerstats</code> | <code>/resellers</code>\n"
        "🔸 <code>/addbalance &lt;id&gt; &lt;₹&gt;</code>\n\n"
        "📢 <b>BROADCAST & DATA</b>\n"
        "🔊 <code>/broadcast &lt;msg&gt;</code> | <code>/bcpaid</code>\n"
        "📄 <code>/logs</code> | 🗑 <code>/clearlogs</code>\n"
        "📦 <code>/getdata</code> (Download Full Ledger)\n"
        "━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['paidusers', 'freeusers', 'resellerstats'])
def admin_reports(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    
    if cmd == '/paidusers':
        paid = [u for u in allowed_user_ids if u not in trial_users]
        if not paid: return bot.reply_to(message, "⚠️ No paid users found.", parse_mode="HTML")
        lines = ["💎 <b>𝗣𝗔𝗜𝗗 𝗨𝗦𝗘𝗥𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for uid in paid:
            exp = fmt_expiry(user_access[uid]['expiry_time']) if uid in user_access else "No expiry"
            lines.append(f"🆔 <code>{uid}</code> [Exp: {exp}]")
        bot.reply_to(message, "\n".join(lines)[:4000], parse_mode="HTML")
    elif cmd == '/freeusers':
        free = [u for u in all_known_users if u not in allowed_user_ids]
        if not free: return bot.reply_to(message, "⚠️ No free users found.", parse_mode="HTML")
        lines = [f"🆓 <b>𝗙𝗥𝗘𝗘 𝗨𝗦𝗘𝗥𝗦 ({len(free)})</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for uid in free: lines.append(f"🆔 <code>{uid}</code>")
        bot.reply_to(message, "\n".join(lines)[:4000], parse_mode="HTML")
    elif cmd == '/resellerstats':
        if not resellers_data: return bot.reply_to(message, "⚠️ No resellers found.", parse_mode="HTML")
        lines = ["📊 <b>𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥 𝗦𝗧𝗔𝗧𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for uid, username in resellers_data.items():
            lines.append(f"👤 {username} (<code>{uid}</code>)\n💵 Bal: ₹{get_balance(uid)} | 🔑 Keys Gen: {count_keys_generated_by(uid)}\n")
        bot.reply_to(message, "\n".join(lines)[:4000], parse_mode="HTML")

@bot.message_handler(commands=['getdata'])
def send_database_files(message):
    if not is_admin(str(message.chat.id)): return
    bot.reply_to(message, "📦 <b>Fetching Database Files & Building Ledger...</b>", parse_mode="HTML")
    
    summary_path = os.path.join(DATA_DIR, "Human_Readable_Ledger.txt")
    with open(summary_path, "w", encoding="utf-8") as sf:
        sf.write("========== 📊 MASTER DATABASE SUMMARY ==========\n")
        sf.write(f"Generated: {datetime.datetime.now(ist).strftime('%d %b %Y %I:%M %p')}\n\n")
        sf.write("========== 🤝 RESELLER LEDGERS ==========\n")
        if not resellers_data: sf.write("No resellers found.\n")
        for uid, username in resellers_data.items():
            sf.write(f"Reseller: {username} (ID: {uid})\n")
            sf.write(f"Leftover Balance: ₹{get_balance(uid)}\n")
            r_keys = {k: v for k, v in key_history.items() if v["creator"] == uid}
            unused = [k for k, v in r_keys.items() if v["status"] == "UNUSED"]
            used = [k for k, v in r_keys.items() if str(v["status"]).startswith("USED")]
            sf.write(f"Total Keys Generated: {len(r_keys)}\n")
            sf.write(f"  🟢 Unused Keys ({len(unused)}):\n")
            for k in unused: sf.write(f"    - {k} [{r_keys[k]['plan']}]\n")
            if not unused: sf.write("    (None)\n")
            sf.write(f"  🔴 Used Keys ({len(used)}):\n")
            for k in used: sf.write(f"    - {k} [{r_keys[k]['plan']}] -> {r_keys[k]['status']}\n")
            if not used: sf.write("    (None)\n")
            sf.write("-" * 45 + "\n\n")
        
        sf.write("========== 👤 ACTIVE PREMIUM USERS ==========\n")
        if not user_access: sf.write("No active paid users.\n")
        for uid, info in user_access.items(): sf.write(f"ID: {uid} | Expiry: {fmt_expiry(info['expiry_time'])}\n")
            
    files_to_send = [summary_path, USER_ACCESS_FILE, KEYS_FILE, RESELLERS_FILE, BALANCE_FILE, ALL_USERS_FILE, TRIAL_KEYS_FILE, TRIAL_USERS_FILE, LOG_FILE]
    found_files = False
    for fp in files_to_send:
        if os.path.exists(fp) and os.stat(fp).st_size > 0:
            with open(fp, "rb") as f: bot.send_document(message.chat.id, f, visible_file_name=os.path.basename(fp))
            found_files = True
    if not found_files: bot.reply_to(message, "⚠️ <b>No data files found yet.</b>", parse_mode="HTML")

@bot.message_handler(commands=['status'])
def status_cmd(message):
    attack_status(message)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    remove_expired_users()
    print("   ✅ Bot is running perfectly with Conversational Handlers & WebApp UI!")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
