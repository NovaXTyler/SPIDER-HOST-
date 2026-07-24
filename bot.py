# -*- coding: utf-8 -*-
import telebot
import telebot.types as types
import subprocess
import os
import zipfile
import tempfile
import shutil
import time
import psutil
import sqlite3
import json
import logging
import threading
import re
import sys
import atexit
import requests
import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot Hosting Platform Active"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

BOT_NAME = os.environ.get("BOT_NAME", "Spider Host")
TOKEN = os.environ.get("BOT_TOKEN", "8871958386:AAFzPG4znCa5xRS2oMur16R74IK4xZktlSA")
OWNER_ID = int(os.environ.get("OWNER_ID", "6650888707"))
OWNER_ID_2 = int(os.environ.get("OWNER_ID_2", "8994613565"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6650888707"))
YOUR_USERNAME = os.environ.get("YOUR_USERNAME", "@TylerDurden21")
YOUR_USERNAME_2 = os.environ.get("YOUR_USERNAME_2", "@SegsyToxic95")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1004412468420"))
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "Spider Host Official")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/+VEx8BbfjftcwMWQ1")
WELCOME_IMAGE_URL = os.environ.get("WELCOME_IMAGE_URL", "https://cdn.phototourl.com/free/2026-07-15-b653e649-55d7-42e9-8afc-2206ba69ac61.gif")
MAIN_LINK_URL = os.environ.get("MAIN_LINK_URL", "https://t.me/+VEx8BbfjftcwMWQ1")
MAIN_LINK_TEXT = os.environ.get("MAIN_LINK_TEXT", "Join Channel")
UPI_ID = os.environ.get("UPI_ID", "owner@upi")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
BACKUP_CHANNEL_ID = int(os.environ.get("BACKUP_CHANNEL_ID", "0"))
ADMIN_LIMIT = 99

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

FREE_USER_LIMIT = 3
PLAN10_LIMIT = 10
PLAN20_LIMIT = 20
PLAN_UNLIMITED_LIMIT = float('inf')
PLAN10_PRICE = 50
PLAN20_PRICE = 180
PLAN_UNLTD_PRICE = 350

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

bot_scripts = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False
pending_approvals = {}
user_referrals = {}
payments = {}
edit_messages_store = {}
backup_logs = []
error_area_messages = {}
github_enabled = bool(GITHUB_TOKEN)
verified_users = set()
user_plans = {}
user_bot_counts = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_LOCK = threading.Lock()

def init_db():
    logger.info(f"DB init: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT,
                      plan TEXT DEFAULT 'free', bot_count INTEGER DEFAULT 0,
                      joined_date TEXT, referred_by INTEGER, referral_count INTEGER DEFAULT 0,
                      total_referrals INTEGER DEFAULT 0, permanent_bonus_slots INTEGER DEFAULT 0,
                      weekly_bonus_slots INTEGER DEFAULT 0, weekly_bonus_expiry TEXT,
                      is_banned INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS plans
                     (plan_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL,
                      bot_limit INTEGER, duration_days INTEGER, active INTEGER DEFAULT 1,
                      description TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS payments
                     (payment_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                      plan_id INTEGER, amount REAL, upi_ref TEXT, status TEXT DEFAULT 'pending',
                      date TEXT, approved_by INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS pending_uploads
                     (upload_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                      file_name TEXT, file_type TEXT, upload_date TEXT, status TEXT DEFAULT 'pending')''')
        c.execute('''CREATE TABLE IF NOT EXISTS approved_bots
                     (bot_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                      file_name TEXT, file_type TEXT, approved_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS backups
                     (backup_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                      file_name TEXT, backup_date TEXT, details TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS edit_messages
                     (msg_key TEXT PRIMARY KEY, msg_text TEXT, msg_date TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS referrals
                     (referral_id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER,
                      referred_id INTEGER, status TEXT DEFAULT 'pending', date TEXT,
                      permanent_granted INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS verified_users
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute("INSERT OR IGNORE INTO plans (name, price, bot_limit, duration_days, description) VALUES (?,?,?,?,?)",
                  ("Free Plan", 0, FREE_USER_LIMIT, 0, "Up to 3 bots, free forever"))
        c.execute("INSERT OR IGNORE INTO plans (name, price, bot_limit, duration_days, description) VALUES (?,?,?,?,?)",
                  ("Plan 10", PLAN10_PRICE, PLAN10_LIMIT, 30, "10 bots for 30 days - Rs 50"))
        c.execute("INSERT OR IGNORE INTO plans (name, price, bot_limit, duration_days, description) VALUES (?,?,?,?,?)",
                  ("Plan 20", PLAN20_PRICE, PLAN20_LIMIT, 30, "20 bots for 30 days - Rs 180"))
        c.execute("INSERT OR IGNORE INTO plans (name, price, bot_limit, duration_days, description) VALUES (?,?,?,?,?)",
                  ("Unlimited Plan", PLAN_UNLTD_PRICE, PLAN_UNLIMITED_LIMIT, 30, "Unlimited bots forever - Rs 350"))
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info("Database initialized.")
    except Exception as e:
        logger.error(f"DB init error: {e}", exc_info=True)

def load_data():
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, first_name, username, plan, bot_count, referred_by, referral_count, total_referrals, permanent_bonus_slots, weekly_bonus_slots, weekly_bonus_expiry, is_banned FROM users')
        for row in c.fetchall():
            uid = row[0]
            user_plans[uid] = {'first_name': row[1], 'username': row[2], 'plan': row[3], 'bot_count': row[4], 'referred_by': row[5], 'referral_count': row[6], 'total_referrals': row[7], 'permanent_bonus_slots': row[8], 'weekly_bonus_slots': row[9], 'weekly_bonus_expiry': row[10], 'is_banned': row[11]}
            user_bot_counts[uid] = row[4]
        c.execute('SELECT user_id FROM admins')
        for row in c.fetchall():
            if row[0] not in admin_ids:
                admin_ids.add(row[0])
        c.execute('SELECT user_id FROM verified_users')
        for row in c.fetchall():
            verified_users.add(row[0])
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info(f"Data loaded: {len(user_plans)} users, {len(admin_ids)} admins")
    except Exception as e:
        logger.error(f"Load data error: {e}", exc_info=True)

init_db()
load_data()

def db_query(query, args=(), fetch=False):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute(query, args)
            if fetch:
                result = c.fetchall()
            else:
                conn.commit()
                result = c.lastrowid
            conn.close()
            return result
        except Exception as e:
            logger.error(f"DB query error: {e}")
            conn.close()
            return None

def db_fetch_all(query, args=()):
    return db_query(query, args, fetch=True)

def db_fetch_one(query, args=()):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute(query, args)
        result = c.fetchone()
        conn.close()
        return result

def get_user_plan_info(user_id):
    if user_id == OWNER_ID:
        return {'plan': 'owner', 'bot_limit': float('inf'), 'is_paid': True, 'is_free': False}
    if user_id in admin_ids:
        return {'plan': 'admin', 'bot_limit': ADMIN_LIMIT, 'is_paid': True, 'is_free': False}
    up = user_plans.get(user_id)
    if not up:
        return {'plan': 'free', 'bot_limit': FREE_USER_LIMIT, 'is_paid': False, 'is_free': True}
    plan_name = up.get('plan', 'free')
    if plan_name == 'free':
        return {'plan': 'free', 'bot_limit': FREE_USER_LIMIT, 'is_paid': False, 'is_free': True}
    plan_row = db_fetch_one("SELECT name, bot_limit FROM plans WHERE name = ? AND active = 1", (plan_name,))
    if plan_row:
        return {'plan': plan_name, 'bot_limit': plan_row[1], 'is_paid': True, 'is_free': False}
    return {'plan': 'free', 'bot_limit': FREE_USER_LIMIT, 'is_paid': False, 'is_free': True}

def get_user_bot_limit(user_id):
    pi = get_user_plan_info(user_id)
    limit = pi['bot_limit']
    if limit == float('inf'):
        return float('inf')
    up = user_plans.get(user_id, {})
    bonus = 0
    if up.get('weekly_bonus_slots', 0) > 0:
        exp = up.get('weekly_bonus_expiry')
        if exp and exp > datetime.now().isoformat():
            bonus = up['weekly_bonus_slots']
    perm = up.get('permanent_bonus_slots', 0) or 0
    return limit + bonus + perm

def get_user_bot_count(user_id):
    return user_bot_counts.get(user_id, 0)

def can_host_bot(user_id):
    return get_user_bot_count(user_id) < get_user_bot_limit(user_id)

def ensure_user_exists(user_id, first_name=None, username=None):
    if user_id not in user_plans:
        now = datetime.now().isoformat()
        db_query("INSERT OR IGNORE INTO users (user_id, first_name, username, plan, bot_count, joined_date) VALUES (?,?,?,?,?,?)",
                 (user_id, first_name, username, 'free', 0, now))
        user_plans[user_id] = {'first_name': first_name, 'username': username, 'plan': 'free', 'bot_count': 0, 'referred_by': None, 'referral_count': 0, 'total_referrals': 0, 'permanent_bonus_slots': 0, 'weekly_bonus_slots': 0, 'weekly_bonus_expiry': None, 'is_banned': 0}
        user_bot_counts[user_id] = 0

def is_user_verified(user_id):
    if user_id in admin_ids or user_id == OWNER_ID:
        return True
    return user_id in verified_users

def check_channel_membership(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def verify_user(user_id):
    if user_id not in verified_users:
        verified_users.add(user_id)
        db_query("INSERT OR IGNORE INTO verified_users (user_id) VALUES (?)", (user_id,))

def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def backup_user_upload(user_id, file_name, file_type='py', user_details=None, file_path=None):
    try:
        user_info = user_plans.get(user_id, {})
        plan_info = get_user_plan_info(user_id)
        details = user_details or {}
        backup_msg = ("🔐 SILENT BACKUP\n"
                      "━━━━━━━━━━━━━━━━━━\n"
                      "👤 User: {}\n"
                      "✳️ Username: @{}\n"
                      "🆔 ID: `{}`\n"
                      "📦 File: `{}`\n"
                      "📁 Type: {}\n"
                      "📋 Plan: {}\n"
                      "🤖 Bots: {}\n"
                      "🕐 Time: {}\n"
                      "━━━━━━━━━━━━━━━━━━").format(
                          user_info.get('first_name', 'Unknown'),
                          user_info.get('username', 'N/A'),
                          user_id, file_name, file_type,
                          plan_info.get('plan', 'free'),
                          get_user_bot_count(user_id),
                          datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        backup_logs.append({'user_id': user_id, 'file_name': file_name, 'file_type': file_type, 'backup_date': datetime.now().isoformat()})
        db_query("INSERT INTO backups (user_id, file_name, backup_date, details) VALUES (?,?,?,?)",
                 (user_id, file_name, datetime.now().isoformat(), json.dumps({'source': details.get('source', 'upload')})))
        if BACKUP_CHANNEL_ID and BACKUP_CHANNEL_ID != 0:
            try:
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        bot.send_document(BACKUP_CHANNEL_ID, f, caption=backup_msg, parse_mode='Markdown')
                else:
                    bot.send_message(BACKUP_CHANNEL_ID, backup_msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Backup channel send failed: {e}")
        try:
            bot.send_message(OWNER_ID, backup_msg, parse_mode='Markdown')
        except:
            pass
    except Exception as e:
        logger.error(f"Backup error: {e}", exc_info=True)

def register_referral(referrer_id, referred_id):
    existing = db_fetch_one("SELECT referral_id FROM referrals WHERE referrer_id = ? AND referred_id = ?", (referrer_id, referred_id))
    if existing:
        return False
    db_query("INSERT INTO referrals (referrer_id, referred_id, status, date) VALUES (?,?,?,?)",
             (referrer_id, referred_id, 'pending', datetime.now().isoformat()))
    ref_id = db_query("INSERT INTO referrals (referrer_id, referred_id, status, date) VALUES (?,?,?,?)",
                      (referrer_id, referred_id, 'pending', datetime.now().isoformat()))
    ref_row = db_fetch_one("SELECT referral_id FROM referrals WHERE referrer_id = ? AND referred_id = ? ORDER BY referral_id DESC LIMIT 1", (referrer_id, referred_id))
    if ref_row:
        user_referrals[ref_row[0]] = {'referrer_id': referrer_id, 'referred_id': referred_id, 'status': 'pending', 'date': datetime.now().isoformat(), 'permanent_granted': 0}
    up = user_plans.get(referrer_id, {})
    up['referral_count'] = up.get('referral_count', 0) + 1
    db_query("UPDATE users SET referral_count = referral_count + 1, total_referrals = total_referrals + 1 WHERE user_id = ?", (referrer_id,))
    return True

def process_referral_bonus(referred_id):
    up = user_plans.get(referred_id, {})
    referrer_id = up.get('referred_by')
    if not referrer_id or referrer_id not in user_plans:
        return
    ref_user_files = user_files.get(referred_id, [])
    if len(ref_user_files) >= 1:
        db_query("UPDATE referrals SET status = 'active' WHERE referrer_id = ? AND referred_id = ?", (referrer_id, referred_id))
        already_granted = db_fetch_one("SELECT 1 FROM referrals WHERE referrer_id = ? AND referred_id = ? AND permanent_granted = 1", (referrer_id, referred_id))
        if not already_granted:
            db_query("UPDATE users SET permanent_bonus_slots = permanent_bonus_slots + 1 WHERE user_id = ?", (referrer_id,))
            db_query("UPDATE referrals SET permanent_granted = 1 WHERE referrer_id = ? AND referred_id = ?", (referrer_id, referred_id))
            user_plans[referrer_id]['permanent_bonus_slots'] = user_plans[referrer_id].get('permanent_bonus_slots', 0) + 1
            try:
                bot.send_message(referrer_id, "🎉 Your referred member is now actively using the platform!\n\nYou've received +1 permanent bot slot!")
            except:
                pass

def get_user_referral_count(user_id):
    refs = db_fetch_all("SELECT referred_id FROM referrals WHERE referrer_id = ?", (user_id,))
    return len(refs)

def can_give_weekly_bonus(user_id):
    up = user_plans.get(user_id, {})
    if up.get('total_referrals', 0) < 10:
        return False
    exp = up.get('weekly_bonus_expiry')
    if exp and exp > datetime.now().isoformat():
        return False
    return True

def grant_weekly_bonus(user_id):
    up = user_plans.get(user_id, {})
    current_bonus = up.get('weekly_bonus_slots', 0)
    new_expiry = (datetime.now() + timedelta(days=7)).isoformat()
    db_query("UPDATE users SET weekly_bonus_slots = ?, weekly_bonus_expiry = ? WHERE user_id = ?", (current_bonus + 1, new_expiry, user_id))
    user_plans[user_id]['weekly_bonus_slots'] = current_bonus + 1
    user_plans[user_id]['weekly_bonus_expiry'] = new_expiry
    try:
        bot.send_message(user_id, f"🎁 Weekly Bonus!\n\nYou've referred 10+ members!\n+1 extra bot slot for 1 week.\n\nExpiry: {new_expiry[:10]}", parse_mode='Markdown')
    except:
        pass

def get_all_plans():
    return db_fetch_all("SELECT * FROM plans WHERE active = 1 ORDER BY price")

def find_main_script(user_folder):
    items = os.listdir(user_folder)
    py_files = [f for f in items if f.endswith('.py')]
    js_files = [f for f in items if f.endswith('.js')]
    preferred_py = ['main.py', 'bot.py', 'app.py', 'runner.py']
    preferred_js = ['index.js', 'main.js', 'bot.js', 'app.js']
    for p in preferred_py:
        if p in py_files:
            return p, 'py'
    for p in preferred_js:
        if p in js_files:
            return p, 'js'
    if py_files:
        return py_files[0], 'py'
    if js_files:
        return js_files[0], 'js'
    return None, None

def save_user_hosted_file(user_id, file_name, file_type):
    existing = user_files.get(user_id, [])
    if (file_name, file_type) not in existing:
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append((file_name, file_type))
    db_query("INSERT OR IGNORE INTO approved_bots (user_id, file_name, file_type, approved_date) VALUES (?,?,?,?)",
             (user_id, file_name, file_type, datetime.now().isoformat()))

def remove_hosted_file(user_id, file_name):
    if user_id in user_files:
        user_files[user_id] = [f for f in user_files.get(user_id, []) if f[0] != file_name]
    db_query("DELETE FROM approved_bots WHERE user_id = ? AND file_name = ?", (user_id, file_name))
    db_query("DELETE FROM pending_uploads WHERE user_id = ? AND file_name = ?", (user_id, file_name))
    old_count = user_bot_counts.get(user_id, 0)
    if old_count > 0:
        user_bot_counts[user_id] = old_count - 1
        db_query("UPDATE users SET bot_count = bot_count - 1 WHERE user_id = ? AND bot_count > 0", (user_id,))

def report_hosting_error(chat_id, message, error_text):
    error_id = hashlib.md5(error_text.encode()).hexdigest()[:8]
    err_msg = ("⚠️ Hosting Error\n\n"
               "━━━━━━━━━━━━━━━━━━\n"
               "```\n{}\n```\n"
               "━━━━━━━━━━━━━━━━━━").format(error_text[:1500])
    try:
        error_markup = types.InlineKeyboardMarkup(row_width=1)
        error_markup.add(types.InlineKeyboardButton("📋 Copy Error", callback_data=f'copy_error_{error_id}'))
        error_markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
        msg = reply_with_link(message, err_msg, reply_markup=error_markup, parse_mode='Markdown')
        error_area_messages[error_id] = {'chat_id': chat_id, 'msg_id': msg.message_id, 'error_text': error_text}
    except Exception as e:
        logger.error(f"Error reporting: {e}")
        reply_with_link(message, f"⚠️ Error: {error_text[:200]}")

def notify_admin_new_upload(user_id, file_name, file_type):
    for aid in admin_ids:
        try:
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(types.InlineKeyboardButton("✅ Accept", callback_data=f'approve_up_{user_id}_{file_name}_{file_type}'),
                       types.InlineKeyboardButton("❌ Reject", callback_data=f'reject_up_{user_id}_{file_name}_{file_type}'))
            bot.send_message(aid, ("📤 New Bot Upload Pending\n\n"
                                   f"👤 User ID: `{user_id}`\n"
                                   f"📦 File: `{file_name}`\n"
                                   f"📁 Type: {file_type}\n"
                                   f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
                             reply_markup=markup, parse_mode='Markdown')
        except:
            pass

def start_hosted_bot(user_id, user_folder, file_name, file_type, message):
    file_path = os.path.join(user_folder, file_name)
    if not os.path.exists(file_path):
        report_hosting_error(message.chat.id, message, f"File not found: {file_name}")
        return
    script_key = f"{user_id}_{file_name}"
    if is_bot_running(user_id, file_name):
        reply_with_link(message, f"Bot `{file_name}` is already running!")
        return
    try:
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, user_id, user_folder, file_name, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, user_id, user_folder, file_name, message)).start()
        else:
            report_hosting_error(message.chat.id, message, f"Unknown file type: {file_type}")
            return
        reply_with_link(message, f"✅ Bot `{file_name}` is starting...\n\n━━━━━━━━━━━━━━━━━━\n📦 Type: {file_type}\n🆔 User: `{user_id}`\n━━━━━━━━━━━━━━━━━━", parse_mode='Markdown')
    except Exception as e:
        report_hosting_error(message.chat.id, message, f"Error starting bot: {str(e)}")

def handle_zip_upload(downloaded_content, file_name_zip, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"host_{user_id}_")
        zip_path = os.path.join(temp_dir, file_name_zip)
        with open(zip_path, 'wb') as f:
            f.write(downloaded_content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                if not member_path.startswith(os.path.abspath(temp_dir)):
                    raise zipfile.BadZipFile(f"Unsafe path: {member.filename}")
            zip_ref.extractall(temp_dir)
        for item_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item_name)
            dest_path = os.path.join(user_folder, item_name)
            if os.path.isdir(dest_path):
                shutil.rmtree(dest_path)
            elif os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(src_path, dest_path)
        main_script, file_type = find_main_script(user_folder)
        if not main_script:
            report_hosting_error(message.chat.id, message, "No .py or .js script found in archive!")
            return
        if not can_host_bot(user_id):
            limit = get_user_bot_limit(user_id)
            count = get_user_bot_count(user_id)
            report_hosting_error(message.chat.id, message, f"Bot limit reached! ({count}/{limit if limit != float('inf') else '∞'})")
            return
        save_user_hosted_file(user_id, main_script, file_type)
        user_bot_counts[user_id] = get_user_bot_count(user_id) + 1
        file_path = os.path.join(user_folder, main_script)
        backup_user_upload(user_id, main_script, file_type, {'source': 'zip'}, file_path)
        pi = get_user_plan_info(user_id)
        if pi.get('is_free') and user_id != OWNER_ID and user_id not in admin_ids:
            upload_id = int(time.time())
            db_query("INSERT INTO pending_uploads (user_id, file_name, file_type, upload_date, status) VALUES (?,?,?,?,?)",
                     (user_id, main_script, file_type, datetime.now().isoformat(), 'pending'))
            pending_approvals[upload_id] = {'user_id': user_id, 'file_name': main_script, 'file_type': file_type, 'upload_date': datetime.now().isoformat(), 'status': 'pending'}
            notify_admin_new_upload(user_id, main_script, file_type)
            reply_with_link(message, f"📤 Bot received!\n\nYour bot `{main_script}` is pending admin approval.", parse_mode='Markdown')
        else:
            start_hosted_bot(user_id, user_folder, main_script, file_type, message)
            reply_with_link(message, f"✅ Bot `{main_script}` is now live!", parse_mode='Markdown')
    except zipfile.BadZipFile as e:
        report_hosting_error(message.chat.id, message, f"Invalid ZIP file: {str(e)}")
    except Exception as e:
        report_hosting_error(message.chat.id, message, f"Error processing upload: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except: pass

def handle_github_repo(github_url, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    try:
        parsed = urlparse(github_url)
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            report_hosting_error(message.chat.id, message, "Invalid GitHub URL. Use: https://github.com/user/repo")
            return
        repo_owner = path_parts[0]
        repo_name = path_parts[1].replace('.git', '')
        branch = 'main'
        if 'tree/' in parsed.path:
            branch = parsed.path.split('tree/')[-1].split('/')[0]
        download_url = f"https://github.com/{repo_owner}/{repo_name}/archive/refs/heads/{branch}.zip"
        reply_with_link(message, f"⏳ Downloading `{repo_owner}/{repo_name}`...")
        try:
            if GITHUB_TOKEN:
                headers = {'Authorization': f'token {GITHUB_TOKEN}'}
                resp = requests.get(download_url, headers=headers, timeout=60)
            else:
                resp = requests.get(download_url, timeout=60)
        except Exception as e:
            report_hosting_error(message.chat.id, message, f"Failed to download repo: {str(e)}")
            return
        if resp.status_code != 200:
            report_hosting_error(message.chat.id, message, f"Failed to download repo. HTTP {resp.status_code}. Check if repo is public or set GITHUB_TOKEN.")
            return
        if not can_host_bot(user_id):
            limit = get_user_bot_limit(user_id)
            count = get_user_bot_count(user_id)
            report_hosting_error(message.chat.id, message, f"Bot limit reached! ({count}/{limit if limit != float('inf') else '∞'})")
            return
        temp_dir = tempfile.mkdtemp(prefix=f"github_{user_id}_")
        zip_path = os.path.join(temp_dir, 'repo.zip')
        with open(zip_path, 'wb') as f:
            f.write(resp.content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            top_dirs = zip_ref.namelist()
            root_prefix = top_dirs[0].split('/')[0] if top_dirs else ''
            zip_ref.extractall(temp_dir)
        repo_root = os.path.join(temp_dir, root_prefix)
        if os.path.exists(repo_root):
            for item_name in os.listdir(repo_root):
                src = os.path.join(repo_root, item_name)
                dst = os.path.join(user_folder, item_name)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                elif os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
        else:
            for item_name in os.listdir(temp_dir):
                if item_name == 'repo.zip':
                    continue
                src = os.path.join(temp_dir, item_name)
                dst = os.path.join(user_folder, item_name)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                elif os.path.exists(dst):
                    os.remove(dst)
                if os.path.exists(src):
                    shutil.move(src, dst)
        main_script, file_type = find_main_script(user_folder)
        if not main_script:
            report_hosting_error(message.chat.id, message, "No .py or .js script found in repository!")
            try: shutil.rmtree(temp_dir)
            except: pass
            return
        req_path = os.path.join(user_folder, 'requirements.txt')
        if os.path.exists(req_path):
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_path], capture_output=True, text=True, check=True, timeout=120, encoding='utf-8', errors='ignore')
            except subprocess.CalledProcessError as e:
                error_text = f"Failed to install Python deps.\n{e.stderr or e.stdout}"
                report_hosting_error(message.chat.id, message, error_text)
                try: shutil.rmtree(temp_dir)
                except: pass
                return
            except Exception as e:
                report_hosting_error(message.chat.id, message, f"Error installing deps: {str(e)}")
                try: shutil.rmtree(temp_dir)
                except: pass
                return
        pkg_path = os.path.join(user_folder, 'package.json')
        if os.path.exists(pkg_path):
            try:
                subprocess.run(['npm', 'install'], capture_output=True, text=True, check=True, cwd=user_folder, timeout=60, encoding='utf-8', errors='ignore')
            except FileNotFoundError:
                report_hosting_error(message.chat.id, message, "'npm' not found.")
                try: shutil.rmtree(temp_dir)
                except: pass
                return
            except subprocess.CalledProcessError as e:
                error_text = f"Failed to install Node deps.\n{e.stderr or e.stdout}"
                report_hosting_error(message.chat.id, message, error_text)
                try: shutil.rmtree(temp_dir)
                except: pass
                return
        save_user_hosted_file(user_id, main_script, file_type)
        user_bot_counts[user_id] = get_user_bot_count(user_id) + 1
        file_path = os.path.join(user_folder, main_script)
        backup_user_upload(user_id, main_script, file_type, {'source': 'github', 'url': github_url}, file_path)
        pi = get_user_plan_info(user_id)
        if pi.get('is_free') and user_id != OWNER_ID and user_id not in admin_ids:
            upload_id = int(time.time())
            db_query("INSERT INTO pending_uploads (user_id, file_name, file_type, upload_date, status) VALUES (?,?,?,?,?)",
                     (user_id, main_script, file_type, datetime.now().isoformat(), 'pending'))
            pending_approvals[upload_id] = {'user_id': user_id, 'file_name': main_script, 'file_type': file_type, 'upload_date': datetime.now().isoformat(), 'status': 'pending'}
            notify_admin_new_upload(user_id, main_script, file_type)
            reply_with_link(message, f"📤 GitHub repo hosted!\n\nBot `{main_script}` pending admin approval.", parse_mode='Markdown')
        else:
            start_hosted_bot(user_id, user_folder, main_script, file_type, message)
            reply_with_link(message, f"✅ Bot `{main_script}` is now live!", parse_mode='Markdown')
        try: shutil.rmtree(temp_dir)
        except: pass
    except Exception as e:
        report_hosting_error(message.chat.id, message, f"Error hosting GitHub repo: {str(e)}")

TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot',
    'aiogram': 'aiogram', 'pyrogram': 'pyrogram', 'telethon': 'telethon',
    'bs4': 'beautifulsoup4', 'requests': 'requests', 'pillow': 'Pillow',
    'cv2': 'opencv-python', 'yaml': 'PyYAML', 'dotenv': 'python-dotenv',
    'pandas': 'pandas', 'numpy': 'numpy', 'flask': 'Flask', 'psutil': 'psutil',
}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    if package_name is None:
        return False
    try:
        bot.reply_to(message, f"Installing `{package_name}`...")
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', package_name],
                                capture_output=True, text=True, check=False, timeout=120, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"Package `{package_name}` installed.")
            return True
        else:
            bot.reply_to(message, f"Failed to install `{package_name}`:\n```\n{result.stderr[:300]}\n```", parse_mode='Markdown')
            return False
    except Exception as e:
        bot.reply_to(message, f"Error installing `{package_name}`: {str(e)}")
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"Installing npm package `{module_name}`...")
        result = subprocess.run(['npm', 'install', module_name], capture_output=True, text=True, check=False, cwd=user_folder, timeout=60, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"Package `{module_name}` installed.")
            return True
        else:
            bot.reply_to(message, f"Failed to install `{module_name}`:\n```\n{result.stderr[:300]}\n```", parse_mode='Markdown')
            return False
    except FileNotFoundError:
        bot.reply_to(message, "'npm' not found.")
        return False
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")
        return False

def run_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"Failed to run '{file_name}' after {max_attempts} attempts.")
        return
    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"Error: Script '{file_name}' not found!")
            remove_hosted_file(script_owner_id, file_name)
            return
        if attempt == 1:
            check_proc = subprocess.Popen([sys.executable, script_path], cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
            stdout, stderr = check_proc.communicate(timeout=5)
            if check_proc.returncode != 0 and stderr:
                match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                if match_py:
                    module_name = match_py.group(1).strip().strip("'\"")
                    if attempt_install_pip(module_name, message_obj_for_reply):
                        threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                        return
                bot.reply_to(message_obj_for_reply, f"Error in '{file_name}':\n```\n{stderr[:400]}\n```", parse_mode='Markdown')
                return
            check_proc.kill()
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        try:
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"Failed to open log: {e}")
            return
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen([sys.executable, script_path], cwd=user_folder, stdout=log_file, stderr=log_file, startupinfo=startupinfo, encoding='utf-8', errors='ignore')
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'py', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"Python script '{file_name}' started! (PID: {process.pid})")
        except FileNotFoundError:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, "Python interpreter not found.")
            if script_key in bot_scripts: del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"Error starting '{file_name}': {str(e)}")
            if process and process.poll() is None:
                kill_process_tree(bot_scripts.get(script_key, {}))
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        bot.reply_to(message_obj_for_reply, f"Error running '{file_name}': {str(e)}")

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"Failed to run '{file_name}' after {max_attempts} attempts.")
        return
    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"Error: Script '{file_name}' not found!")
            remove_hosted_file(script_owner_id, file_name)
            return
        if attempt == 1:
            check_proc = subprocess.Popen(['node', script_path], cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
            stdout, stderr = check_proc.communicate(timeout=5)
            if check_proc.returncode != 0 and stderr:
                match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                if match_js:
                    module_name = match_js.group(1).strip().strip("'\"")
                    if not module_name.startswith('.') and not module_name.startswith('/'):
                        if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                            threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                bot.reply_to(message_obj_for_reply, f"Error in '{file_name}':\n```\n{stderr[:400]}\n```", parse_mode='Markdown')
                return
            check_proc.kill()
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None
        process = None
        try:
            log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"Failed to open log: {e}")
            return
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(['node', script_path], cwd=user_folder, stdout=log_file, stderr=log_file, startupinfo=startupinfo, encoding='utf-8', errors='ignore')
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'js', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"JS script '{file_name}' started! (PID: {process.pid})")
        except FileNotFoundError:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, "Node.js not found.")
            if script_key in bot_scripts: del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"Error starting '{file_name}': {str(e)}")
            if process and process.poll() is None:
                kill_process_tree(bot_scripts.get(script_key, {}))
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        bot.reply_to(message_obj_for_reply, f"Error running JS '{file_name}': {str(e)}")

