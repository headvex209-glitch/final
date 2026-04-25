#!/usr/bin/python3

import requests
import telebot
from flask import Flask, request, jsonify
from flask_cors import CORS
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
import sys

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONFIG (Optimized Threading)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BOT_TOKEN = os.environ.get("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ FATAL ERROR: BOT_TOKEN is missing! Check your host's environment variables.")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=32)

# 🔥 ULTRA-FAST UI PATCH 🔥
original_delete = bot.delete_message
def async_delete(*args, **kwargs):
    def task():
        try: original_delete(*args, **kwargs)
        except Exception: pass
    threading.Thread(target=task).start()
bot.delete_message = async_delete

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
APK_KEYS_FILE    = os.path.join(DATA_DIR, "apk_keys.txt")          
APK_HISTORY_FILE = os.path.join(DATA_DIR, "apk_key_history.txt")   
RESELLERS_FILE   = os.path.join(DATA_DIR, "resellers.txt") 
BALANCE_FILE     = os.path.join(DATA_DIR, "balances.txt")
ALL_USERS_FILE   = os.path.join(DATA_DIR, "all_users.txt")
TRIAL_KEYS_FILE  = os.path.join(DATA_DIR, "trial_keys.txt")
TRIAL_USERS_FILE = os.path.join(DATA_DIR, "trial_users.txt")
PROFILES_FILE    = os.path.join(DATA_DIR, "profiles.txt")
ist = pytz.timezone('Asia/Kolkata')

# --- UPDATED PRICE LISTS ---
BOT_KEY_PLANS = {
    "12hr":  {"duration": timedelta(hours=12), "cost": 30},
    "1day":  {"duration": timedelta(days=1),   "cost": 60},
    "3day":  {"duration": timedelta(days=3),   "cost": 180},
    "7day":  {"duration": timedelta(days=7),   "cost": 300},
    "30day": {"duration": timedelta(days=30),  "cost": 850},
    "60day": {"duration": timedelta(days=60),  "cost": 9999999999},
}

APK_KEY_PLANS = {
    "12hr":  {"duration": timedelta(hours=12), "cost": 40},
    "1day":  {"duration": timedelta(days=1),   "cost": 70},
    "3day":  {"duration": timedelta(days=3),   "cost": 180},
    "7day":  {"duration": timedelta(days=7),   "cost": 350},
    "30day": {"duration": timedelta(days=30),  "cost": 900},
    "60day": {"duration": timedelta(days=60),  "cost": 9999999999},
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DATA HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def read_profiles() -> dict:
    profiles = {}
    try:
        with open(PROFILES_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("|", 1)
                if len(parts) == 2: profiles[parts[0]] = parts[1]
    except FileNotFoundError: pass
    return profiles

def save_profiles(profiles: dict):
    with open(PROFILES_FILE, "w") as f:
        for uid, name in profiles.items(): f.write(f"{uid}|{name}\n")

def track_profile(user):
    uid = str(user.id)
    name = f"@{user.username}" if user.username else str(user.first_name)
    if user_profiles.get(uid) != name:
        user_profiles[uid] = name
        save_profiles(user_profiles)

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

def read_keys(filename) -> dict:
    keys = {}
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if "|" in line:
                    parts = line.split("|", 1)
                    keys[parts[0].strip()] = parts[1].strip()
    except FileNotFoundError: pass
    return keys

def save_keys(filename, keys: dict):
    with open(filename, "w") as f:
        for key, plan in keys.items(): f.write(f"{key}|{plan}\n")

def read_resellers() -> dict:
    resellers = {}
    try:
        with open(RESELLERS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split("|")
                # NEW FORMAT: uid | tier | username
                if len(parts) >= 3:
                    resellers[parts[0]] = {"tier": parts[1], "username": parts[2]}
                # MIGRATION: Auto-converts old data to MASTER
                elif len(parts) == 2:
                    resellers[parts[0]] = {"tier": "MASTER", "username": parts[1]}
    except FileNotFoundError: pass
    return resellers

def save_resellers(resellers_dict: dict):
    with open(RESELLERS_FILE, "w") as f:
        for uid, data in resellers_dict.items(): 
            f.write(f"{uid}|{data['tier']}|{data['username']}\n")

def read_key_history(filename) -> dict:
    history = {}
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                parts = line.split("|")
                if len(parts) >= 4:
                    history[parts[0]] = {"plan": parts[1], "creator": parts[2], "status": parts[3]}
    except FileNotFoundError: pass
    return history

def save_key_history(filename, history_dict: dict):
    with open(filename, "w") as f:
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
user_profiles = read_profiles()
all_known_users: set   = read_file_lines(ALL_USERS_FILE)
trial_users: set       = read_file_lines(TRIAL_USERS_FILE)
allowed_user_ids: list = read_users()
user_access: dict      = read_user_access()
active_keys: dict      = read_keys(KEYS_FILE)               
key_history: dict      = read_key_history(KEY_HISTORY_FILE) 
active_apk_keys: dict  = read_keys(APK_KEYS_FILE)           
apk_key_history: dict  = read_key_history(APK_HISTORY_FILE) 
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
    bot_keys = sum(1 for k, v in key_history.items() if v["creator"] == user_id)
    apk_keys = sum(1 for k, v in apk_key_history.items() if v["creator"] == user_id)
    return bot_keys + apk_keys

def update_reseller_username(message):
    uid = str(message.chat.id)
    if uid in resellers_data and message.from_user.username:
        new_username = f"@{message.from_user.username}"
        if resellers_data[uid]["username"] != new_username:
            resellers_data[uid]["username"] = new_username
            save_resellers(resellers_data)

def build_profile_text(user_id, username_str):
    if is_admin(user_id):
        role = "👑 Admin"
    elif is_reseller(user_id):
        tier = resellers_data[user_id]["tier"]
        role = f"🤝 {tier} Reseller"
    else:
        role = "👤 User"
        
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

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    user_id = str(message.chat.id)
    bot.clear_step_handler_by_chat_id(message.chat.id)
    msg = bot.send_message(user_id, "✅ Active operations cancelled.", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=3)

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
def animated_delete(chat_id, message_id, delay=5):
    def task():
        time.sleep(delay)
        try: bot.delete_message(chat_id, message_id)
        except Exception: pass
    threading.Thread(target=task).start()

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

def get_reseller_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🛠 Generate Keys", callback_data="cb_genkey"),
        InlineKeyboardButton("📦 Unused Keys", callback_data="cb_listkeys"),
        InlineKeyboardButton("💰 My Balance", callback_data="cb_balance"),
        InlineKeyboardButton("🛒 Price List", callback_data="cb_prices"),
        InlineKeyboardButton("🗑 Delete a Key", callback_data="cb_delkey")
    )
    markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main"))
    return markup

active_prompts = {}

def get_admin_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Add User", callback_data="cb_adduser"),
        InlineKeyboardButton("➖ Remove User", callback_data="cb_rmuser"),
        InlineKeyboardButton("💎 Paid Users", callback_data="cb_paidusers"),
        InlineKeyboardButton("🆓 Free Users", callback_data="cb_freeusers"),
        InlineKeyboardButton("⏳ Trial Users", callback_data="cb_trialusers"),
        InlineKeyboardButton("📊 Reseller Stats", callback_data="cb_rstats"),
        InlineKeyboardButton("🤝 Add Reseller", callback_data="cb_addres"),
        InlineKeyboardButton("🛑 Remove Reseller", callback_data="cb_rmres"),
        InlineKeyboardButton("💰 Add Funds", callback_data="cb_addbal"),
        InlineKeyboardButton("⚙️ Set Balance", callback_data="cb_setbal"),
        InlineKeyboardButton("🎁 Gen Trial Key", callback_data="cb_trialkey"),
        InlineKeyboardButton("💀 Kill All Trials", callback_data="cb_killtrial"),
        InlineKeyboardButton("📢 Broadcast", callback_data="cb_broadcast"),
        InlineKeyboardButton("📦 Download DB", callback_data="cb_getdata")
    )
    markup.add(InlineKeyboardButton("⚠️ Advanced / Danger Zone", callback_data="menu_danger"))
    markup.add(InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main"))
    return markup

def get_danger_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⏳ Extend All Users", callback_data="cb_extendall"),
        InlineKeyboardButton("🗑 Clear Logs", callback_data="cb_clearlogs")
    )
    markup.add(InlineKeyboardButton("⚠️ WIPE ALL DATABASE ⚠️", callback_data="cb_clearall"))
    markup.add(InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="menu_admin"))
    return markup