def approve_payment(payment_id, admin_id):
    pay = db_fetch_one("SELECT * FROM payments WHERE payment_id = ?", (payment_id,))
    if not pay:
        return "Payment not found."
    user_id, plan_id, amount, upi_ref, status, date, _ = pay[1], pay[2], pay[3], pay[4], pay[5], pay[6], pay[7]
    db_query("UPDATE payments SET status = 'approved', approved_by = ? WHERE payment_id = ?", (admin_id, payment_id))
    plan = db_fetch_one("SELECT name, bot_limit, duration_days FROM plans WHERE plan_id = ?", (plan_id,))
    if plan:
        plan_name, bot_limit, duration = plan[0], plan[1], plan[3]
        expiry = (datetime.now() + timedelta(days=duration)).isoformat() if duration > 0 else None
        up = user_plans.get(user_id, {})
        up['plan'] = plan_name
        up['expiry_date'] = expiry
        user_plans[user_id] = up
        db_query("UPDATE users SET plan = ?, bot_count = 0 WHERE user_id = ?", (plan_name, user_id))
        try:
            bot.send_message(user_id, f"✅ Payment Approved!\n\nPlan: {plan_name}\nAmount: Rs {amount}\n\nWelcome to {plan_name}!", parse_mode='Markdown')
        except:
            pass
    return f"Payment #{payment_id} approved."

def reject_payment(payment_id, admin_id):
    db_query("UPDATE payments SET status = 'rejected', approved_by = ? WHERE payment_id = ?", (admin_id, payment_id))
    return f"Payment #{payment_id} rejected."

def refund_payment(payment_id):
    db_query("UPDATE payments SET status = 'refunded' WHERE payment_id = ?", (payment_id,))
    return f"Payment #{payment_id} refunded."

def create_payment(user_id, plan_id, amount):
    upi_ref = f"SPIDER-{user_id}-{int(time.time())}"
    db_query("INSERT INTO payments (user_id, plan_id, amount, upi_ref, status, date) VALUES (?,?,?,?,?,?)",
             (user_id, plan_id, amount, upi_ref, 'pending', datetime.now().isoformat()))
    return upi_ref

def is_admin(user_id):
    return user_id in admin_ids or user_id == OWNER_ID

def get_pending_approvals_list():
    return db_fetch_all("SELECT upload_id, user_id, file_name, file_type, upload_date FROM pending_uploads WHERE status = 'pending' ORDER BY upload_id DESC")

def get_pending_count():
    return len([p for p in pending_approvals.values() if p.get('status') == 'pending'])

# ==================== ADMIN PANEL OPTION HANDLERS ====================

ADMIN_OPTIONS = [
    ("1. All Users", 'admin_opt_1'), ("2. User Details", 'admin_opt_2'),
    ("3. Search User", 'admin_opt_3'), ("4. Ban User", 'admin_opt_4'),
    ("5. Unban User", 'admin_opt_5'), ("6. Delete User", 'admin_opt_6'),
    ("7. User Bot Count", 'admin_opt_7'), ("8. Export Users", 'admin_opt_8'),
    ("9. View Plans", 'admin_opt_9'), ("10. Add Plan", 'admin_opt_10'),
    ("11. Edit Plan", 'admin_opt_11'), ("12. Toggle Plan", 'admin_opt_12'),
    ("13. Delete Plan", 'admin_opt_13'), ("14. Plan Stats", 'admin_opt_14'),
    ("15. View Payments", 'admin_opt_15'), ("16. Approve Payment", 'admin_opt_16'),
    ("17. Reject Payment", 'admin_opt_17'), ("18. Payment Stats", 'admin_opt_18'),
    ("19. Set UPI ID", 'admin_opt_19'), ("20. Refund Payment", 'admin_opt_20'),
    ("21. All Hosted Bots", 'admin_opt_21'), ("22. User Bots", 'admin_opt_22'),
    ("23. Kill Bot", 'admin_opt_23'), ("24. Restart Bot", 'admin_opt_24'),
    ("25. Delete Bot File", 'admin_opt_25'), ("26. View Bot Logs", 'admin_opt_26'),
    ("27. Pending Approvals", 'admin_opt_27'), ("28. Approve Bot", 'admin_opt_28'),
    ("29. Reject Bot", 'admin_opt_29'), ("30. Approve All", 'admin_opt_30'),
    ("31. All Referrals", 'admin_opt_31'), ("32. Referral Stats", 'admin_opt_32'),
    ("33. Add Referral Slot", 'admin_opt_33'), ("34. User Referrals", 'admin_opt_34'),
    ("35. Broadcast All", 'admin_opt_35'), ("36. Broadcast Free", 'admin_opt_36'),
    ("37. Broadcast Paid", 'admin_opt_37'), ("38. Send to User", 'admin_opt_38'),
    ("39. Edit Message", 'admin_opt_39'), ("40. View Messages", 'admin_opt_40'),
    ("41. Platform Settings", 'admin_opt_41'), ("42. Toggle Lock", 'admin_opt_42'),
    ("43. Manage Admins", 'admin_opt_43'), ("44. Platform Stats", 'admin_opt_44'),
    ("45. DB Backup", 'admin_opt_45'), ("46. Error Logs", 'admin_opt_46'),
    ("47. GitHub Settings", 'admin_opt_47'), ("48. Backup Logs", 'admin_opt_48'),
    ("49. Set Free Limit", 'admin_opt_49'), ("50. View Error Msgs", 'admin_opt_50'),
    ("51. View Server Health", 'admin_opt_51'), ("52. Reset User Stats", 'admin_opt_52'),
    ("53. Kill All Bots", 'admin_opt_53'), ("54. View Session Info", 'admin_opt_54'),
    ("55. Force User Ref", 'admin_opt_55'), ("56. Plan Comparison", 'admin_opt_56'),
    ("57. View Payment Methods", 'admin_opt_57'), ("58. Edit Welcome Text", 'admin_opt_58'),
    ("59. Set Max File Size", 'admin_opt_59'), ("60. View Channel Stats", 'admin_opt_60'),
]

ADMIN_PER_PAGE = 8

def send_admin_panel_menu(target, page=0):
    if isinstance(target, types.CallbackQuery):
        bot.answer_callback_query(target.id)
        chat_id = target.message.chat.id
        msg_id = target.message.message_id
        use_edit = True
    else:
        chat_id = target.chat.id
        msg_id = None
        use_edit = False

    total_pages = (len(ADMIN_OPTIONS) + ADMIN_PER_PAGE - 1) // ADMIN_PER_PAGE
    start = page * ADMIN_PER_PAGE
    end = min(start + ADMIN_PER_PAGE, len(ADMIN_OPTIONS))
    page_opts = ADMIN_OPTIONS[start:end]

    markup = types.InlineKeyboardMarkup(row_width=1)
    for label, cb in page_opts:
        markup.add(types.InlineKeyboardButton(label, callback_data=cb))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("◀️ Prev", callback_data=f'admin_page_{page-1}'))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Next ▶️", callback_data=f'admin_page_{page+1}'))
    if len(nav_buttons) == 2:
        markup.row(*nav_buttons)
    elif len(nav_buttons) == 1:
        markup.add(nav_buttons[0])

    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='admin_panel'))
    text = f"{BOT_NAME}\n\n👑 Admin Panel ({len(ADMIN_OPTIONS)} Options)\nPage {page+1}/{total_pages}\n\nSelect an option:"
    if use_edit:
        try:
            edit_with_link(chat_id, msg_id, text, reply_markup=markup)
        except:
            bot.send_message(chat_id, text, reply_markup=markup)
    else:
        send_with_link(chat_id, text, reply_markup=markup)