def get_broadcast_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🌍 Everyone", callback_data="bc_all"),
        InlineKeyboardButton("💎 Paid Users", callback_data="bc_paid"),
        InlineKeyboardButton("🆓 Free Users", callback_data="bc_free"),
        InlineKeyboardButton("🤝 Resellers", callback_data="bc_reseller")
    )
    markup.add(InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="menu_admin"))
    return markup

@bot.message_handler(commands=['start'])
def welcome_start(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    track_profile(message.from_user)
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_file_lines(ALL_USERS_FILE, all_known_users)

    name = message.from_user.first_name
    is_paid = user_id in allowed_user_ids and user_access.get(user_id, {}).get("expiry_time", 0) > time.time()
    
    if is_paid: 
        res = f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝗯𝗮𝗰𝗸, {name}!</b> 🚀\n\n👑 <b>𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗔𝗰𝗰𝗲𝘀𝘀 𝗔𝗰𝘁𝗶𝘃𝗲</b>\n\n<i>Use the buttons below to manage your account.</i>"
    else: 
        res = f"🚀 <b>𝗪𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗣𝗿𝗲𝗺𝗶𝘂𝗺 𝗕𝗼𝘁, {name}!</b> 🚀\n\n⛔ <b>𝗡𝗼 𝗔𝗰𝘁𝗶𝘃𝗲 𝗣𝗹𝗮𝗻</b>\n\n<i>Please click 'Redeem Key' below to activate your access!</i>"

    bot.send_message(user_id, res, reply_markup=get_main_menu(user_id, is_paid), parse_mode="HTML")
    try: bot.delete_message(user_id, message.message_id)
    except: pass
    
@bot.message_handler(commands=['help'])
def show_help(message):
    update_reseller_username(message)
    msg = bot.send_message(message.chat.id, "Please use the /start command to access the menu.", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

@bot.message_handler(commands=['rules', 'prices', 'id', 'plan', 'myplan', 'mylogs'])
def handle_basic_commands(message):
    msg = bot.send_message(message.chat.id, "Please use the buttons in the /start menu.", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL USER COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['redeem'])
def redeem_cmd(message):
    msg = bot.send_message(message.chat.id, "Please use the Redeem button in the /start menu.", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

def redeem_step(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
        
    execute_redeem(message, message.text.strip().upper())

def execute_redeem(message, key):
    user_id = str(message.chat.id)
    if user_id not in all_known_users:
        all_known_users.add(user_id)
        save_file_lines(ALL_USERS_FILE, all_known_users)

    if key.startswith("FZ-APK-"):
        msg = bot.send_message(user_id, "❌ <b>This is an APK key!</b>\nPlease paste this key directly inside the Android App to login.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=8)

    now = datetime.datetime.now(ist)
    if key in active_keys:
        plan_label = active_keys[key]
        duration_sec = BOT_KEY_PLANS[plan_label]["duration"].total_seconds()
        if key in key_history:
            key_history[key]["status"] = f"USED_BY:{user_id}"
            save_key_history(KEY_HISTORY_FILE, key_history)
        del active_keys[key]
        save_keys(KEYS_FILE, active_keys)
        if user_id in trial_users:
            trial_users.remove(user_id)
            save_file_lines(TRIAL_USERS_FILE, trial_users)
    elif key in trial_keys:
        t_data = trial_keys[key]
        if user_id in t_data["used_by"]: 
            msg = bot.send_message(user_id, "❌ You already used this trial!", parse_mode="HTML")
            return animated_delete(user_id, msg.message_id, delay=5)
        if len(t_data["used_by"]) >= t_data["max_uses"]: 
            msg = bot.send_message(user_id, "❌ Trial key is full!", parse_mode="HTML")
            return animated_delete(user_id, msg.message_id, delay=5)
        duration_sec = t_data["duration"]
        t_data["used_by"].append(user_id)
        save_trial_keys(trial_keys)
        trial_users.add(user_id)
        save_file_lines(TRIAL_USERS_FILE, trial_users)
        plan_label = "Free Trial"
    else: 
        msg = bot.send_message(user_id, "❌ <b>𝗜𝗡𝗩𝗔𝗟𝗜𝗗 𝗞𝗘𝗬</b>", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)

    current_exp = user_access.get(user_id, {}).get("expiry_time", now.timestamp())
    expiry_ts = (datetime.datetime.fromtimestamp(max(current_exp, now.timestamp())) + timedelta(seconds=duration_sec)).timestamp()
    
    if user_id not in allowed_user_ids:
        allowed_user_ids.append(user_id)
        save_users(allowed_user_ids)
    user_access[user_id] = {"expiry_time": expiry_ts}
    save_user_access(user_access)

    log_action(user_id, f"Redeemed key | plan={plan_label}", message)
    msg = bot.send_message(user_id, f"✅ <b>𝗞𝗘𝗬 𝗔𝗖𝗧𝗜𝗩𝗔𝗧𝗘𝗗!</b>\n📦 <b>Plan:</b> {plan_label}\n⏳ <b>Expires:</b> {fmt_expiry(expiry_ts)}", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=10)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ATTACK COMMANDS & UI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['attack'])
def attack_cmd(message):
    user_id = str(message.chat.id)
    update_reseller_username(message)
    if user_id not in allowed_user_ids or user_access.get(user_id, {}).get("expiry_time", 0) < time.time():
        return bot.send_message(user_id, no_access_msg(), parse_mode="HTML")

    parts = message.text.split()
    if len(parts) == 4: execute_attack(message, parts[1], parts[2], parts[3])
    else:
        msg = bot.send_message(user_id, "🎯 <b>Enter Target IP:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, attack_step_ip)

def attack_step_ip(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    ip = message.text.strip()
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        
    msg = bot.send_message(user_id, "🔌 <b>Enter Target Port:</b>", parse_mode="HTML")
    active_prompts[user_id] = msg.message_id
    bot.register_next_step_handler(msg, attack_step_port, ip)

def attack_step_port(message, ip):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    port = message.text.strip()
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        
    msg = bot.send_message(user_id, "⏱️ <b>Enter Attack Duration (Max 600s):</b>", parse_mode="HTML")
    active_prompts[user_id] = msg.message_id
    bot.register_next_step_handler(msg, attack_step_time, ip, port)

def attack_step_time(message, ip, port):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
        
    execute_attack(message, ip, port, message.text.strip())

def execute_attack(message, target, port_str, time_str):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids or user_access.get(user_id, {}).get("expiry_time", 0) < time.time():
        return bot.send_message(user_id, no_access_msg(), parse_mode="HTML")

    if not is_admin(user_id):
        time_passed = (datetime.datetime.now() - bgmi_cooldown.get(user_id, datetime.datetime.min)).total_seconds()
        if time_passed < 60: return bot.send_message(user_id, f"⏳ <b>Cooldown!</b> Wait {int(60 - time_passed)}s.", parse_mode="HTML")

    try: port, time_val = int(port_str), int(time_str)
    except ValueError: return bot.send_message(user_id, "❌ Port and Time must be numbers.", parse_mode="HTML")

    if time_val > 600: return bot.send_message(user_id, "❌ Max time is 600s.", parse_mode="HTML")

    bgmi_cooldown[user_id] = datetime.datetime.now()
    active_attacks[user_id] = {"target": f"{target}:{port}", "start_time": time.time(), "duration": time_val}
    log_action(user_id, f"Attack → IP: {target} | Port: {port} | Time: {time_val}s", message)
    
    attack_msg = (
        "🚀 <b>𝗔𝗧𝗧𝗔𝗖𝗞 𝗜𝗡𝗜𝗧𝗜𝗔𝗧𝗘𝗗!</b> 🚀\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>Target:</b> <code>{target}:{port}</code>\n"
        f"⏱️ <b>Time:</b> {time_val}s\n"
        f"⏳ <b>Cooldown after attack:</b> 60s\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <i>/status se live check kro</i> ⚡️"
    )
    bot.send_message(user_id, attack_msg, parse_mode="HTML")
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
    user_id = str(message.chat.id)
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
    bot.send_message(user_id, status_msg, parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CONVERSATIONAL RESELLER COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['genkey'])
def genkey_cmd(message):
    msg = bot.send_message(message.chat.id, "Please use the Reseller Menu to generate keys.", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

def genkey_plan_step(message, key_type):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    
    plan = message.text.strip()
    plans = BOT_KEY_PLANS if key_type == "BOT" else APK_KEY_PLANS

    if plan not in plans: 
        msg = bot.send_message(user_id, "❌ Invalid plan. Operation cancelled.", parse_mode="HTML")
        if user_id in active_prompts:
            try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
            except: pass
            del active_prompts[user_id]
        return animated_delete(user_id, msg.message_id, delay=5)
        
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
    msg = bot.send_message(user_id, f"🔢 <b>How many {key_type} keys do you want?</b> (Enter 1 to 50)", parse_mode="HTML")
    active_prompts[user_id] = msg.message_id
    bot.register_next_step_handler(msg, genkey_amount_step, plan, key_type)

def genkey_amount_step(message, plan, key_type):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
        
    execute_genkey(message, plan, message.text.strip(), key_type)

def execute_genkey(message, plan, amount_str, key_type):
    user_id = str(message.chat.id)
    plans = BOT_KEY_PLANS if key_type == "BOT" else APK_KEY_PLANS

    if plan not in plans: 
        msg = bot.send_message(user_id, "❌ Invalid Plan.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)
    try:
        amount = int(amount_str)
        if not (1 <= amount <= 50): raise ValueError
    except ValueError: 
        msg = bot.send_message(user_id, "❌ Amount must be between 1 and 50.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)

    total_cost = plans[plan]["cost"] * amount
    if is_reseller(user_id) and not is_admin(user_id):
        if get_balance(user_id) < total_cost:
            msg = bot.send_message(user_id, f"❌ <b>𝗜𝗡𝗦𝗨𝗙𝗙𝗜𝗖𝗜𝗘𝗡𝗧 𝗕𝗔𝗟𝗔𝗡𝗖𝗘</b>\n💰 Needed: ₹{total_cost} | Bal: ₹{get_balance(user_id)}", parse_mode="HTML")
            return animated_delete(user_id, msg.message_id, delay=8)
        balances[user_id] -= total_cost
        save_balances(balances)

    prefix = "BOT-" if key_type == "BOT" else "FZ-APK-"
    target_dict = active_keys if key_type == "BOT" else active_apk_keys
    target_hist = key_history if key_type == "BOT" else apk_key_history
    target_file = KEYS_FILE if key_type == "BOT" else APK_KEYS_FILE
    target_hist_file = KEY_HISTORY_FILE if key_type == "BOT" else APK_HISTORY_FILE

    gen_keys = []
    for _ in range(amount):
        k = generate_key(prefix)
        target_dict[k], target_hist[k] = plan, {"plan": plan, "creator": user_id, "status": "UNUSED"}
        gen_keys.append(k)
        
    save_keys(target_file, target_dict)
    save_key_history(target_hist_file, target_hist)

    log_action(user_id, f"Generated {amount} {key_type} key(s) | plan={plan} | cost=₹{total_cost}", message)
    
    bot.send_message(user_id, f"🔑 <b>{key_type} 𝗞𝗘𝗬(𝗦) 𝗚𝗘𝗡𝗘𝗥𝗔𝗧𝗘𝗗!</b>\n\n" + "\n".join([f"<code>{k}</code>" for k in gen_keys]) + f"\n\n📦 <b>Plan:</b> {plan}\n💰 <b>Cost:</b> ₹{total_cost}", parse_mode="HTML")

@bot.message_handler(commands=['deletekey'])
def delete_key_cmd(message):
    msg = bot.send_message(message.chat.id, "Please use the Reseller Menu to delete keys.", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

def deletekey_step(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
        
    execute_deletekey(message, message.text.strip())

def execute_deletekey(message, key_str):
    user_id, key = str(message.chat.id), key_str.upper()
    
    if key in key_history:
        if not is_admin(user_id) and key_history[key]["creator"] != user_id:
            msg = bot.send_message(user_id, "❌ You can only delete keys that you generated.", parse_mode="HTML")
            return animated_delete(user_id, msg.message_id, delay=5)
        if key in active_keys:
            del active_keys[key]
            save_keys(KEYS_FILE, active_keys)
            key_history[key]["status"] = "DELETED"
            save_key_history(KEY_HISTORY_FILE, key_history)
            msg = bot.send_message(user_id, f"✅ <b>BOT Key successfully deleted.</b>", parse_mode="HTML")
            return animated_delete(user_id, msg.message_id, delay=5)

    elif key in apk_key_history:
        if not is_admin(user_id) and apk_key_history[key]["creator"] != user_id:
            msg = bot.send_message(user_id, "❌ You can only delete keys that you generated.", parse_mode="HTML")
            return animated_delete(user_id, msg.message_id, delay=5)
        if key in active_apk_keys:
            del active_apk_keys[key]
            save_keys(APK_KEYS_FILE, active_apk_keys)
            apk_key_history[key]["status"] = "DELETED"
            save_key_history(APK_HISTORY_FILE, apk_key_history)
            msg = bot.send_message(user_id, f"✅ <b>APK Key successfully deleted.</b>", parse_mode="HTML")
            return animated_delete(user_id, msg.message_id, delay=5)

    msg = bot.send_message(user_id, "❌ Key not found or already used.", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=5)

@bot.message_handler(commands=['balance'])
def check_balance(message):
    msg = bot.send_message(message.chat.id, "Please use the buttons to check balances.", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PAGINATED LIST COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['listkeys'])
def listkeys_cmd(message):
    user_id = str(message.chat.id)
    if not is_admin_or_reseller(user_id): 
        return bot.send_message(user_id, admin_reseller_only_msg(), parse_mode="HTML")
    
    user_unused_keys = []
    for k, p in active_keys.items():
        if is_admin(user_id) or (k in key_history and key_history[k]["creator"] == user_id):
            user_unused_keys.append((k, f"{p} [BOT]"))
    for k, p in active_apk_keys.items():
        if is_admin(user_id) or (k in apk_key_history and apk_key_history[k]["creator"] == user_id):
            user_unused_keys.append((k, f"{p} [APK]"))

    if not user_unused_keys: 
        return bot.send_message(user_id, "⚠️ No unused keys available.", parse_mode="HTML")
    send_listkeys_page(message.chat.id, user_unused_keys, 0)

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
    user_unused_keys = []
    for k, p in active_keys.items():
        if is_admin(user_id) or (k in key_history and key_history[k]["creator"] == user_id):
            user_unused_keys.append((k, f"{p} [BOT]"))
    for k, p in active_apk_keys.items():
        if is_admin(user_id) or (k in apk_key_history and apk_key_history[k]["creator"] == user_id):
            user_unused_keys.append((k, f"{p} [APK]"))
    send_listkeys_page(call.message.chat.id, user_unused_keys, page, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['resellers'])
def resellers_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.send_message(message.chat.id, admin_only_msg(), parse_mode="HTML")
    if not resellers_data: return bot.send_message(message.chat.id, "⚠️ No resellers found.", parse_mode="HTML")
    send_resellers_page(message.chat.id, list(resellers_data.items()), 0)

def send_resellers_page(chat_id, res_list, page, message_id=None):
    per_page = 15
    total_pages = max(1, (len(res_list) + per_page - 1) // per_page)
    page_items = res_list[page*per_page : (page+1)*per_page]
    
    text = f"🤝 <b>𝗥𝗘𝗦𝗘𝗟𝗟𝗘𝗥𝗦 (Page {page+1}/{total_pages})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid, data in page_items: 
        text += f"🆔 <code>{uid}</code> ({data['username']} - {data['tier']}) → ₹{get_balance(uid)}\n"
    
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
    if not is_admin(str(message.chat.id)): return bot.send_message(message.chat.id, admin_only_msg(), parse_mode="HTML")
    bot.send_message(message.chat.id,
        "🛠 <b>𝗔𝗗𝗠𝗜𝗡 𝗖𝗢𝗠𝗠𝗔𝗡𝗗𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        "👤 <b>USERS</b>\n🔹 /add | /remove\n🔹 /paidusers | /freeusers\n🔹 /extendall\n🔹 /trialkey | /killtrial\n\n"
        "🤝 <b>RESELLERS</b>\n🔸 /addreseller | /rmreseller\n🔸 /resellerstats | /resellers\n🔸 /addbalance | /setbalance\n\n"
        "📢 <b>BROADCAST & DATA</b>\n🔊 /broadcast | /bcpaid | /bcreseller\n📄 /logs | 🗑 /clearlogs\n📦 /getdata (Download Full Ledger)\n⚠️ /clearalldata (Wipe Database)\n━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML"
    ) 

@bot.message_handler(commands=['trialkey'])
def trialkey_cmd(message):
    if not is_admin(str(message.chat.id)): return
    parts = message.text.split()
    if len(parts) == 3:
        try:
            days = float(parts[1])
            max_uses = int(parts[2])
            key = generate_key("TRIAL-")
            trial_keys[key] = {"duration": days * 86400, "max_uses": max_uses, "used_by": []}
            save_trial_keys(trial_keys)
            bot.send_message(message.chat.id, f"✅ <b>Trial Key Generated!</b>\n🔑 <code>{key}</code>\n⏳ Duration: {days} days\n👥 Max Uses: {max_uses}", parse_mode="HTML")
        except:
            bot.send_message(message.chat.id, "❌ Error in numbers.", parse_mode="HTML")
    else:
        bot.send_message(message.chat.id, "❌ Usage: /trialkey <days> <max_uses>\nExample: /trialkey 0.5 10 (12 hours, 10 users)", parse_mode="HTML")

@bot.message_handler(commands=['killtrial'])
def killtrial_cmd(message):
    if not is_admin(str(message.chat.id)): return
    trial_keys.clear()
    save_trial_keys(trial_keys)
    
    expired = []
    for uid in list(trial_users):
        if uid in user_access: user_access.pop(uid, None)
        if uid in allowed_user_ids: allowed_user_ids.remove(uid)
        expired.append(uid)
        
    trial_users.clear()
    save_file_lines(TRIAL_USERS_FILE, trial_users)
    save_users(allowed_user_ids)
    save_user_access(user_access)
    
    bot.send_message(message.chat.id, f"🛑 <b>All Trial Keys Killed!</b>\nRemoved access for {len(expired)} trial users.", parse_mode="HTML")

@bot.message_handler(commands=['add'])
def add_user_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.send_message(message.chat.id, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) >= 3: execute_add(message, parts[1], parts[2])
    else:
        msg = bot.send_message(message.chat.id, "👤 <b>Enter the User ID to add:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[str(message.chat.id)] = msg.message_id
        bot.register_next_step_handler(msg, add_step_id)

def add_step_id(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    target = message.text.strip()
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
    msg = bot.send_message(user_id, f"📦 <b>Which plan?</b> ({', '.join(BOT_KEY_PLANS.keys())})", parse_mode="HTML")
    active_prompts[user_id] = msg.message_id
    bot.register_next_step_handler(msg, add_step_plan, target)

def add_step_plan(message, target):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
    execute_add(message, target, message.text.strip())

def execute_add(message, target, plan):
    user_id = str(message.chat.id)
    if plan not in BOT_KEY_PLANS: 
        msg = bot.send_message(user_id, "❌ Invalid plan.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)
        
    expiry_ts = (datetime.datetime.now(ist) + BOT_KEY_PLANS[plan]["duration"]).timestamp()
    if target not in allowed_user_ids:
        allowed_user_ids.append(target)
        save_users(allowed_user_ids)
        prefix = "✅ <b>User Added</b>"
    else: prefix = "🔄 <b>Access Updated</b>"
    
    user_access[target] = {"expiry_time": expiry_ts}
    save_user_access(user_access)
    all_known_users.add(target)
    save_file_lines(ALL_USERS_FILE, all_known_users)
    log_action(user_id, f"Added user={target} plan={plan}", message)
    msg = bot.send_message(user_id, f"{prefix}\n🆔 <b>ID:</b> <code>{target}</code>\n⏳ <b>Expires:</b> {fmt_expiry(expiry_ts)}", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=10)

@bot.message_handler(commands=['remove', 'rmreseller'])
def remove_targets_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.send_message(message.chat.id, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    parts = message.text.split()
    if len(parts) >= 2: execute_remove(message, cmd, parts[1])
    else:
        msg = bot.send_message(message.chat.id, f"🗑️ <b>Enter the ID to remove:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[str(message.chat.id)] = msg.message_id
        bot.register_next_step_handler(msg, remove_step_id, cmd)

def remove_step_id(message, cmd):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
    execute_remove(message, cmd, message.text.strip())

def execute_remove(message, cmd, target):
    user_id = str(message.chat.id)
    if cmd == '/remove':
        if target in allowed_user_ids:
            allowed_user_ids.remove(target); user_access.pop(target, None)
            save_users(allowed_user_ids); save_user_access(user_access)
            msg = bot.send_message(user_id, f"✅ <b>User {target} removed.</b>", parse_mode="HTML")
        else: msg = bot.send_message(user_id, "❌ User not found.", parse_mode="HTML")
    else:
        if target in resellers_data:
            del resellers_data[target]
            if target in balances: del balances[target] 
            save_resellers(resellers_data); save_balances(balances)
            msg = bot.send_message(user_id, f"✅ <b>Reseller {target} removed. Balance wiped.</b>", parse_mode="HTML")
        else: msg = bot.send_message(user_id, "❌ Reseller not found.", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=5)

@bot.message_handler(commands=['addreseller'])
def addreseller_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.send_message(message.chat.id, admin_only_msg(), parse_mode="HTML")
    msg = bot.send_message(message.chat.id, "🤝 <b>Enter the new Reseller's Telegram ID:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
    active_prompts[str(message.chat.id)] = msg.message_id
    bot.register_next_step_handler(msg, addres_step_id)

def addres_step_id(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    target = message.text.strip()
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🌟 Master (Bot + APK)", callback_data=f"set_tier_{target}_MASTER"),
        InlineKeyboardButton("🤖 Bot Only", callback_data=f"set_tier_{target}_BOT"),
        InlineKeyboardButton("📱 APK Only", callback_data=f"set_tier_{target}_APK")
    )
    msg = bot.send_message(user_id, f"🎯 <b>Select Tier for ID {target}:</b>", reply_markup=markup, parse_mode="HTML")
    active_prompts[user_id] = msg.message_id

def addres_step_bal(message, target, tier):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
    execute_addreseller(message, target, tier, message.text.strip())

def execute_addreseller(message, target, tier, bal_str):
    user_id = str(message.chat.id)
    try: initial_bal = int(bal_str)
    except ValueError: 
        msg = bot.send_message(user_id, "❌ Balance must be a number.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)
    
    resellers_data[target] = {"tier": tier, "username": "Unknown"}
    balances[target] = get_balance(target) + initial_bal
    save_resellers(resellers_data); save_balances(balances)
    log_action(user_id, f"Added {tier} reseller={target} with {initial_bal}", message)
    
    msg = bot.send_message(user_id, f"✅ <b>{tier} Reseller Added!</b>\n🆔 <b>ID:</b> <code>{target}</code>\n💵 <b>Starting Balance:</b> ₹{balances[target]}", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=10)
    
    try: bot.send_message(target, f"💰 <b>𝗬𝗼𝘂 𝗔𝗿𝗲 𝗣𝗿𝗼𝗺𝗼𝘁𝗲𝗱 𝗧𝗼 {tier} 𝗥𝗲𝘀𝗲𝗹𝗹𝗲𝗿!</b>\n━━━━━━━━━━━━━━━━━━━━━━\n💵 <b>Balance:</b> ₹{balances[target]}\n🔑 <b>Total Keys Generated:</b> 0\n\n📋 <i>Use /prices to see key prices</i>\n🔑 <i>Use /genkey to generate</i>", parse_mode="HTML")
    except Exception: pass

@bot.message_handler(commands=['addbalance', 'setbalance'])
def addbalance_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.send_message(message.chat.id, admin_only_msg(), parse_mode="HTML")
    cmd = message.text.split()[0].lower()
    parts = message.text.split()
    if len(parts) >= 3: execute_balance_change(message, cmd, parts[1], parts[2])
    else:
        msg = bot.send_message(message.chat.id, "👤 <b>Enter the Reseller's Telegram ID:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[str(message.chat.id)] = msg.message_id
        bot.register_next_step_handler(msg, bal_step_id, cmd)

def bal_step_id(message, cmd):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    target = message.text.strip()
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
    msg = bot.send_message(user_id, "💰 <b>Enter the amount:</b>", parse_mode="HTML")
    active_prompts[user_id] = msg.message_id
    bot.register_next_step_handler(msg, bal_step_amt, cmd, target)

def bal_step_amt(message, cmd, target):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
    execute_balance_change(message, cmd, target, message.text.strip())

def execute_balance_change(message, cmd, target, amount_str):
    user_id = str(message.chat.id)
    try: amount = int(amount_str)
    except ValueError: 
        msg = bot.send_message(user_id, "❌ Amount must be a number.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)
    if target not in resellers_data: 
        msg = bot.send_message(user_id, "❌ User is not a reseller.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)
    
    balances[target] = get_balance(target) + amount if cmd == '/addbalance' else amount
    save_balances(balances)
    
    reseller_uname = resellers_data.get(target, {}).get("username", "Unknown")
    msg = bot.send_message(user_id, f"✅ <b>𝗕𝗮𝗹𝗮𝗻𝗰𝗲 Updated!</b>\n👤 <b>Reseller:</b> {reseller_uname} (<code>{target}</code>)\n💵 <b>New Balance:</b> ₹{balances[target]}", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=10)
    try: bot.send_message(target, f"💰 <b>𝗬𝗼𝘂𝗿 𝗕𝗮𝗹𝗮𝗻𝗰𝗲 𝗛𝗮𝘀 𝗕𝗲𝗲𝗻 𝗨𝗽𝗱𝗮𝘁𝗲𝗱!</b>\n💵 <b>Current Balance:</b> ₹{balances[target]}", parse_mode="HTML")
    except: pass

@bot.message_handler(commands=['extendall'])
def extendall_cmd(message):
    if not is_admin(str(message.chat.id)): return bot.send_message(message.chat.id, admin_only_msg(), parse_mode="HTML")
    parts = message.text.split()
    if len(parts) >= 3: execute_extendall(message, parts[1], parts[2])
    else:
        msg = bot.send_message(message.chat.id, "⏳ <b>Enter amount to extend (e.g. 2):</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[str(message.chat.id)] = msg.message_id
        bot.register_next_step_handler(msg, ext_step_amt)

def ext_step_amt(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    amount_str = message.text.strip()
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
    msg = bot.send_message(user_id, "📅 <b>Enter unit (hours or days):</b>", parse_mode="HTML")
    active_prompts[user_id] = msg.message_id
    bot.register_next_step_handler(msg, ext_step_unit, amount_str)

def ext_step_unit(message, amount_str):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
    execute_extendall(message, amount_str, message.text.strip())

def execute_extendall(message, amount_str, unit):
    user_id = str(message.chat.id)
    try: amount = int(amount_str)
    except: 
        msg = bot.send_message(user_id, "❌ Amount must be a number.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)
    unit = unit.lower()
    time_to_add = timedelta(hours=amount) if "hour" in unit else (timedelta(days=amount) if "day" in unit else None)
    if not time_to_add: 
        msg = bot.send_message(user_id, "❌ Unit must be 'hours' or 'days'.", parse_mode="HTML")
        return animated_delete(user_id, msg.message_id, delay=5)

    users_ext, now = 0, time.time()
    for uid in list(user_access.keys()):
        if user_access[uid]["expiry_time"] > now:
            user_access[uid]["expiry_time"] = (datetime.datetime.fromtimestamp(user_access[uid]["expiry_time"]) + time_to_add).timestamp()
            users_ext += 1
    save_user_access(user_access)
    msg = bot.send_message(user_id, f"🎉 <b>𝗧𝗶𝗺𝗲 𝗘𝘅𝘁𝗲𝗻𝗱𝗲𝗱!</b>\n⏰ <b>Added:</b> {amount} {unit}\n👥 <b>Users Updated:</b> {users_ext}", parse_mode="HTML")
    animated_delete(user_id, msg.message_id, delay=10)

@bot.message_handler(commands=['broadcast', 'bcpaid', 'bcreseller'])
def broadcast_cmd(message):
    if not is_admin(str(message.chat.id)): return
    msg = bot.send_message(message.chat.id, "📢 <b>Please use the Admin Panel buttons to broadcast.</b>\nClick /start to open the menu.", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

def broadcast_step(message, target_type):
    user_id = str(message.chat.id)
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
        
    try: bot.delete_message(message.chat.id, message.message_id) 
    except: pass
    if is_cancel(message): return
    execute_broadcast(message, target_type, message.text)

def execute_broadcast(message, target_type, text_content):
    if target_type == 'reseller': targets = set(resellers_data.keys())
    elif target_type == 'paid': targets = set(allowed_user_ids)
    elif target_type == 'free': targets = all_known_users - set(allowed_user_ids)
    else: targets = all_known_users | set(allowed_user_ids) | set(resellers_data.keys()) | ADMIN_IDS

    targets = list(targets)
    text = f"📢 <b>𝗕𝗥𝗢𝗔𝗗𝗖𝗔𝗦𝗧</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\n{text_content}\n\n━━━━━━━━━━━━━━━━━━━━━━"
    
    loading_msg = bot.send_message(message.chat.id, f"⏳ <i>Broadcasting to {len(targets)} users in progress...</i>", parse_mode="HTML")
    
    success, fail = 0, 0
    for t in targets:
        try: 
            bot.send_message(t, text, parse_mode="HTML")
            success += 1
            time.sleep(0.05) 
        except: fail += 1

    try: bot.delete_message(message.chat.id, loading_msg.message_id)
    except: pass

    final_msg = bot.send_message(message.chat.id, f"📢 <b>Broadcast Done</b>\n✅ Sent: {success}\n❌ Failed: {fail}", parse_mode="HTML")
    animated_delete(message.chat.id, final_msg.message_id, delay=10)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN REPORTS & STATS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['paidusers', 'freeusers', 'rstats', 'trialusers'])
def admin_reports(message):
    if not is_admin(str(message.chat.id)): return
    cmd = message.text.split()[0].lower()
    
    if cmd == '/paidusers':
        paid = [u for u in allowed_user_ids if u not in trial_users]
        if not paid: 
            msg = bot.send_message(message.chat.id, "⚠️ No paid users found.", parse_mode="HTML")
            return animated_delete(message.chat.id, msg.message_id, delay=5)
        send_paidusers_page(message.chat.id, paid, 0)
        
    elif cmd == '/freeusers':
        free = [u for u in all_known_users if u not in allowed_user_ids]
        if not free: 
            msg = bot.send_message(message.chat.id, "⚠️ No free users found.", parse_mode="HTML")
            return animated_delete(message.chat.id, msg.message_id, delay=5)
        send_freeusers_page(message.chat.id, free, 0)
        
    elif cmd == '/rstats':
        if not resellers_data: 
            msg = bot.send_message(message.chat.id, "⚠️ No resellers found.", parse_mode="HTML")
            return animated_delete(message.chat.id, msg.message_id, delay=5)
        send_rstats_page(message.chat.id, list(resellers_data.items()), 0)

    elif cmd == '/trialusers':
        t_users = list(trial_users)
        if not t_users: 
            msg = bot.send_message(message.chat.id, "⚠️ No trial users found.", parse_mode="HTML")
            return animated_delete(message.chat.id, msg.message_id, delay=5)
            
        text = "⏳ <b>𝗧𝗥𝗜𝗔𝗟 𝗨𝗦𝗘𝗥𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
        for uid in t_users: 
            uname = user_profiles.get(uid, "Unknown")
            text += f"🆔 <code>{uid}</code> ({uname})\n"
        bot.send_message(message.chat.id, text, parse_mode="HTML")
        
def send_paidusers_page(chat_id, users_list, page, message_id=None):
    per_page = 20
    total_pages = max(1, (len(users_list) + per_page - 1) // per_page)
    page_items = users_list[page*per_page : (page+1)*per_page]
    text = f"💎 <b>𝗣𝗔𝗜𝗗 𝗨𝗦𝗘𝗥𝗦 (Page {page+1}/{total_pages})</b>\n━━━━━━━━━━━━━━━━━━━━━━\n"
    for uid in page_items: 
        uname = user_profiles.get(uid, "Unknown")
        text += f"🆔 <code>{uid}</code> ({uname}) [Exp: {fmt_expiry(user_access.get(uid, {}).get('expiry_time', 0))}]\n"
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
    for uid in page_items: 
        uname = user_profiles.get(uid, "Unknown")
        text += f"🆔 <code>{uid}</code> ({uname})\n"
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
    for uid, data in page_items: 
        text += f"👤 {data['username']} [{data['tier']}] (<code>{uid}</code>)\n💵 Bal: ₹{get_balance(uid)} | 🔑 Keys: {count_keys_generated_by(uid)}\n\n"
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
    msg = bot.send_message(message.chat.id, "📦 <b>Fetching Database Files & Building Ledger...</b>", parse_mode="HTML")
    summary_path = os.path.join(DATA_DIR, "Human_Readable_Ledger.txt")
    with open(summary_path, "w", encoding="utf-8") as sf:
        sf.write("========== 📊 MASTER DATABASE SUMMARY ==========\n")
        sf.write(f"Generated: {datetime.datetime.now(ist).strftime('%d %b %Y %I:%M %p')}\n\n")
        sf.write("========== 🤝 RESELLER LEDGERS ==========\n")
        for uid, data in resellers_data.items():
            sf.write(f"Reseller: {data['username']} [{data['tier']}] (ID: {uid})\nLeftover Balance: ₹{get_balance(uid)}\n")
            
            r_keys = {k: v for k, v in key_history.items() if v["creator"] == uid}
            r_apk_keys = {k: v for k, v in apk_key_history.items() if v["creator"] == uid}
            r_all_keys = {**r_keys, **r_apk_keys}
            
            unused = [k for k, v in r_all_keys.items() if v["status"] == "UNUSED"]
            used = [k for k, v in r_all_keys.items() if str(v["status"]).startswith("USED")]
            
            sf.write(f"Total Keys Generated: {len(r_all_keys)}\n  🟢 Unused Keys ({len(unused)}):\n")
            for k in unused: sf.write(f"    - {k} [{r_all_keys[k]['plan']}]\n")
            sf.write(f"  🔴 Used Keys ({len(used)}):\n")
            for k in used: sf.write(f"    - {k} [{r_all_keys[k]['plan']}] -> {r_all_keys[k]['status']}\n")
            sf.write("-" * 45 + "\n\n")
        sf.write("========== 👤 ACTIVE PREMIUM USERS ==========\n")
        for uid, info in user_access.items(): sf.write(f"ID: {uid} | Expiry: {fmt_expiry(info['expiry_time'])}\n")
    
    found = False
    for fp in [summary_path, USER_ACCESS_FILE, KEYS_FILE, APK_KEYS_FILE, RESELLERS_FILE, BALANCE_FILE, ALL_USERS_FILE, TRIAL_KEYS_FILE, TRIAL_USERS_FILE, LOG_FILE]:
        if os.path.exists(fp) and os.stat(fp).st_size > 0:
            with open(fp, "rb") as f: bot.send_document(message.chat.id, f, visible_file_name=os.path.basename(fp))
            found = True
    if not found: bot.send_message(message.chat.id, "⚠️ <b>No data files found yet.</b>", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  DANGER ZONE: WIPE DATABASE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=['clearalldata'])
def clearalldata_cmd(message):
    if not is_admin(str(message.chat.id)): return
    msg = bot.send_message(message.chat.id, "⚠️ <b>WARNING: EXTREME DANGER</b> ⚠️\nThis will wipe ALL users, resellers, balances, and keys. This cannot be undone.\n\nType exactly <code>CONFIRM WIPE</code> to proceed, or /cancel to abort.", parse_mode="HTML")
    active_prompts[str(message.chat.id)] = msg.message_id
    bot.register_next_step_handler(msg, clearalldata_step)

def clearalldata_step(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
        
    if message.text.strip() == "CONFIRM WIPE":
        all_known_users.clear(); trial_users.clear(); allowed_user_ids.clear()
        user_access.clear(); active_keys.clear(); key_history.clear()
        active_apk_keys.clear(); apk_key_history.clear()
        resellers_data.clear(); trial_keys.clear(); balances.clear()
        
        files_to_wipe = [USER_FILE, LOG_FILE, USER_ACCESS_FILE, KEYS_FILE, KEY_HISTORY_FILE, APK_KEYS_FILE, APK_HISTORY_FILE, RESELLERS_FILE, BALANCE_FILE, ALL_USERS_FILE, TRIAL_KEYS_FILE, TRIAL_USERS_FILE]
        for f in files_to_wipe:
            if os.path.exists(f): open(f, 'w').close()
            
        msg = bot.send_message(user_id, "✅ <b>DATABASE COMPLETELY WIPED.</b> Everything has been reset to zero.", parse_mode="HTML")
        log_action(user_id, "EXECUTED FULL DATABASE WIPE", message)
        animated_delete(user_id, msg.message_id, delay=10)
    else: 
        msg = bot.send_message(user_id, "🚫 <b>Confirmation failed. Wipe cancelled.</b>", parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=5)

@bot.message_handler(commands=['logs'])
def send_logs(message):
    if not is_admin(str(message.chat.id)): return
    if os.path.exists(LOG_FILE) and os.stat(LOG_FILE).st_size > 0:
        with open(LOG_FILE, "rb") as f: bot.send_document(message.chat.id, f, visible_file_name="bot_logs.txt")
    else: 
        msg = bot.send_message(message.chat.id, "⚠️ Logs are empty.", parse_mode="HTML")
        animated_delete(message.chat.id, msg.message_id, delay=5)

@bot.message_handler(commands=['clearlogs'])
def clear_logs_cmd(message):
    if not is_admin(str(message.chat.id)): return
    if os.path.exists(LOG_FILE): open(LOG_FILE, "w").close()
    msg = bot.send_message(message.chat.id, "✅ <b>Logs wiped.</b>", parse_mode="HTML")
    animated_delete(message.chat.id, msg.message_id, delay=5)

def trialkey_step(message):
    user_id = str(message.chat.id)
    if is_cancel(message): return
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
        
    parts = message.text.split()
    if len(parts) == 2:
        try:
            days = float(parts[0])
            max_uses = int(parts[1])
            key = generate_key("TRIAL-")
            trial_keys[key] = {"duration": days * 86400, "max_uses": max_uses, "used_by": []}
            save_trial_keys(trial_keys)
            bot.send_message(user_id, f"✅ <b>Trial Key Generated!</b>\n🔑 <code>{key}</code>\n⏳ Duration: {days} days\n👥 Max Uses: {max_uses}", parse_mode="HTML")
        except:
            msg = bot.send_message(user_id, "❌ Error in numbers. Try again.", parse_mode="HTML")
            animated_delete(user_id, msg.message_id, delay=5)
    else:
        msg = bot.send_message(user_id, "❌ Invalid format. Use: days max_uses", parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=5)

def execute_killtrial(chat_id):
    trial_keys.clear()
    save_trial_keys(trial_keys)
    expired = []
    for uid in list(trial_users):
        if uid in user_access: user_access.pop(uid, None)
        if uid in allowed_user_ids: allowed_user_ids.remove(uid)
        expired.append(uid)
    trial_users.clear()
    save_file_lines(TRIAL_USERS_FILE, trial_users)
    save_users(allowed_user_ids)
    save_user_access(user_access)
    msg = bot.send_message(chat_id, f"🛑 <b>All Trial Keys Killed!</b>\nRemoved access for {len(expired)} trial users.", parse_mode="HTML")
    animated_delete(chat_id, msg.message_id, delay=10)
    
# --- MASTER BUTTON ROUTER ---
@bot.callback_query_handler(func=lambda call: True)
def handle_all_buttons(call):
    user_id = str(call.message.chat.id)
    track_profile(call.from_user)
    try: bot.answer_callback_query(call.id)
    except: pass
    
    bot.clear_step_handler_by_chat_id(call.message.chat.id)
    if user_id in active_prompts:
        try: bot.delete_message(chat_id=user_id, message_id=active_prompts[user_id])
        except: pass
        del active_prompts[user_id]
    
    action = call.data
    username_str = f"@{call.from_user.username}" if call.from_user.username else "—"
    is_paid = user_id in allowed_user_ids and user_access.get(user_id, {}).get("expiry_time", 0) > time.time()

    # --- MENU NAVIGATION ---
    try:
        if action == "menu_main":
            bot.edit_message_text(f"🚀 <b>Main Dashboard</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=get_main_menu(user_id, is_paid), parse_mode="HTML")
        elif action == "menu_reseller":
            bot.edit_message_text("🤝 <b>Reseller Control Panel</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=get_reseller_menu(), parse_mode="HTML")
        elif action == "menu_admin":
            bot.edit_message_text("🛠 <b>Master Admin Panel</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=get_admin_menu(), parse_mode="HTML")
        elif action == "menu_danger":
            if not is_admin(user_id): return
            bot.edit_message_text("⚠️ <b>Advanced & Danger Zone</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=get_danger_menu(), parse_mode="HTML")
    except Exception:
        pass 
        
    # --- MAIN MENU ACTIONS ---
    if action == "ui_profile":
        msg = bot.send_message(user_id, build_profile_text(user_id, username_str), parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=10)
    elif action == "ui_plan":
        if not is_paid: msg = bot.send_message(user_id, no_access_msg(), parse_mode="HTML")
        else: msg = bot.send_message(user_id, f"📅 <b>𝗬𝗢𝗨𝗥 𝗣𝗟𝗔𝗡</b>\n⏳ <b>Expires:</b> {fmt_expiry(user_access[user_id]['expiry_time'])}", parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=8)
    elif action == "ui_rules":
        msg = bot.send_message(user_id, "📜 <b>𝗥𝗨𝗟𝗘𝗦</b>\n1️⃣ No sharing keys.\n2️⃣ One key = one account.\n3️⃣ No refunds.", parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=10)
    elif action == "ui_status":
        attack_status(call.message) 
    elif action == "ui_redeem":
        msg = bot.send_message(user_id, "🔑 <b>Enter the key you want to redeem:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, redeem_step)
    elif action == "ui_attack":
        if not is_paid:
            msg = bot.send_message(user_id, no_access_msg(), parse_mode="HTML")
            animated_delete(user_id, msg.message_id, delay=5)
        else:
            msg = bot.send_message(user_id, "🎯 <b>Enter Target IP:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
            active_prompts[user_id] = msg.message_id
            bot.register_next_step_handler(msg, attack_step_ip)

    # --- RESELLER ACTIONS ---
    elif action == "cb_genkey":
        if not is_admin_or_reseller(user_id): return
        
        # Determine User Tier
        tier = "MASTER"
        if is_reseller(user_id) and not is_admin(user_id):
            tier = resellers_data[user_id]["tier"]

        markup = InlineKeyboardMarkup()
        if tier in ["MASTER", "BOT"]:
            markup.add(InlineKeyboardButton("🤖 BOT Key", callback_data="gen_bot"))
        if tier in ["MASTER", "APK"]:
            markup.add(InlineKeyboardButton("📱 APK Key", callback_data="gen_apk"))
            
        if not markup.keyboard:
            msg = bot.send_message(user_id, "❌ Your account is not configured to generate any keys.")
            return animated_delete(user_id, msg.message_id, delay=5)

        bot.edit_message_text("📦 <b>What type of key do you want to generate?</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=markup, parse_mode="HTML")
        
    elif action in ["gen_bot", "gen_apk"]:
        if not is_admin_or_reseller(user_id): return
        key_type = "BOT" if action == "gen_bot" else "APK"
        plans = BOT_KEY_PLANS if key_type == "BOT" else APK_KEY_PLANS
        msg = bot.send_message(user_id, f"📦 <b>Which {key_type} plan?</b>\nAvailable: {', '.join(plans.keys())}\n<i>(Type /cancel)</i>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, genkey_plan_step, key_type)
        
    elif action == "cb_listkeys":
        if not is_admin_or_reseller(user_id): return
        listkeys_cmd(call.message) 
        
    elif action == "cb_balance":
        if not is_admin_or_reseller(user_id): return
        msg = bot.send_message(user_id, f"💰 <b>Your Balance:</b> ₹{get_balance(user_id)}", parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=8)
        
    elif action == "cb_prices":
        lines = ["💰 <b>𝗕𝗢𝗧 𝗞𝗘𝗬 𝗣𝗥𝗜𝗖𝗘𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━"]
        for plan, info in BOT_KEY_PLANS.items(): lines.append(f"🤖 <b>{plan.ljust(8)}</b> - ₹{info['cost']}")
        lines.append("\n💰 <b>𝗔𝗣𝗞 𝗞𝗘𝗬 𝗣𝗥𝗜𝗖𝗘𝗦</b>\n━━━━━━━━━━━━━━━━━━━━━━")
        for plan, info in APK_KEY_PLANS.items(): lines.append(f"📱 <b>{plan.ljust(8)}</b> - ₹{info['cost']}")
        msg = bot.send_message(user_id, "\n".join(lines), parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=15)
        
    elif action == "cb_delkey":
        if not is_admin_or_reseller(user_id): return
        msg = bot.send_message(user_id, "🗑️ <b>Enter the key to delete:</b>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, deletekey_step)

    # --- ADMIN ACTIONS ---
    elif action == "cb_adduser":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "👤 <b>Enter the User ID to add:</b>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, add_step_id)
    elif action == "cb_rmuser":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "🗑️ <b>Enter the User ID to remove:</b>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, remove_step_id, '/remove')
        
    elif action == "cb_addres":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "🤝 <b>Enter new Reseller ID:</b>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, addres_step_id)
        
    # NEW TIER SELECTION LOGIC
    elif action.startswith("set_tier_"):
        if not is_admin(user_id): return
        parts = action.split("_")
        target = parts[2]
        tier = parts[3]
        
        msg = bot.send_message(user_id, f"💰 <b>Enter Initial Balance for {tier} Reseller:</b>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, addres_step_bal, target, tier)
        
    elif action == "cb_rmres":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "🛑 <b>Enter Reseller ID to remove:</b>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, remove_step_id, '/rmreseller')
    elif action == "cb_setbal":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "⚙️ <b>Enter Reseller ID to SET balance:</b>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, bal_step_id, '/setbalance')
        
    elif action == "cb_trialkey":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "🎁 <b>Generate Trial Key</b>\n\nEnter exactly like this: <code>days uses</code>\n<i>Example: 0.5 10 (12 hrs, 10 uses)</i>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, trialkey_step)
        
    elif action == "cb_killtrial":
        if not is_admin(user_id): return
        execute_killtrial(user_id)
        
    # --- BROADCAST SYSTEM ---
    elif action == "cb_broadcast":
        if not is_admin(user_id): return
        bot.edit_message_text("📢 <b>Select Broadcast Target:</b>", chat_id=user_id, message_id=call.message.message_id, reply_markup=get_broadcast_menu(), parse_mode="HTML")
    elif action.startswith("bc_"):
        if not is_admin(user_id): return
        target_type = action.replace("bc_", "") 
        msg = bot.send_message(user_id, f"📢 <b>Enter message for {target_type.upper()}:</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, broadcast_step, target_type)
        
    # --- DANGER ZONE ACTIONS ---
    elif action == "cb_extendall":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "⏳ <b>Enter amount to extend (e.g. 2):</b>\n<i>(Type /cancel to abort)</i>", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, ext_step_amt)
    elif action == "cb_clearlogs":
        if not is_admin(user_id): return
        if os.path.exists(LOG_FILE): open(LOG_FILE, "w").close()
        msg = bot.send_message(user_id, "✅ <b>Logs have been wiped clean.</b>", parse_mode="HTML")
        animated_delete(user_id, msg.message_id, delay=5)
    elif action == "cb_clearall":
        if not is_admin(user_id): return
        msg = bot.send_message(user_id, "⚠️ <b>WARNING: EXTREME DANGER</b> ⚠️\nThis will wipe ALL users, keys, and balances.\n\nType exactly <code>CONFIRM WIPE</code> to proceed.", parse_mode="HTML")
        active_prompts[user_id] = msg.message_id
        bot.register_next_step_handler(msg, clearalldata_step)
        
    # --- REPORTS ---
    elif action == "cb_getdata":
        if not is_admin(user_id): return
        send_database_files(call.message)
    elif action in ["cb_paidusers", "cb_freeusers", "cb_rstats", "cb_trialusers"]:
        if not is_admin(user_id): return
        call.message.text = "/" + action.replace("cb_", "") 
        admin_reports(call.message)

@bot.message_handler(content_types=['web_app_data'])
def handle_webapp_data(message):
    user_id = str(message.chat.id)
    if user_id not in allowed_user_ids or user_access.get(user_id, {}).get("expiry_time", 0) < time.time():
        return bot.send_message(user_id, no_access_msg(), parse_mode="HTML")
    try:
        data = json.loads(message.web_app_data.data)
        execute_attack(message, data.get("ip"), int(data.get("port")), int(data.get("time")))
    except Exception:
        bot.send_message(user_id, f"❌ Error processing Web App data.", parse_mode="HTML")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  INTEGRATED FLASK API FOR ANDROID APP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
app = Flask(__name__)
CORS(app)

@app.route('/verify-key', methods=['POST'])
def verify_key():
    data = request.get_json(force=True, silent=True)
    if not data: return jsonify({"status": "error", "message": "Invalid format"}), 400

    user_key = data.get('key', '').strip()
    user_hwid = data.get('hwid', '').strip()

    if not user_key or not user_hwid:
        return jsonify({"status": "error", "message": "Missing info"}), 400

    # Read DIRECTLY from the bot's live RAM!
    if user_key not in apk_key_history:
        return jsonify({"status": "error", "message": "Invalid license key."}), 401

    key_info = apk_key_history[user_key]
    current_status = key_info["status"]

    if current_status == "DELETED":
        return jsonify({"status": "error", "message": "License key revoked."}), 401

    if current_status == "UNUSED":
        # 1. Update the Bot's RAM
        apk_key_history[user_key]["status"] = f"USED_BY:{user_hwid}"
        if user_key in active_apk_keys:
            del active_apk_keys[user_key]
            
        # 2. Save it to the text files
        save_key_history(APK_HISTORY_FILE, apk_key_history)
        save_keys(APK_KEYS_FILE, active_apk_keys)

        print(f"[SUCCESS] App Key Activated! {user_key} -> HWID: {user_hwid}")
        return jsonify({"status": "success", "message": "ACTIVATED & BOUND TO DEVICE"}), 200

    if current_status.startswith("USED_BY:"):
        bound_hwid = current_status.split(":")[1]
        if bound_hwid == user_hwid:
            return jsonify({"status": "success", "message": "AUTHENTICATION SUCCESSFUL"}), 200
        else:
            return jsonify({"status": "error", "message": "KEY BOUND TO ANOTHER DEVICE"}), 403

    return jsonify({"status": "error", "message": "Unknown Key Error"}), 400

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ENTRY POINT (DUAL-THREADING)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    remove_expired_users()
    print("  ✅ Bot is running with Tiered Reseller System Enabled!")
    
    # Start the Flask API on a background thread so the Bot can still run
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port, use_reloader=False)).start()
    
    # Start the Telegram Bot
    bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=20)