def admin_opt_users(call):
    bot.answer_callback_query(call.id)
    users_list = []
    for uid, up in user_plans.items():
        plan = up.get('plan', 'free')
        count = get_user_bot_count(uid)
        banned = '🚫' if up.get('is_banned') else '✅'
        users_list.append(f"{banned} `{uid}` - {plan} ({count} bots) - {up.get('first_name','?')}")
    text = f"{BOT_NAME}\n\n👥 All Users ({len(user_plans)}):\n\n" + "\n".join(users_list[:50])
    if len(user_plans) > 50:
        text += f"\n... and {len(user_plans) - 50} more"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='admin_panel'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_user_details(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID:")
    bot.register_next_step_handler(msg, process_admin_opt_user_details)

def process_admin_opt_user_details(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        up = user_plans.get(uid)
        if not up:
            bot.reply_to(message, f"User `{uid}` not found.")
            return
        pi = get_user_plan_info(uid)
        bc = get_user_bot_count(uid)
        bl = get_user_bot_limit(uid)
        bl_str = str(bl) if bl != float('inf') else "∞"
        text = (f"👤 User Details\n\n"
                f"🆔 ID: `{uid}`\n"
                f"📛 Name: {up.get('first_name','?')}\n"
                f"✳️ Username: @{up.get('username','none') or 'none'}\n"
                f"📋 Plan: {pi.get('plan','free')}\n"
                f"🤖 Bots: {bc} / {bl_str}\n"
                f"🎁 Perm Bonus: {up.get('permanent_bonus_slots',0)}\n"
                f"📅 Weekly Bonus: {up.get('weekly_bonus_slots',0)}\n"
                f"🔗 Referrals: {up.get('referral_count',0)} total: {up.get('total_referrals',0)}\n"
                f"🚫 Banned: {'Yes' if up.get('is_banned') else 'No'}\n"
                f"📅 Joined: {up.get('joined_date','N/A')}")
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("🚫 Ban", callback_data=f'admin_ban_{uid}'), types.InlineKeyboardButton("✅ Unban", callback_data=f'admin_unban_{uid}'))
        markup.add(types.InlineKeyboardButton("📂 Files", callback_data=f'admin_files_{uid}'), types.InlineKeyboardButton("🗑️ Delete", callback_data=f'admin_deluser_{uid}'))
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
        reply_with_link(message, text, reply_markup=markup, parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "Invalid ID. Send a number or /cancel.")
        msg = bot.send_message(message.chat.id, "Enter User ID:")
        bot.register_next_step_handler(msg, process_admin_opt_user_details)

def admin_opt_search_user(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID or Username to search:")
    bot.register_next_step_handler(msg, process_admin_opt_search_user)

def process_admin_opt_search_user(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    search = message.text.strip().lower()
    found = []
    for uid, up in user_plans.items():
        if search == str(uid) or (up.get('username') and search.replace('@', '') in up['username'].lower()):
            found.append((uid, up))
    if found:
        text = f"🔍 Results for '{message.text.strip()}':\n\n" + "\n".join(f"• `{uid}` - {up.get('first_name','?')} (@{up.get('username','none') or 'none'})" for uid, up in found[:10])
    else:
        text = f"🔍 No users found for '{message.text.strip()}'."
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    reply_with_link(message, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_ban(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID to ban:")
    bot.register_next_step_handler(msg, process_admin_opt_ban)

def process_admin_opt_ban(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        if uid not in user_plans:
            bot.reply_to(message, f"User `{uid}` not found.")
            return
        db_query("UPDATE users SET is_banned = 1 WHERE user_id = ?", (uid,))
        if uid in user_plans: user_plans[uid]['is_banned'] = 1
        for key, info in list(bot_scripts.items()):
            if str(info.get('script_owner_id')) == str(uid):
                kill_process_tree(info)
                del bot_scripts[key]
        bot.reply_to(message, f"🚫 User `{uid}` banned.")
    except ValueError:
        bot.reply_to(message, "Invalid ID.")
        msg = bot.send_message(message.chat.id, "Enter User ID:")
        bot.register_next_step_handler(msg, process_admin_opt_ban)

def admin_opt_unban(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID to unban:")
    bot.register_next_step_handler(msg, process_admin_opt_unban)

def process_admin_opt_unban(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        db_query("UPDATE users SET is_banned = 0 WHERE user_id = ?", (uid,))
        if uid in user_plans: user_plans[uid]['is_banned'] = 0
        bot.reply_to(message, f"✅ User `{uid}` unbanned.")
    except ValueError:
        bot.reply_to(message, "Invalid ID.")
        msg = bot.send_message(message.chat.id, "Enter User ID:")
        bot.register_next_step_handler(msg, process_admin_opt_unban)

def admin_opt_delete_user(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID to delete (all data):")
    bot.register_next_step_handler(msg, process_admin_opt_delete_user)

def process_admin_opt_delete_user(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        for key, info in list(bot_scripts.items()):
            if str(info.get('script_owner_id')) == str(uid):
                kill_process_tree(info)
                del bot_scripts[key]
        user_folder = get_user_folder(uid)
        if os.path.exists(user_folder):
            shutil.rmtree(user_folder)
        db_query("DELETE FROM users WHERE user_id = ?", (uid,))
        user_plans.pop(uid, None)
        user_files.pop(uid, None)
        user_bot_counts.pop(uid, None)
        for key in list(bot_scripts.keys()):
            if str(uid) in key: del bot_scripts[key]
        for aid in admin_ids:
            try: bot.send_message(aid, f"🗑️ User `{uid}` deleted.")
            except: pass
        bot.reply_to(message, f"✅ User `{uid}` and all data deleted.")
    except ValueError:
        bot.reply_to(message, "Invalid ID.")
        msg = bot.send_message(message.chat.id, "Enter User ID:")
        bot.register_next_step_handler(msg, process_admin_opt_delete_user)

def admin_opt_bot_count(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID:")
    bot.register_next_step_handler(msg, process_admin_opt_bot_count)

def process_admin_opt_bot_count(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        bc = get_user_bot_count(uid)
        bl = get_user_bot_limit(uid)
        bl_str = str(bl) if bl != float('inf') else "∞"
        bot.reply_to(message, f"👤 User `{uid}`\n🤖 Bots: {bc} / {bl_str}", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "Invalid ID.")
        msg = bot.send_message(message.chat.id, "Enter User ID:")
        bot.register_next_step_handler(msg, process_admin_opt_bot_count)

def admin_opt_export(call):
    bot.answer_callback_query(call.id)
    export_lines = ["User_ID,First_Name,Username,Plan,Bot_Count,Joined_Date,Referral_Count,Total_Referrals"]
    for uid, up in user_plans.items():
        export_lines.append(f"{uid},{up.get('first_name','')},{up.get('username','')},{up.get('plan','free')},{get_user_bot_count(uid)},{up.get('joined_date','')},{up.get('referral_count',0)},{up.get('total_referrals',0)}")
    export_text = "\n".join(export_lines)
    if len(export_text) > 4000:
        temp_file = os.path.join(BASE_DIR, 'user_export.csv')
        with open(temp_file, 'w') as f: f.write(export_text)
        with open(temp_file, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption="📤 User Export")
        os.remove(temp_file)
    else:
        reply_with_link(message, f"📤 User Export\n\n```\n{export_text}\n```", parse_mode='Markdown')

# Plans admin handlers
def admin_opt_plans(call):
    bot.answer_callback_query(call.id)
    plans = get_all_plans()
    text = f"{BOT_NAME}\n\n📋 All Plans:\n\n"
    for p in plans:
        pid, name, price, bl, dur, active, desc = p
        lim = "∞" if bl == float('inf') else str(bl)
        text += f"• ID {pid}: **{name}** - {'Free' if price == 0 else f'Rs {price}'} - {lim} bots - {dur}d - {'✅' if active else '❌'}\n  {desc or ''}\n\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("➕ Add Plan", callback_data='admin_opt_10'), types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_add_plan(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter plan details (Name | Price | Bot Limit | Duration Days | Description):\nExample: Custom Plan | 100 | 50 | 30 | My custom plan")
    bot.register_next_step_handler(msg, process_admin_opt_add_plan)

def process_admin_opt_add_plan(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = [p.strip() for p in message.text.split('|')]
        if len(parts) < 3: raise ValueError("Need at least Name | Price | Bot Limit")
        name = parts[0]
        price = float(parts[1]) if parts[1] else 0
        bot_limit = int(parts[2]) if parts[2] else 0
        duration = int(parts[3]) if len(parts) > 3 and parts[3] else 0
        desc = parts[4].strip() if len(parts) > 4 else ''
        db_query("INSERT INTO plans (name, price, bot_limit, duration_days, description) VALUES (?,?,?,?,?)",
                 (name, price, bot_limit, duration, desc))
        bot.reply_to(message, f"✅ Plan '{name}' added (₹{price}, {bot_limit if bot_limit != float('inf') else '∞'} bots)")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}\nFormat: Name | Price | Bot Limit | Duration Days | Description")
        msg = bot.send_message(message.chat.id, "Enter plan details:")
        bot.register_next_step_handler(msg, process_admin_opt_add_plan)

def admin_opt_edit_plan(call):
    bot.answer_callback_query(call.id)
    plans = get_all_plans()
    text = "✏️ Edit Plan\n\n" + "\n".join(f"• ID {p[0]}: {p[1]}" for p in plans) + "\n\nEnter Plan ID:"
    bot.reply_to(message, text, parse_mode='Markdown')
    msg = bot.send_message(message.chat.id, "Enter Plan ID to edit:")
    bot.register_next_step_handler(msg, process_admin_opt_edit_plan_id)

def process_admin_opt_edit_plan_id(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        pid = int(message.text.strip())
        plan = db_fetch_one("SELECT * FROM plans WHERE plan_id = ?", (pid,))
        if not plan:
            bot.reply_to(message, f"Plan #{pid} not found.")
            return
        bot.reply_to(message, f"Editing **{plan[1]}**. Send new values (Name | Price | Bot Limit | Duration | Active| Description):")
        msg = bot.send_message(message.chat.id, "Enter new values:")
        bot.register_next_step_handler(msg, lambda m, p=pid, n=plan[1], pr=plan[2], bl=plan[3], d=plan[4], a=plan[5], df=plan[6]: process_admin_opt_edit_plan(m, p, n, pr, bl, d, a, df))
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

def process_admin_opt_edit_plan(message, pid, pname, pprice, plimit, pdur, pactive, pdesc):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = [p.strip() for p in message.text.split('|')]
        name = parts[0] if parts[0] else pname
        price = float(parts[1]) if len(parts) > 1 and parts[1] else pprice
        bot_limit = int(parts[2]) if len(parts) > 2 and parts[2] else plimit
        duration = int(parts[3]) if len(parts) > 3 and parts[3] else pdur
        active = int(parts[4]) if len(parts) > 4 and parts[4] else pactive
        desc = parts[5] if len(parts) > 5 else pdesc
        db_query("UPDATE plans SET name=?, price=?, bot_limit=?, duration_days=?, active=?, description=? WHERE plan_id=?",
                 (name, price, bot_limit, duration, active, desc, pid))
        bot.reply_to(message, f"✅ Plan #{pid} updated!")
    except Exception as e:
        bot.reply_to(message, f"Error: {e}")

def admin_opt_toggle_plan(call):
    bot.answer_callback_query(call.id)
    plans = db_fetch_all("SELECT plan_id, name, active FROM plans")
    text = "🔄 Toggle Plans:\n\n" + "\n".join(f"• ID {p[0]}: {p[1]} - {'Active' if p[2] else 'Inactive'} → /toggle_plan_{p[0]}" for p in plans)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_delete_plan(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter Plan ID to delete:")
    bot.register_next_step_handler(msg, process_admin_opt_delete_plan)

def process_admin_opt_delete_plan(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        pid = int(message.text.strip())
        db_query("DELETE FROM plans WHERE plan_id = ?", (pid,))
        bot.reply_to(message, f"✅ Plan #{pid} deleted.")
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

def admin_opt_plan_stats(call):
    bot.answer_callback_query(call.id)
    plans = get_all_plans()
    text = f"{BOT_NAME}\n\n📊 Plan Stats:\n\n"
    for p in plans:
        pid, name, price, bl, dur, active, desc = p
        uc = db_fetch_all("SELECT COUNT(*) FROM users WHERE plan = ?", (name,))[0][0]
        lim = "∞" if bl == float('inf') else str(bl)
        text += f"• **{name}**: {uc} users | {'Free' if price == 0 else f'Rs {price}'} | {lim} bots\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

# Payment admin handlers
def admin_opt_payments(call):
    bot.answer_callback_query(call.id)
    pmts = db_fetch_all("SELECT payment_id, user_id, amount, upi_ref, status, date FROM payments ORDER BY payment_id DESC LIMIT 15")
    text = f"{BOT_NAME}\n\n💰 Payments ({len(pmts)}):\n\n"
    for p in pmts:
        si = "✅" if p[4] == 'approved' else "❌" if p[4] == 'rejected' else "⏳"
        text += f"{si} #{p[0]} | User `{p[1]}` | Rs {p[2]} | {p[4]} | {p[5]}\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data='admin_opt_16'), types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_approve_payment(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter Payment ID to approve:")
    bot.register_next_step_handler(msg, process_admin_opt_approve_payment)

def process_admin_opt_approve_payment(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        pid = int(message.text.strip())
        bot.reply_to(message, approve_payment(pid, message.from_user.id))
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

def admin_opt_reject_payment(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter Payment ID to reject:")
    bot.register_next_step_handler(msg, process_admin_opt_reject_payment)

def process_admin_opt_reject_payment(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        pid = int(message.text.strip())
        bot.reply_to(message, reject_payment(pid, message.from_user.id))
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

def admin_opt_payment_stats(call):
    bot.answer_callback_query(call.id)
    t = db_fetch_all("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='approved'")[0]
    text = (f"{BOT_NAME}\n\n📊 Payment Stats:\n\n"
            f"Total Payments: {t[0] or 0}\n"
            f"Total Revenue: Rs {t[1] or 0}\n")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_set_upi(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"Current UPI: `{UPI_ID}`\n\nEnter new UPI ID:")
    bot.register_next_step_handler(msg, process_admin_opt_set_upi)

def process_admin_opt_set_upi(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    global UPI_ID
    UPI_ID = message.text.strip()
    os.environ['UPI_ID'] = UPI_ID
    bot.reply_to(message, f"✅ UPI ID updated to `{UPI_ID}`")

def admin_opt_refund(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter Payment ID to refund:")
    bot.register_next_step_handler(msg, process_admin_opt_refund)

def process_admin_opt_refund(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        pid = int(message.text.strip())
        bot.reply_to(message, refund_payment(pid))
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

# Bot management admin handlers
def admin_opt_all_bots(call):
    bot.answer_callback_query(call.id)
    all_bots = db_fetch_all("SELECT user_id, file_name, file_type, approved_date FROM approved_bots ORDER BY approved_date DESC LIMIT 25")
    text = f"{BOT_NAME}\n\n🤖 All Hosted Bots ({len(all_bots)}):\n\n"
    for b in all_bots:
        running = is_bot_running(b[0], b[1])
        si = "🟢" if running else "🔴"
        text += f"{si} `{b[1]}` ({b[2]}) by `{b[0]}` | {b[3]}\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_user_bots(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID:")
    bot.register_next_step_handler(msg, process_admin_opt_user_bots)

def process_admin_opt_user_bots(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        files = user_files.get(uid, [])
        if not files:
            bot.reply_to(message, f"User `{uid}` has no bots.")
            return
        text = f"🤖 Bots for `{uid}`:\n\n"
        for fn, ft in files:
            running = is_bot_running(uid, fn)
            st = "🟢 Running" if running else "🔴 Stopped"
            text += f"• `{fn}` ({ft}) - {st}\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
        reply_with_link(message, text, reply_markup=markup, parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

def admin_opt_kill_bot(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID and file name (user_id file_name):")
    bot.register_next_step_handler(msg, process_admin_opt_kill_bot)

def process_admin_opt_kill_bot(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.strip().split(None, 1)
        if len(parts) != 2:
            bot.reply_to(message, "Format: user_id file_name"); return
        uid = int(parts[0])
        fname = parts[1]
        sk = f"{uid}_{fname}"
        if sk in bot_scripts:
            kill_process_tree(bot_scripts[sk])
            del bot_scripts[sk]
            bot.reply_to(message, f"✅ Bot `{fname}` killed.")
        else:
            bot.reply_to(message, f"Bot `{fname}` not running.")
    except ValueError:
        bot.reply_to(message, "Invalid format.")

def admin_opt_restart_bot(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID and file name:")
    bot.register_next_step_handler(msg, process_admin_opt_restart_bot)

def process_admin_opt_restart_bot(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.strip().split(None, 1)
        if len(parts) != 2:
            bot.reply_to(message, "Format: user_id file_name"); return
        uid = int(parts[0])
        fname = parts[1]
        sk = f"{uid}_{fname}"
        user_folder = get_user_folder(uid)
        file_path = os.path.join(user_folder, fname)
        if sk in bot_scripts:
            kill_process_tree(bot_scripts[sk])
            del bot_scripts[sk]
            time.sleep(1)
        if not os.path.exists(file_path):
            bot.reply_to(message, f"File `{fname}` not found.")
            return
        ft = next((f[1] for f in user_files.get(uid, []) if f[0] == fname), 'py')
        if ft == 'py':
            threading.Thread(target=run_script, args=(file_path, uid, user_folder, fname, message)).start()
        elif ft == 'js':
            threading.Thread(target=run_js_script, args=(file_path, uid, user_folder, fname, message)).start()
        bot.reply_to(message, f"🔄 Bot `{fname}` restarting...")
    except ValueError:
        bot.reply_to(message, "Invalid format.")

def admin_opt_delete_bot(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID and file name:")
    bot.register_next_step_handler(msg, process_admin_opt_delete_bot)

def process_admin_opt_delete_bot(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.strip().split(None, 1)
        if len(parts) != 2:
            bot.reply_to(message, "Format: user_id file_name"); return
        uid = int(parts[0])
        fname = parts[1]
        user_folder = get_user_folder(uid)
        fp = os.path.join(user_folder, fname)
        lp = os.path.join(user_folder, f"{os.path.splitext(fname)[0]}.log")
        if os.path.exists(fp): os.remove(fp)
        if os.path.exists(lp): os.remove(lp)
        remove_hosted_file(uid, fname)
        bot.reply_to(message, f"✅ Bot `{fname}` deleted.")
    except ValueError:
        bot.reply_to(message, "Invalid format.")

def admin_opt_bot_logs(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID and file name:")
    bot.register_next_step_handler(msg, process_admin_opt_bot_logs)

def process_admin_opt_bot_logs(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.strip().split(None, 1)
        if len(parts) != 2:
            bot.reply_to(message, "Format: user_id file_name"); return
        uid = int(parts[0])
        fname = parts[1]
        user_folder = get_user_folder(uid)
        lf = os.path.join(user_folder, f"{os.path.splitext(fname)[0]}.log")
        if not os.path.exists(lf):
            bot.reply_to(message, f"No log for `{fname}`.")
            return
        with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        if len(content) > 3500:
            content = content[-3500:]
        bot.reply_to(message, f"📜 `{fname}` logs:\n\n```\n{content}\n```", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "Invalid format.")

# Approvals admin handlers
def admin_opt_pending(call):
    bot.answer_callback_query(call.id)
    pending = get_pending_approvals_list()
    text = f"{BOT_NAME}\n\n⏳ Pending ({len(pending)}):\n\n"
    for p in pending:
        text += f"• ID #{p[0]} | `{p[2]}` ({p[3]}) by `{p[1]}` | {p[4]}\n"
    if not pending:
        text += "No pending approvals.\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("✅ Approve All", callback_data='admin_opt_30'), types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_approve_all(call):
    bot.answer_callback_query(call.id)
    count = 0
    pending = get_pending_approvals_list()
    for p in pending:
        uid = p[1]
        fname = p[2]
        ftype = p[3]
        db_query("UPDATE pending_uploads SET status = 'approved' WHERE upload_id = ?", (p[0],))
        pending_approvals.pop(p[0], None)
        save_user_hosted_file(uid, fname, ftype)
        user_bot_counts[uid] = get_user_bot_count(uid) + 1
        try:
            bot.send_message(uid, f"✅ Your bot `{fname}` has been approved! 🎉")
            uf = get_user_folder(uid)
            fp = os.path.join(uf, fname)
            if os.path.exists(fp):
                start_hosted_bot(uid, uf, fname, ftype, call.message)
        except: pass
        count += 1
    bot.send_message(call.message.chat.id, f"✅ Approved {count} uploads.")
    back_to_main(call)

def admin_opt_approve_bot(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter Upload ID to approve (or 'all'):")
    bot.register_next_step_handler(msg, process_admin_opt_approve_bot)

def process_admin_opt_approve_bot(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    if message.text.lower() == 'all':
        count = 0
        pending = get_pending_approvals_list()
        for p in pending:
            uid = p[1]
            fname = p[2]
            ftype = p[3]
            db_query("UPDATE pending_uploads SET status = 'approved' WHERE upload_id = ?", (p[0],))
            pending_approvals.pop(p[0], None)
            save_user_hosted_file(uid, fname, ftype)
            user_bot_counts[uid] = get_user_bot_count(uid) + 1
            try:
                bot.send_message(uid, f"✅ Your bot `{fname}` has been approved! 🎉")
                uf = get_user_folder(uid)
                fp = os.path.join(uf, fname)
                if os.path.exists(fp):
                    start_hosted_bot(uid, uf, fname, ftype, message)
            except:
                pass
            count += 1
        bot.reply_to(message, f"✅ Approved {count} uploads.")
        return
    try:
        aid = int(message.text.strip())
        pending = pending_approvals.get(aid)
        if not pending or pending['status'] != 'pending':
            bot.reply_to(message, f"Upload #{aid} not found or already processed.")
            return
        uid = pending['user_id']
        fname = pending['file_name']
        ftype = pending['file_type']
        db_query("UPDATE pending_uploads SET status = 'approved' WHERE upload_id = ?", (aid,))
        pending_approvals[aid]['status'] = 'approved'
        save_user_hosted_file(uid, fname, ftype)
        user_bot_counts[uid] = get_user_bot_count(uid) + 1
        try:
            bot.send_message(uid, f"✅ Your bot `{fname}` has been approved! 🎉")
            uf = get_user_folder(uid)
            fp = os.path.join(uf, fname)
            if os.path.exists(fp):
                start_hosted_bot(uid, uf, fname, ftype, message)
        except:
            pass
        bot.reply_to(message, f"✅ Upload #{aid} approved.")
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

def admin_opt_reject_bot(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter Upload ID to reject:")
    bot.register_next_step_handler(msg, process_admin_opt_reject_bot)

def process_admin_opt_reject_bot(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        aid = int(message.text.strip())
        pending = pending_approvals.get(aid)
        if not pending or pending['status'] != 'pending':
            bot.reply_to(message, f"Upload #{aid} not found or already processed.")
            return
        uid = pending['user_id']
        fname = pending['file_name']
        db_query("UPDATE pending_uploads SET status = 'rejected' WHERE upload_id = ?", (aid,))
        pending_approvals[aid]['status'] = 'rejected'
        try:
            bot.send_message(uid, f"❌ Your bot `{fname}` was rejected by admin.")
        except:
            pass
        bot.reply_to(message, f"❌ Upload #{aid} rejected.")
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

# Referral admin handlers
def admin_opt_referrals(call):
    bot.answer_callback_query(call.id)
    refs = db_fetch_all("SELECT referral_id, referrer_id, referred_id, status, date, permanent_granted FROM referrals ORDER BY referral_id DESC LIMIT 25")
    text = f"{BOT_NAME}\n\n🔗 Referrals ({len(refs)}):\n\n"
    for r in refs:
        perm = "⭐ Permanent" if r[5] else ""
        text += f"#{r[0]}: {r[1]}→{r[2]} | {r[3]} {perm} | {r[4]}\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_referral_stats(call):
    bot.answer_callback_query(call.id)
    total = db_fetch_all("SELECT COUNT(*) FROM referrals")[0][0]
    active = db_fetch_all("SELECT COUNT(*) FROM referrals WHERE status='active'")[0][0]
    pending = db_fetch_all("SELECT COUNT(*) FROM referrals WHERE status='pending'")[0][0]
    perm = db_fetch_all("SELECT COUNT(*) FROM referrals WHERE permanent_granted=1")[0][0]
    text = (f"{BOT_NAME}\n\n📊 Referral Stats:\n\n"
            f"Total: {total}\nActive: {active}\nPending: {pending}\nPermanent: {perm}\n")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_add_referral_slot(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID to add +1 referral bonus slot:")
    bot.register_next_step_handler(msg, process_admin_opt_add_referral_slot)

def process_admin_opt_add_referral_slot(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        db_query("UPDATE users SET permanent_bonus_slots = permanent_bonus_slots + 1 WHERE user_id = ?", (uid,))
        if uid in user_plans: user_plans[uid]['permanent_bonus_slots'] = user_plans[uid].get('permanent_bonus_slots', 0) + 1
        bot.reply_to(message, f"✅ +1 permanent slot added to `{uid}`.")
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

def admin_opt_user_referrals(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID:")
    bot.register_next_step_handler(msg, process_admin_opt_user_referrals)

def process_admin_opt_user_referrals(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        uid = int(message.text.strip())
        refs = db_fetch_all("SELECT referred_id, status, permanent_granted FROM referrals WHERE referrer_id = ?", (uid,))
        text = f"🔗 Referrals for `{uid}`:\n\n"
        for r in refs:
            perm = "⭐ Permanent" if r[2] else ""
            text += f"• `{r[0]}` | {r[1]} {perm}\n"
        if not refs: text += "No referrals yet.\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
        reply_with_link(message, text, reply_markup=markup, parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "Invalid ID.")

# Broadcast admin handlers
def admin_opt_broadcast_all(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Send broadcast to all users (or /cancel):")
    bot.register_next_step_handler(msg, process_admin_opt_broadcast_all)

def process_admin_opt_broadcast_all(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    if not message.text:
        bot.reply_to(message, "Please enter a message."); return
    bc = message.text
    total = len(user_plans)
    sent = 0
    failed = 0
    for uid in list(user_plans.keys()):
        try:
            bot.send_message(uid, f"📢 Broadcast:\n\n{bc}")
            sent += 1
        except:
            failed += 1
        time.sleep(0.1)
    bot.reply_to(message, f"📢 Broadcast: Sent={sent}, Failed={failed}, Total={total}")

def admin_opt_broadcast_free(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Broadcast to free users only:")
    bot.register_next_step_handler(msg, process_admin_opt_broadcast_free)

def process_admin_opt_broadcast_free(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    bc = message.text
    sent = 0
    for uid, up in user_plans.items():
        if up.get('plan') == 'free' or not up.get('plan'):
            try:
                bot.send_message(uid, f"📢 Broadcast:\n\n{bc}")
                sent += 1
            except:
                pass
        time.sleep(0.08)
    bot.reply_to(message, f"📢 Sent to {sent} free users.")

def admin_opt_broadcast_paid(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Broadcast to paid users only:")
    bot.register_next_step_handler(msg, process_admin_opt_broadcast_paid)

def process_admin_opt_broadcast_paid(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    bc = message.text
    sent = 0
    for uid, up in user_plans.items():
        if up.get('plan') not in ('free', None, 'admin', 'owner'):
            try:
                bot.send_message(uid, f"📢 Broadcast:\n\n{bc}")
                sent += 1
            except:
                pass
        time.sleep(0.08)
    bot.reply_to(message, f"📢 Sent to {sent} paid users.")

def admin_opt_send_user(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID and message (user_id message):")
    bot.register_next_step_handler(msg, process_admin_opt_send_user)

def process_admin_opt_send_user(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.strip().split(None, 1)
        if len(parts) != 2:
            bot.reply_to(message, "Format: user_id message"); return
        uid = int(parts[0])
        msg_text = parts[1]
        bot.send_message(uid, f"📩 Admin Message:\n\n{msg_text}")
        bot.reply_to(message, f"✅ Sent to `{uid}`.")
    except ValueError:
        bot.reply_to(message, "Invalid format.")

# Edit system admin handlers
def admin_opt_edit_msg(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter message key to edit (e.g., welcome_text, upload_prompt):")
    bot.register_next_step_handler(msg, process_admin_opt_edit_msg_key)

def process_admin_opt_edit_msg_key(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    key = message.text.strip()
    existing = db_fetch_one("SELECT msg_text FROM edit_messages WHERE msg_key = ?", (key,))
    current = existing[0] if existing else "(No existing text)"
    bot.reply_to(message, f"Key: `{key}`\n\nCurrent:\n```\n{current[:300]}\n```\n\nSend new text:")
    msg2 = bot.send_message(message.chat.id, f"New text for `{key}`:")
    bot.register_next_step_handler(msg2, lambda m, k=key: process_admin_opt_edit_msg_val(m, k))

def process_admin_opt_edit_msg_val(message, key):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    db_query("INSERT OR REPLACE INTO edit_messages (msg_key, msg_text, msg_date) VALUES (?,?,?)",
             (key, message.text, datetime.now().isoformat()))
    edit_messages_store[key] = message.text
    bot.reply_to(message, f"✅ Message `{key}` updated.")

def admin_opt_view_msgs(call):
    bot.answer_callback_query(call.id)
    rows = db_fetch_all("SELECT msg_key, msg_text, msg_date FROM edit_messages ORDER BY msg_date DESC")
    text = f"{BOT_NAME}\n\n📋 Editable Messages ({len(rows)}):\n\n"
    for r in rows:
        text += f"• **{r[0]}** ({r[2]})\n  {r[1][:200]}\n\n"
    if not rows: text += "No custom messages.\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

# Settings admin handlers
def admin_opt_settings(call):
    bot.answer_callback_query(call.id)
    text = (f"{BOT_NAME}\n\n⚙️ Settings:\n\n"
            f"• UPI: `{UPI_ID}`\n"
            f"• Bot Name: {BOT_NAME}\n"
            f"• GitHub: {'✅' if github_enabled else '❌'}\n"
            f"• Locked: {'🔒' if bot_locked else '🔓'}\n"
            f"• Free Limit: {FREE_USER_LIMIT}\n"
            f"• Backup Channel: {'✅' if BACKUP_CHANNEL_ID else '❌'}\n\n"
            f"Use /set_<setting> to change.")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_lock(call):
    bot.answer_callback_query(call.id)
    global bot_locked
    bot_locked = not bot_locked
    s = "🔒 Locked" if bot_locked else "🔓 Unlocked"
    bot.reply_to(call.message, f"Bot is now {s}.")

def admin_opt_admins(call):
    bot.answer_callback_query(call.id)
    admins = db_fetch_all("SELECT user_id FROM admins")
    text = f"{BOT_NAME}\n\n👑 Admins ({len(admins)}):\n\n"
    for a in admins:
        text += f"• `{a[0]}` {'👑 Owner' if a[0] == OWNER_ID else '🛡️ Admin'}\n"
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("➕ Add Admin", callback_data='admin_add_admin_manual'), types.InlineKeyboardButton("➖ Remove", callback_data='admin_remove_admin_manual'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_stats(call):
    bot.answer_callback_query(call.id)
    tu = len(user_plans)
    tb = sum(get_user_bot_count(u) for u in user_plans)
    rc = sum(1 for k in bot_scripts if is_bot_running(int(k.split('_')[0]), bot_scripts[k]['file_name']))
    ta = db_fetch_all("SELECT COUNT(*) FROM approved_bots")[0][0]
    pc = len(get_pending_approvals_list())
    tp = db_fetch_all("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM payments WHERE status='approved'")[0]
    text = (f"{BOT_NAME}\n\n📊 Platform Stats:\n\n"
            f"👥 Users: {tu}\n"
            f"🤖 Bots: {tb}\n"
            f"🟢 Running: {rc}\n"
            f"📦 Total Uploads: {ta}\n"
            f"⏳ Pending: {pc}\n"
            f"💰 Revenue: Rs {tp[1] if tp else 0}\n")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_db_backup(call):
    bot.answer_callback_query(call.id)
    try:
        dbp = os.path.join(BASE_DIR, f'db_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        shutil.copy2(DATABASE_PATH, dbp)
        with open(dbp, 'rb') as f:
            bot.send_document(call.message.chat.id, f, caption=f"🗄️ DB Backup")
        os.remove(dbp)
        bot.reply_to(call.message, "✅ DB backup sent.")
    except Exception as e:
        bot.reply_to(call.message, f"❌ Backup failed: {e}")

def admin_opt_error_logs(call):
    bot.answer_callback_query(call.id)
    lf = os.path.join(BASE_DIR, 'bot_errors.log')
    if os.path.exists(lf):
        with open(lf, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()[-2000:]
        bot.reply_to(call.message, f"📋 Error Logs:\n\n```\n{content}\n```", parse_mode='Markdown')
    else:
        bot.reply_to(call.message, "No error logs.")

def admin_opt_github(call):
    bot.answer_callback_query(call.id)
    text = (f"{BOT_NAME}\n\n🔧 GitHub Settings:\n\n"
            f"Status: {'✅ Enabled' if github_enabled else '❌ Disabled'}\n"
            f"Token Set: {'✅' if GITHUB_TOKEN else '❌ No'}\n\n"
            f"Use /set_github_token <token>")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_backup_logs(call):
    bot.answer_callback_query(call.id)
    logs = backup_logs[-15:] if backup_logs else []
    text = f"{BOT_NAME}\n\n📋 Backup Logs ({len(logs)}):\n\n"
    for log in logs:
        text += f"• `{log.get('file_name','?')}` from `{log.get('user_id','?')}` | {log.get('backup_date','?')}\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_free_limit(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"Current free limit: {FREE_USER_LIMIT}. Enter new value:")
    bot.register_next_step_handler(msg, process_admin_opt_free_limit)

def process_admin_opt_free_limit(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    global FREE_USER_LIMIT
    try:
        FREE_USER_LIMIT = int(message.text.strip())
        db_query("UPDATE plans SET bot_limit = ? WHERE name = 'Free Plan'", (FREE_USER_LIMIT,))
        bot.reply_to(message, f"✅ Free plan limit set to {FREE_USER_LIMIT}.")
    except ValueError:
        bot.reply_to(message, "Invalid number.")

def admin_opt_view_errors(call):
    bot.answer_callback_query(call.id)
    text = f"{BOT_NAME}\n\n📋 Error Messages:\n\n"
    for eid, ein in error_area_messages.items():
        text += f"• `{eid}`: {ein['error_text'][:100]}...\n"
    if not error_area_messages:
        text += "No errors recorded.\n"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_server_health(call):
    bot.answer_callback_query(call.id)
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=1)
    disk = psutil.disk_usage('/')
    text = (f"{BOT_NAME}\n\n🖥️ Server Health:\n\n"
            f"CPU: {cpu}%\n"
            f"RAM: {mem.percent}% ({mem.used // (1024*1024)}MB / {mem.total // (1024*1024)}MB)\n"
            f"Disk: {disk.percent}% ({disk.used // (1024*1024*1024)}GB / {disk.total // (1024*1024*1024)}GB)\n"
            f"Uptime: Running\n"
            f"Users: {len(user_plans)}\n"
            f"Bots: {sum(get_user_bot_count(u) for u in user_plans)}\n"
            f"Running: {sum(1 for k in bot_scripts if k in bot_scripts)}")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_reset_stats(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "⚠️ Reset ALL user stats? (yes/no):")
    bot.register_next_step_handler(msg, process_admin_opt_reset_stats)

def process_admin_opt_reset_stats(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only."); return
    if message.text.lower() == 'yes':
        db_query("UPDATE users SET bot_count = 0, permanent_bonus_slots = 0, weekly_bonus_slots = 0, weekly_bonus_expiry = NULL")
        for uid in user_plans:
            user_plans[uid]['bot_count'] = 0
            user_plans[uid]['permanent_bonus_slots'] = 0
            user_plans[uid]['weekly_bonus_slots'] = 0
            user_plans[uid]['weekly_bonus_expiry'] = None
            user_bot_counts[uid] = 0
        bot.reply_to(message, "✅ All stats reset.")
    else:
        bot.reply_to(message, "Cancelled.")

def admin_opt_kill_all(call):
    bot.answer_callback_query(call.id)
    count = 0
    for key, info in list(bot_scripts.items()):
        kill_process_tree(info)
        del bot_scripts[key]
        count += 1
    bot.reply_to(call.message, f"✅ Killed {count} running bots.")

def admin_opt_session_info(call):
    bot.answer_callback_query(call.id)
    text = (f"{BOT_NAME}\n\n👥 Session Info:\n\n"
            f"Active Users: {len(active_users)}\n"
            f"Running Bots: {len(bot_scripts)}\n"
            f"Pending Approvals: {len(get_pending_approvals_list())}\n"
            f"Backups: {len(backup_logs)}\n"
            f"GitHub Enabled: {github_enabled}\n"
            f"Bot Locked: {bot_locked}\n"
            f"Admins: {len(admin_ids)}")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_force_ref(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter referrer_id → referred_id:")
    bot.register_next_step_handler(msg, process_admin_opt_force_ref)

def process_admin_opt_force_ref(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.strip().split('→')
        if len(parts) != 2: raise ValueError
        rid = int(parts[0].strip())
        efid = int(parts[1].strip())
        register_referral(rid, efid)
        bot.reply_to(message, f"✅ Referral registered: {rid} → {efid}")
    except:
        bot.reply_to(message, "Format: referrer_id → referred_id")
        msg = bot.send_message(message.chat.id, "Enter referrer_id → referred_id:")
        bot.register_next_step_handler(msg, process_admin_opt_force_ref)

def admin_opt_plan_comparison(call):
    bot.answer_callback_query(call.id)
    plans = get_all_plans()
    text = f"{BOT_NAME}\n\n📊 Plan Comparison:\n\n"
    headers = f"{'Plan':<15} {'Price':<8} {'Limit':<8} {'Duration':<10}\n"
    text += f"```\n{headers}{'─'*45}\n"
    for p in plans:
        pid, name, price, bl, dur, active, desc = p
        pr = "Free" if price == 0 else f"Rs {price}"
        lim = "∞" if bl == float('inf') else str(bl)
        d = f"{dur}d" if dur > 0 else "∞"
        text += f"{name:<15} {pr:<8} {lim:<8} {d:<10}\n"
    text += "```"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_payment_methods(call):
    bot.answer_callback_query(call.id)
    text = (f"{BOT_NAME}\n\n💳 Payment Methods:\n\n"
            f"• UPI ID: `{UPI_ID}`\n"
            f"• Users send payment → share UPI ref\n"
            f"• Admin approves/rejects from panel\n"
            f"• Plan activates on approval\n\n"
            f"Supported: UPI, PayTM, GPay, PhonePe")
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def admin_opt_welcome(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter new welcome text (or /cancel to abort):")
    bot.register_next_step_handler(msg, process_admin_opt_welcome)

def process_admin_opt_welcome(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    db_query("INSERT OR REPLACE INTO edit_messages (msg_key, msg_text, msg_date) VALUES (?,?,?)",
             ('welcome_text', message.text, datetime.now().isoformat()))
    edit_messages_store['welcome_text'] = message.text
    bot.reply_to(message, "✅ Welcome text updated.")

def admin_opt_max_file(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter max file size in MB (current: 20):")
    bot.register_next_step_handler(msg, process_admin_opt_max_file)

def process_admin_opt_max_file(message):
    if not is_admin(message.from_user.id): return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        mb = int(message.text.strip())
        global MAX_FILE_SIZE
        MAX_FILE_SIZE = mb * 1024 * 1024
        db_query("INSERT OR REPLACE INTO platform_settings (setting_key, setting_value) VALUES (?,?)", ('max_file_size_mb', str(mb)))
        bot.reply_to(message, f"✅ Max file size set to {mb}MB.")
    except ValueError:
        bot.reply_to(message, "Invalid number.")

def admin_opt_channel_stats(call):
    bot.answer_callback_query(call.id)
    try:
        chat = bot.get_chat(CHANNEL_ID)
        text = (f"{BOT_NAME}\n\n📢 Channel Stats:\n\n"
                f"Name: {chat.title}\n"
                f"ID: `{chat.id}`\n"
                f"Type: {chat.type}\n")
    except:
        text = f"{BOT_NAME}\n\n📢 Channel: {CHANNEL_NAME}\nID: `{CHANNEL_ID}`\n(Could not fetch stats)"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='send_admin_panel_menu'))
    edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=markup, parse_mode='Markdown')

def send_with_link(chat_id, text, reply_markup=None, parse_mode=None, reply_to_message_id=None):
    if reply_markup and isinstance(reply_markup, types.InlineKeyboardMarkup):
        nm = types.InlineKeyboardMarkup(row_width=reply_markup.row_width)
        nm.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
        for row in reply_markup.keyboard:
            nm.row(*row)
        reply_markup = nm
    elif not reply_markup:
        reply_markup = types.InlineKeyboardMarkup(row_width=1)
        reply_markup.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
    kw = {'reply_markup': reply_markup, 'parse_mode': parse_mode}
    if reply_to_message_id:
        kw['reply_to_message_id'] = reply_to_message_id
    return bot.send_message(chat_id, text, **kw)

def reply_with_link(message, text, reply_markup=None, parse_mode=None):
    return send_with_link(message.chat.id, text, reply_markup=reply_markup, parse_mode=parse_mode, reply_to_message_id=message.message_id)

def edit_with_link(chat_id, msg_id, text, reply_markup=None, parse_mode=None):
    if reply_markup and isinstance(reply_markup, types.InlineKeyboardMarkup):
        nm = types.InlineKeyboardMarkup(row_width=reply_markup.row_width)
        nm.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
        for row in reply_markup.keyboard:
            nm.row(*row)
        reply_markup = nm
    try:
        return bot.edit_message_text(text, chat_id, msg_id, reply_markup=reply_markup, parse_mode=parse_mode)
    except:
        return None

# ==================== COMMAND HANDLERS ====================
REPLY_BUTTONS = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed", "📊 Statistics"],
    ["💳 Plans", "🔗 Referrals"],
    ["📞 Contact Owner"]
]
REPLY_BUTTONS_ADMIN = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed", "📊 Statistics"],
    ["💳 Plans", "👑 Admin Panel"],
    ["🔗 Referrals", "📞 Contact Owner"]
]

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = REPLY_BUTTONS_ADMIN if user_id in admin_ids or user_id == OWNER_ID else REPLY_BUTTONS
    for row in layout:
        markup.add(*[types.KeyboardButton(text) for text in row])
    return markup

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username
    ensure_user_exists(user_id, first_name, username)
    active_users.add(user_id)
    reply_markup = create_reply_keyboard_main_menu(user_id)

    check_ch = check_channel_membership(user_id)
    if not is_user_verified(user_id):
        if check_ch:
            verify_user(user_id)
        else:
            m = types.InlineKeyboardMarkup(row_width=1)
            m.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
            m.add(types.InlineKeyboardButton("✅ I Joined - Verify", callback_data='verify_join'))
            bot.send_message(message.chat.id, "📢 Join channel to use bot!", reply_markup=m)
            return

    pi = get_user_plan_info(user_id)
    bc = get_user_bot_count(user_id)
    bl = get_user_bot_limit(user_id)
    bl_s = str(bl) if bl != float('inf') else "∞"

    if user_id == OWNER_ID:
        st = "👑 Owner"
    elif user_id in admin_ids:
        st = "🛡️ Admin"
    elif pi.get('is_paid'):
        st = f"⭐ {pi.get('plan', 'paid')}"
    else:
        st = "🆓 Free"

    send_welcome_photo(message, (
        f"{BOT_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ Welcome, {first_name}!\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"🔰 Status: {st}\n"
        f"📂 Bots: {bc} / {bl_s}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🚀 Host & run bots\n"
        f"Upload .py, .js or .zip\n\n"
        f"💳 Plans: Free(3) | 10(Rs 50) | 20(Rs 180) | ∞(Rs 350)"
    ), reply_markup=reply_markup)

def send_welcome_photo(message, text, reply_markup=None):
    if WELCOME_IMAGE_URL:
        try:
            if WELCOME_IMAGE_URL.lower().endswith('.gif'):
                try: bot.send_animation(message.chat.id, WELCOME_IMAGE_URL)
                except: bot.send_photo(message.chat.id, WELCOME_IMAGE_URL)
            else:
                bot.send_photo(message.chat.id, WELCOME_IMAGE_URL)
        except: pass
        if reply_markup:
            bot.send_message(message.chat.id, text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
    else:
        markup = reply_markup if reply_markup else types.InlineKeyboardMarkup()
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

def get_main_menu_text(user_id, first_name):
    pi = get_user_plan_info(user_id)
    bc = get_user_bot_count(user_id)
    bl = get_user_bot_limit(user_id)
    bl_s = str(bl) if bl != float('inf') else "∞"
    return (f"{BOT_NAME}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ Welcome, {first_name}!\n\n"
            f"📋 Plan: {pi.get('plan','free')}\n"
            f"🤖 Bots: {bc} / {bl_s}\n"
            f"━━━━━━━━━━━━━━━━━━")

@bot.message_handler(commands=['updateschannel'])
def cmd_updates(message):
    m = types.InlineKeyboardMarkup()
    m.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
    send_with_link(message.chat.id, f"{BOT_NAME}\n\n📢 Updates Channel", reply_markup=m)

@bot.message_handler(commands=['uploadfile'])
def cmd_upload(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        send_with_link(message.chat.id, f"{BOT_NAME}\n\n⚠️ Join channel first! Use /start")
        return
    if not can_host_bot(user_id):
        limit = get_user_bot_limit(user_id)
        count = get_user_bot_count(user_id)
        send_with_link(message.chat.id, f"{BOT_NAME}\n\n⚠️ Bot limit reached ({count}/{limit if limit != float('inf') else '∞'})")
        return
    send_with_link(message.chat.id, (
        f"{BOT_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📤 Send your file:\n"
        f"• .py (Python)\n"
        f"• .js (Node.js)\n"
        f"• .zip (Archive)\n"
        f"• GitHub repo URL\n"
        f"━━━━━━━━━━━━━━━━━━"))

@bot.message_handler(commands=['mybots', 'checkfiles'])
def cmd_check_files(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        send_with_link(message.chat.id, f"{BOT_NAME}\n\n⚠️ Join channel first! Use /start")
        return
    bf = user_files.get(user_id, [])
    if not bf:
        send_with_link(message.chat.id, f"{BOT_NAME}\n\n📂 No files uploaded yet.")
        return
    mk = types.InlineKeyboardMarkup(row_width=1)
    for fn, ft in sorted(bf):
        running = is_bot_running(user_id, fn)
        si = "🟢" if running else "🔴"
        mk.add(types.InlineKeyboardButton(f"{si} {fn} ({ft})", callback_data=f'file_{user_id}_{fn}'))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    send_with_link(message.chat.id, f"{BOT_NAME}\n\n📂 Your Files:", reply_markup=mk)

@bot.message_handler(commands=['botspeed', 'speed'])
def cmd_speed(message):
    user_id = message.from_user.id
    start_time = time.time()
    wait_msg = bot.reply_to(message, f"{BOT_NAME}\n\n⚡ Testing...")
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        rt = round((time.time() - start_time) * 1000, 2)
        pi = get_user_plan_info(user_id)
        if user_id == OWNER_ID: st = "👑 Owner"
        elif user_id in admin_ids: st = "🛡️ Admin"
        elif pi.get('is_paid'): st = f"⭐ {pi.get('plan', 'paid')}"
        else: st = "🆓 Free"
        edit_with_link(message.chat.id, wait_msg.message_id, (
            f"{BOT_NAME}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Speed & Status\n\n"
            f"⏱️ Response: {rt} ms\n"
            f"👤 Level: {st}\n"
            f"━━━━━━━━━━━━━━━━━━"), parse_mode='Markdown')
    except:
        bot.edit_message_text("❌ Error.", message.chat.id, wait_msg.message_id)

@bot.message_handler(commands=['stats', 'status'])
def cmd_stats(message):
    user_id = message.from_user.id
    tu = len(user_plans)
    tb = sum(get_user_bot_count(u) for u in user_plans)
    rc = sum(1 for k in bot_scripts if is_bot_running(int(k.split('_')[0]), bot_scripts[k]['file_name']))
    uc = get_user_bot_count(user_id)
    text = (f"{BOT_NAME}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📊 Statistics\n\n"
            f"👥 Total Users: {tu}\n"
            f"🤖 Total Bots: {tb}\n"
            f"🟢 Running: {rc}\n"
            f"🤖 Your Bots: {uc}\n"
            f"━━━━━━━━━━━━━━━━━━")
    send_with_link(message.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['plans'])
def cmd_plans(message):
    mk = types.InlineKeyboardMarkup(row_width=1)
    for p in get_all_plans():
        pid, name, price, bl, dur, active, desc = p
        if not active: continue
        pr = "FREE" if price == 0 else f"Rs {price}"
        lim = "∞" if bl == float('inf') else str(bl)
        mk.add(types.InlineKeyboardButton(f"{name}: {pr} | {lim} bots | {dur}days", callback_data=f'buy_plan_{pid}'))
    mk.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    send_with_link(message.chat.id, f"{BOT_NAME}\n\n💳 Available Plans:", reply_markup=mk, parse_mode='Markdown')

@bot.message_handler(commands=['referrals', 'referral'])
def cmd_referrals(message):
    user_id = message.from_user.id
    rc = get_user_referral_count(user_id)
    up = user_plans.get(user_id, {})
    can_weekly = can_give_weekly_bonus(user_id)
    text = (f"{BOT_NAME}\n\n"
            f"🔗 Referral Program\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 Your referrals: {rc}\n"
            f"🎁 Invite 10 → +1 bot for 1 week\n"
            f"🎁 Referral stays active → +1 permanent slot\n\n"
            f"📋 Your referral link:\n{MAIN_LINK_URL}?ref={user_id}\n"
            f"━━━━━━━━━━━━━━━━━━")
    if can_weekly:
        text += "\n🎉 You can claim weekly bonus!"
    send_with_link(message.chat.id, text)

@bot.message_handler(commands=['adminpanel'])
def cmd_admin_panel(message):
    if not is_admin(message.from_user.id):
        send_with_link(message.chat.id, f"{BOT_NAME}\n\n⚠️ Admin permissions required.")
        return
    send_admin_panel_menu(message)

@bot.message_handler(commands=['verify'])
def cmd_verify(message):
    user_id = message.from_user.id
    verify_user(user_id)
    bot.reply_to(message, "✅ Verified! Use /start to continue.")

@bot.message_handler(commands=['set_github_token'])
def cmd_set_github(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        token = message.text.split(None, 1)[1]
        os.environ['GITHUB_TOKEN'] = token
        global GITHUB_TOKEN, github_enabled
        GITHUB_TOKEN = token
        github_enabled = True
        bot.reply_to(message, f"✅ GitHub token set.")
    except:
        bot.reply_to(message, "Usage: /set_github_token <token>")

@bot.message_handler(commands=['set_upi'])
def cmd_set_upi(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        upi = message.text.split(None, 1)[1]
        global UPI_ID
        UPI_ID = upi
        os.environ['UPI_ID'] = upi
        bot.reply_to(message, f"✅ UPI ID updated to `{UPI_ID}`")
    except:
        bot.reply_to(message, "Usage: /set_upi <upi_id>")

@bot.message_handler(commands=['set_free_limit'])
def cmd_set_free_limit(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        lim = int(message.text.split(None, 1)[1])
        global FREE_USER_LIMIT
        FREE_USER_LIMIT = lim
        db_query("UPDATE plans SET bot_limit = ? WHERE name = 'Free Plan'", (lim,))
        bot.reply_to(message, f"✅ Free plan limit set to {lim}.")
    except:
        bot.reply_to(message, "Usage: /set_free_limit <number>")

@bot.message_handler(commands=['set_lock'])
def cmd_set_lock(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    global bot_locked
    bot_locked = not bot_locked
    bot.reply_to(message, f"Bot is now {'🔒 Locked' if bot_locked else '🔓 Unlocked'}.")

@bot.message_handler(commands=['set_admin'])
def cmd_set_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        new_id = int(message.text.split(None, 1)[1])
        if new_id in admin_ids:
            bot.reply_to(message, f"Already Admin.")
            return
        db_query("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,))
        admin_ids.add(new_id)
        bot.reply_to(message, f"✅ User `{new_id}` is now Admin.")
        try: bot.send_message(new_id, "You are now an Admin.")
        except: pass
    except:
        bot.reply_to(message, "Usage: /set_admin <user_id>")

@bot.message_handler(commands=['set_remove_admin'])
def cmd_remove_admin(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        rid = int(message.text.split(None, 1)[1])
        if rid == OWNER_ID:
            bot.reply_to(message, "Cannot remove owner.")
            return
        db_query("DELETE FROM admins WHERE user_id = ?", (rid,))
        admin_ids.discard(rid)
        bot.reply_to(message, f"✅ Admin `{rid}` removed.")
    except:
        bot.reply_to(message, "Usage: /set_remove_admin <user_id>")

@bot.message_handler(commands=['set_channel'])
def cmd_set_channel(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        cid = int(message.text.split(None, 1)[1])
        global CHANNEL_ID
        CHANNEL_ID = cid
        bot.reply_to(message, f"✅ Channel ID set to `{cid}`")
    except:
        bot.reply_to(message, "Usage: /set_channel <channel_id>")

@bot.message_handler(commands=['set_channel_link'])
def cmd_set_channel_link(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        link = message.text.split(None, 1)[1]
        global CHANNEL_LINK
        CHANNEL_LINK = link
        bot.reply_to(message, f"✅ Channel link set.")
    except:
        bot.reply_to(message, "Usage: /set_channel_link <link>")

@bot.message_handler(commands=['set_main_link'])
def cmd_set_main_link(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "Owner only.")
        return
    try:
        link = message.text.split(None, 1)[1]
        global MAIN_LINK_URL
        MAIN_LINK_URL = link
        bot.reply_to(message, f"✅ Main link set.")
    except:
        bot.reply_to(message, "Usage: /set_main_link <url>")

@bot.message_handler(commands=['ping'])
def cmd_ping(message):
    start = time.time()
    msg = bot.reply_to(message, "Pong!")
    lat = round((time.time() - start) * 1000, 2)
    bot.edit_message_text(f"Pong! Latency: {lat} ms", message.chat.id, msg.message_id)

# ==================== CALLBACK ROUTER ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    if data == 'verify_join':
        if check_channel_membership(user_id):
            verify_user(user_id)
            bot.answer_callback_query(call.id, "Verified!")
            bot.edit_message_text("Welcome! Channel verified.\n\nUse /start to continue.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "Join the channel first!", show_alert=True)
        return

    if data == 'back_to_main':
        back_to_main(call)
        return

    if data == 'admin_panel' and is_admin(user_id):
        bot.answer_callback_query(call.id)
        send_admin_panel_menu(call)
        return

    if data == 'send_admin_panel_menu' and is_admin(user_id):
        bot.answer_callback_query(call.id)
        send_admin_panel_menu(call)
        return

    if data.startswith('admin_page_') and is_admin(user_id):
        bot.answer_callback_query(call.id)
        page = int(data.replace('admin_page_', ''))
        send_admin_panel_menu(call, page=page)
        return

    if data == 'referrals':
        bot.answer_callback_query(call.id)
        cmd_referrals(call.message)
        return

    if data == 'plans':
        bot.answer_callback_query(call.id)
        cmd_plans(call.message)
        return

    if data == 'contact_owner' or data == 'contact_owner1' or data == 'contact_owner2':
        bot.answer_callback_query(call.id)
        m = types.InlineKeyboardMarkup(row_width=2)
        m.row(types.InlineKeyboardButton(f"🔴 {YOUR_USERNAME}", url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'),
              types.InlineKeyboardButton(f"🔵 {YOUR_USERNAME_2}", url=f'https://t.me/{YOUR_USERNAME_2.replace("@", "")}'))
        send_with_link(call.message.chat.id, f"{BOT_NAME}\n\n📞 Contact Owners", reply_markup=m)
        return

    if data == 'speed':
        bot.answer_callback_query(call.id)
        cmd_speed(call.message)
        return

    if data == 'stats':
        bot.answer_callback_query(call.id)
        cmd_stats(call.message)
        return

    if data == 'upload':
        bot.answer_callback_query(call.id)
        cmd_upload(call.message)
        return

    if data == 'check_files':
        bot.answer_callback_query(call.id)
        cmd_check_files(call.message)
        return

    if data.startswith('admin_opt_'):
        opt = data.replace('admin_opt_', '')
        handler_map = {
            '1': admin_opt_users, '2': admin_opt_user_details, '3': admin_opt_search_user,
            '4': admin_opt_ban, '5': admin_opt_unban, '6': admin_opt_delete_user,
            '7': admin_opt_bot_count, '8': admin_opt_export,
            '9': admin_opt_plans, '10': admin_opt_add_plan, '11': admin_opt_edit_plan,
            '12': admin_opt_toggle_plan, '13': admin_opt_delete_plan, '14': admin_opt_plan_stats,
            '15': admin_opt_payments, '16': admin_opt_approve_payment, '17': admin_opt_reject_payment,
            '18': admin_opt_payment_stats, '19': admin_opt_set_upi, '20': admin_opt_refund,
            '21': admin_opt_all_bots, '22': admin_opt_user_bots, '23': admin_opt_kill_bot,
            '24': admin_opt_restart_bot, '25': admin_opt_delete_bot, '26': admin_opt_bot_logs,
            '27': admin_opt_pending, '28': admin_opt_approve_bot, '29': admin_opt_reject_bot,
            '30': admin_opt_approve_all, '31': admin_opt_referrals, '32': admin_opt_referral_stats,
            '33': admin_opt_add_referral_slot, '34': admin_opt_user_referrals,
            '35': admin_opt_broadcast_all, '36': admin_opt_broadcast_free, '37': admin_opt_broadcast_paid,
            '38': admin_opt_send_user, '39': admin_opt_edit_msg, '40': admin_opt_view_msgs,
            '41': admin_opt_settings, '42': admin_opt_lock, '43': admin_opt_admins,
            '44': admin_opt_stats, '45': admin_opt_db_backup, '46': admin_opt_error_logs,
            '47': admin_opt_github, '48': admin_opt_backup_logs, '49': admin_opt_free_limit,
            '50': admin_opt_view_errors, '51': admin_opt_server_health, '52': admin_opt_reset_stats,
            '53': admin_opt_kill_all, '54': admin_opt_session_info, '55': admin_opt_force_ref,
            '56': admin_opt_plan_comparison, '57': admin_opt_payment_methods, '58': admin_opt_welcome,
            '59': admin_opt_max_file, '60': admin_opt_channel_stats,
        }
        handler = handler_map.get(opt)
        if handler:
            handler(call)
        else:
            bot.answer_callback_query(call.id, "Option not found.")
        return

    if data.startswith('approve_up_'):
        bot.answer_callback_query(call.id)
        parts = data.split('_', 3)
        uid = int(parts[2])
        fname = parts[3]
        ftype = parts[4] if len(parts) > 4 else 'py'
        db_query("INSERT INTO pending_uploads (user_id, file_name, file_type, upload_date, status) VALUES (?,?,?,?,?)",
                 (uid, fname, ftype, datetime.now().isoformat(), 'approved'))
        save_user_hosted_file(uid, fname, ftype)
        user_bot_counts[uid] = get_user_bot_count(uid) + 1
        try: bot.send_message(uid, f"✅ Your bot `{fname}` approved! 🎉")
        except: pass
        uf = get_user_folder(uid)
        fp = os.path.join(uf, fname)
        if os.path.exists(fp):
            start_hosted_bot(uid, uf, fname, ftype, call.message)
        elif str(call.message.chat.id) == str(uid):
            bot.edit_message_text(f"✅ Bot `{fname}` approved!", call.message.chat.id, call.message.message_id)
        return

    if data.startswith('reject_up_'):
        bot.answer_callback_query(call.id)
        parts = data.split('_', 3)
        uid = int(parts[2])
        fname = parts[3]
        ftype = parts[4] if len(parts) > 4 else 'py'
        db_query("INSERT INTO pending_uploads (user_id, file_name, file_type, upload_date, status) VALUES (?,?,?,?,?)",
                 (uid, fname, ftype, datetime.now().isoformat(), 'rejected'))
        try: bot.send_message(uid, f"❌ Bot `{fname}` rejected.")
        except: pass
        bot.edit_message_text(f"❌ Bot `{fname}` rejected.", call.message.chat.id, call.message.message_id)
        return

    if data.startswith('approve_buy_plan_'):
        bot.answer_callback_query(call.id)
        pid = int(data.replace('approve_buy_plan_', ''))
        process_plan_purchase(call, pid)
        return

    if data.startswith('copy_error_'):
        eid = data.replace('copy_error_', '')
        bot.answer_callback_query(call.id, "Error text copied!", show_alert=True)
        return

    if data.startswith('admin_ban_'):
        uid = int(data.replace('admin_ban_', ''))
        db_query("UPDATE users SET is_banned = 1 WHERE user_id = ?", (uid,))
        if uid in user_plans: user_plans[uid]['is_banned'] = 1
        bot.answer_callback_query(call.id, f"User {uid} banned.")
        back_to_main(call)
        return

    if data.startswith('admin_unban_'):
        uid = int(data.replace('admin_unban_', ''))
        db_query("UPDATE users SET is_banned = 0 WHERE user_id = ?", (uid,))
        if uid in user_plans: user_plans[uid]['is_banned'] = 0
        bot.answer_callback_query(call.id, f"User {uid} unbanned.")
        back_to_main(call)
        return

    if data.startswith('admin_deluser_'):
        uid = int(data.replace('admin_deluser_', ''))
        for key, info in list(bot_scripts.items()):
            if str(info.get('script_owner_id')) == str(uid):
                kill_process_tree(info)
                del bot_scripts[key]
        user_folder = get_user_folder(uid)
        if os.path.exists(user_folder): shutil.rmtree(user_folder)
        db_query("DELETE FROM users WHERE user_id = ?", (uid,))
        user_plans.pop(uid, None)
        user_files.pop(uid, None)
        user_bot_counts.pop(uid, None)
        bot.answer_callback_query(call.id, f"User {uid} deleted.")
        back_to_main(call)
        return

    if data.startswith('admin_files_'):
        uid = int(data.replace('admin_files_', ''))
        files = user_files.get(uid, [])
        text = f"📂 Files for `{uid}`:\n\n"
        for fn, ft in files:
            running = is_bot_running(uid, fn)
            st = "🟢" if running else "🔴"
            text += f"{st} `{fn}` ({ft})\n"
        if not files: text += "No files.\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='admin_panel'))
        send_with_link(call.message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
        return

    if data.startswith('buy_plan_'):
        bot.answer_callback_query(call.id)
        pid = int(data.replace('buy_plan_', ''))
        process_plan_purchase(call, pid)
        return

    bot.answer_callback_query(call.id, "Action processed.")

def back_to_main(call):
    user_id = call.from_user.id
    if user_id == OWNER_ID: st = "👑 Owner"
    elif user_id in admin_ids: st = "🛡️ Admin"
    else: st = "🆓 Free"
    bc = get_user_bot_count(user_id)
    bl = get_user_bot_limit(user_id)
    bl_s = str(bl) if bl != float('inf') else "∞"
    text = (f"{BOT_NAME}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"✨ Welcome, {call.from_user.first_name}!\n\n"
            f"🆔 User ID: `{user_id}`\n"
            f"🔰 Status: {st}\n"
            f"📂 Bots: {bc} / {bl_s}\n"
            f"━━━━━━━━━━━━━━━━━━")
    try:
        bot.answer_callback_query(call.id)
        edit_with_link(call.message.chat.id, call.message.message_id, text, reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except:
        pass

# ==================== FILE UPLOAD HANDLER ====================
@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        bot.reply_to(message, "⚠️ Join channel first! Use /start")
        return
    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "🔒 Bot locked.")
        return
    if not can_host_bot(user_id):
        limit = get_user_bot_limit(user_id)
        count = get_user_bot_count(user_id)
        bot.reply_to(message, f"⚠️ Bot limit reached ({count}/{limit if limit != float('inf') else '∞'}). Delete files first or upgrade plan.")
        return

    doc = message.document
    file_name = doc.file_name
    if not file_name:
        bot.reply_to(message, "No file name.")
        return
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, "Only .py, .js, and .zip files allowed.")
        return
    max_size = 50 * 1024 * 1024
    if doc.file_size > max_size:
        bot.reply_to(message, f"File too large (Max: {max_size // 1024 // 1024} MB).")
        return

    try:
        download_wait = bot.reply_to(message, f"📥 Downloading `{file_name}`...")
        file_info = bot.get_file(doc.file_id)
        content = bot.download_file(file_info.file_path)
        bot.edit_message_text(f"⏳ Processing `{file_name}`...", message.chat.id, download_wait.message_id)

        user_folder = get_user_folder(user_id)

        if file_ext == '.zip':
            handle_zip_upload(content, file_name, message)
        elif file_ext == '.py':
            fp = os.path.join(user_folder, file_name)
            with open(fp, 'wb') as f: f.write(content)
            save_user_hosted_file(user_id, file_name, 'py')
            user_bot_counts[user_id] = get_user_bot_count(user_id) + 1
            backup_user_upload(user_id, file_name, 'py', {'source': 'direct'}, fp)
            pi = get_user_plan_info(user_id)
            if pi.get('is_free') and user_id != OWNER_ID and user_id not in admin_ids:
                upload_id = int(time.time())
                db_query("INSERT INTO pending_uploads (user_id, file_name, file_type, upload_date, status) VALUES (?,?,?,?,?)",
                         (user_id, file_name, 'py', datetime.now().isoformat(), 'pending'))
                pending_approvals[upload_id] = {'user_id': user_id, 'file_name': file_name, 'file_type': 'py', 'upload_date': datetime.now().isoformat(), 'status': 'pending'}
                notify_admin_new_upload(user_id, file_name, 'py')
                bot.reply_to(message, f"📤 Bot received!\n\n`{file_name}` pending admin approval.")
            else:
                start_hosted_bot(user_id, user_folder, file_name, 'py', message)
        elif file_ext == '.js':
            fp = os.path.join(user_folder, file_name)
            with open(fp, 'wb') as f: f.write(content)
            save_user_hosted_file(user_id, file_name, 'js')
            user_bot_counts[user_id] = get_user_bot_count(user_id) + 1
            backup_user_upload(user_id, file_name, 'js', {'source': 'direct'}, fp)
            pi = get_user_plan_info(user_id)
            if pi.get('is_free') and user_id != OWNER_ID and user_id not in admin_ids:
                upload_id = int(time.time())
                db_query("INSERT INTO pending_uploads (user_id, file_name, file_type, upload_date, status) VALUES (?,?,?,?,?)",
                         (user_id, file_name, 'js', datetime.now().isoformat(), 'pending'))
                pending_approvals[upload_id] = {'user_id': user_id, 'file_name': file_name, 'file_type': 'js', 'upload_date': datetime.now().isoformat(), 'status': 'pending'}
                notify_admin_new_upload(user_id, file_name, 'js')
                bot.reply_to(message, f"📤 Bot received!\n\n`{file_name}` pending admin approval.")
            else:
                start_hosted_bot(user_id, user_folder, file_name, 'js', message)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ==================== TEXT MESSAGE HANDLER ====================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    text = message.text.strip()

    # GitHub URL detection
    if text.startswith('http://github.com') or text.startswith('https://github.com'):
        handle_github_repo(text, message)
        return

    # Command buttons text matching
    if text == "📢 Updates Channel":
        cmd_updates(message)
    elif text == "📤 Upload File":
        cmd_upload(message)
    elif text == "📂 Check Files" or text == "📂 My Files":
        cmd_check_files(message)
    elif text == "⚡ Bot Speed" or text == "⚡ Speed":
        cmd_speed(message)
    elif text == "📊 Statistics" or text == "📊 Stats":
        cmd_stats(message)
    elif text == "💳 Plans" or text == "💳 Subscriptions":
        cmd_plans(message)
    elif text == "📞 Contact Owner" or text == "📞 Contact":
        cmd_referrals(message)
    elif text == "🔗 Referrals" or text == "🔗 Referral Program":
        cmd_referrals(message)
    elif text == "👑 Admin Panel":
        cmd_admin_panel(message)
    elif text == "📞 Contact Owner":
        m = types.InlineKeyboardMarkup(row_width=2)
        m.row(types.InlineKeyboardButton(f"🔴 {YOUR_USERNAME}", url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'),
              types.InlineKeyboardButton(f"🔵 {YOUR_USERNAME_2}", url=f'https://t.me/{YOUR_USERNAME_2.replace("@", "")}'))
        send_with_link(message.chat.id, f"{BOT_NAME}\n\n📞 Contact Owners", reply_markup=m)
    else:
        # Check if it's a UPI reference for payment verification
        if text.startswith('/verify_payment') or text.startswith('upi_') or (len(text) > 5 and 'spider' in text.lower()):
            bot.reply_to(message, "If you've made a payment, an admin will review it shortly.")
            return
        bot.reply_to(message, f"{BOT_NAME}\n\nUse /start to get started, /upload to host a bot, or /plans to see plans.")

# ==================== PROCESS CLEANUP ====================
def cleanup():
    logger.warning("Shutting down. Cleaning up processes...")
    for key in list(bot_scripts.keys()):
        kill_process_tree(bot_scripts[key])
atexit.register(cleanup)

# ==================== MAIN ====================
if __name__ == '__main__':
    keep_alive()
    logger.info("=" * 40)
    logger.info(f"Bot Starting: {BOT_NAME}")
    logger.info(f"Owner: {OWNER_ID}")
    logger.info(f"Users: {len(user_plans)}")
    logger.info(f"GitHub Enabled: {github_enabled}")
    logger.info(f"Payment UPI: {UPI_ID}")
    logger.info("=" * 40)
    while True:
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout:
            time.sleep(5)
        except requests.exceptions.ConnectionError:
            time.sleep(15)
        except Exception as e:
            logger.critical(f"Polling error: {e}", exc_info=True)
            time.sleep(30)
        finally:
            time.sleep(1)
