# -*- coding: utf-8 -*-
import telebot
import subprocess
import os
import zipfile
import tempfile
import shutil
from telebot import types
import time
from datetime import datetime, timedelta
import psutil
import sqlite3
import json
import logging
import signal
import threading
import re
import sys
import atexit
import requests

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'am Yash File Host"

def run_flask():
  port = int(os.environ.get("PORT", 8080))
  app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    print("Flask Keep-Alive server started.")

# --- Configuration from ENV ---
BOT_NAME = os.environ.get("BOT_NAME", "🕷️ 𝐒𝐩𝐢𝐝𝐞𝐫 𝐇𝐨𝐬𝐭")
TOKEN = os.environ.get("BOT_TOKEN", "8135674571:AAH60RNMkiG4cMkvoFJVxSCYfe-DE2lwjtE")
OWNER_ID = int(os.environ.get("OWNER_ID", "6650888707"))
OWNER_ID_2 = int(os.environ.get("OWNER_ID_2", "8994613565"))  # Second owner ID
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6650888707"))
YOUR_USERNAME = os.environ.get("YOUR_USERNAME", "@TylerDurden21")
YOUR_USERNAME_2 = os.environ.get("YOUR_USERNAME_2", "@SegsyToxic95")  # Second owner username

# Channel settings
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "-1004412468420"))
CHANNEL_NAME = os.environ.get("CHANNEL_NAME", "🕷️ Spider Host Official")
CHANNEL_LINK = os.environ.get("CHANNEL_LINK", "https://t.me/ToxicCodeVerse")

# Welcome image (ONLY on /start welcome)
WELCOME_IMAGE_URL = os.environ.get("WELCOME_IMAGE_URL", "https://cdn.phototourl.com/free/2026-07-15-b653e649-55d7-42e9-8afc-2206ba69ac61.gif")

# Main link button
MAIN_LINK_URL = os.environ.get("MAIN_LINK_URL", "https://t.me/ToxicCodeVerse")
MAIN_LINK_TEXT = os.environ.get("MAIN_LINK_TEXT", "🔗 Join Channel")

# Folder setup
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_BOTS_DIR = os.path.join(BASE_DIR, 'upload_bots')
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

FREE_USER_LIMIT = 10
SUBSCRIBED_USER_LIMIT = 20
ADMIN_LIMIT = 99
OWNER_LIMIT = float('inf')

os.makedirs(UPLOAD_BOTS_DIR, exist_ok=True)
os.makedirs(IROTECH_DIR, exist_ok=True)

bot = telebot.TeleBot(TOKEN)

# --- Data structures ---
bot_scripts = {}
user_subscriptions = {}
user_files = {}
active_users = set()
admin_ids = {ADMIN_ID, OWNER_ID}
bot_locked = False

# Users who have verified channel join
verified_users = set()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Reply Keyboard Layouts ---
COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed", "📊 Statistics"],
    ["📞 Contact Owner"]
]
ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC = [
    ["📢 Updates Channel"],
    ["📤 Upload File", "📂 Check Files"],
    ["⚡ Bot Speed", "📊 Statistics"],
    ["💳 Subscriptions", "📢 Broadcast"],
    ["🔒 Lock Bot", "🟢 Running All Code"],
    ["👑 Admin Panel", "📞 Contact Owner"]
]

# --- Database Setup ---
def init_db():
    logger.info(f"Initializing database at: {DATABASE_PATH}")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                     (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_files
                     (user_id INTEGER, file_name TEXT, file_type TEXT,
                      PRIMARY KEY (user_id, file_name))''')
        c.execute('''CREATE TABLE IF NOT EXISTS active_users
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS admins
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS verified_users
                     (user_id INTEGER PRIMARY KEY)''')
        c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (OWNER_ID,))
        if ADMIN_ID != OWNER_ID:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (ADMIN_ID,))
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)

def load_data():
    logger.info("Loading data from database...")
    try:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT user_id, expiry FROM subscriptions')
        for user_id, expiry in c.fetchall():
            try:
                user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
            except ValueError:
                pass
        c.execute('SELECT user_id, file_name, file_type FROM user_files')
        for user_id, file_name, file_type in c.fetchall():
            if user_id not in user_files:
                user_files[user_id] = []
            user_files[user_id].append((file_name, file_type))
        c.execute('SELECT user_id FROM active_users')
        active_users.update(user_id for (user_id,) in c.fetchall())
        c.execute('SELECT user_id FROM admins')
        admin_ids.update(user_id for (user_id,) in c.fetchall())
        # Load verified users
        c.execute('SELECT user_id FROM verified_users')
        verified_users.update(user_id for (user_id,) in c.fetchall())
        conn.close()
        logger.info(f"Data loaded: {len(active_users)} users, {len(user_subscriptions)} subscriptions, {len(admin_ids)} admins, {len(verified_users)} verified.")
    except Exception as e:
        logger.error(f"Error loading data: {e}", exc_info=True)

init_db()
load_data()

# --- Channel Verification ---
def is_user_verified(user_id):
    """Check if user has verified channel join"""
    if user_id in admin_ids or user_id == OWNER_ID:
        return True
    return user_id in verified_users

def check_channel_membership(user_id):
    """Check if user is member of the channel. Bot must be admin."""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        status = member.status
        # left, kicked = not member; creator, administrator, member = member
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking channel membership for {user_id}: {e}")
        return False

def verify_user(user_id):
    """Mark user as verified in DB and memory"""
    if user_id not in verified_users:
        verified_users.add(user_id)
        try:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO verified_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error saving verified user {user_id}: {e}")

def create_join_channel_markup():
    """Create inline keyboard for channel join"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"📢 Join {CHANNEL_NAME}", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("✅ I've Joined - Verify", callback_data='verify_join'))
    return markup

def add_main_link_button(markup):
    """Add main link button at the TOP of any inline keyboard"""
    if not isinstance(markup, types.InlineKeyboardMarkup):
        markup = types.InlineKeyboardMarkup(row_width=1)
    link_btn = types.InlineKeyboardButton(MAIN_LINK_TEXT, url=MAIN_LINK_URL)
    # Create new markup with link button first, then existing buttons
    new_markup = types.InlineKeyboardMarkup(row_width=markup.row_width)
    new_markup.add(link_btn)
    # Copy existing rows
    for row in markup.keyboard:
        new_markup.row(*row)
    return new_markup

def send_welcome_with_photo(chat_id, text, reply_markup=None, parse_mode=None):
    """Send welcome message WITH photo/GIF (only for /start)"""
    if WELCOME_IMAGE_URL:
        try:
            # Try GIF/Animation first (for .gif URLs)
            if WELCOME_IMAGE_URL.lower().endswith('.gif'):
                try:
                    bot.send_animation(chat_id, WELCOME_IMAGE_URL)
                except:
                    # Fallback to send_photo if animation fails
                    bot.send_photo(chat_id, WELCOME_IMAGE_URL)
            else:
                # Regular photo
                bot.send_photo(chat_id, WELCOME_IMAGE_URL)
        except Exception as e:
            logger.warning(f"Failed to send welcome image: {e}")
            # Try sending as document if photo fails
            try:
                bot.send_document(chat_id, WELCOME_IMAGE_URL)
            except:
                pass
    # Send text message with reply markup
    return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

def send_message_with_link(chat_id, text, reply_markup=None, parse_mode=None, reply_to_message_id=None):
    """Send message with channel link at top (NO photo)"""
    # Add channel link button at top
    if reply_markup and isinstance(reply_markup, types.InlineKeyboardMarkup):
        # Create new markup with channel link first
        new_markup = types.InlineKeyboardMarkup(row_width=reply_markup.row_width)
        new_markup.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
        for row in reply_markup.keyboard:
            new_markup.row(*row)
        reply_markup = new_markup
    elif not reply_markup:
        reply_markup = types.InlineKeyboardMarkup(row_width=1)
        reply_markup.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
    
    if reply_to_message_id:
        return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, reply_to_message_id=reply_to_message_id)
    else:
        return bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

def send_reply_with_link(message, text, reply_markup=None, parse_mode=None):
    """Reply to a message with channel link (NO photo)"""
    return send_message_with_link(message.chat.id, text, reply_markup=reply_markup, parse_mode=parse_mode, reply_to_message_id=message.message_id)

def edit_with_link_button(chat_id, message_id, text, reply_markup=None, parse_mode=None):
    """Edit message and add channel link at top"""
    if reply_markup and isinstance(reply_markup, types.InlineKeyboardMarkup):
        new_markup = types.InlineKeyboardMarkup(row_width=reply_markup.row_width)
        new_markup.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
        for row in reply_markup.keyboard:
            new_markup.row(*row)
        reply_markup = new_markup
    elif not reply_markup:
        reply_markup = types.InlineKeyboardMarkup(row_width=1)
        reply_markup.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
    return bot.edit_message_text(text, chat_id, message_id, reply_markup=reply_markup, parse_mode=parse_mode)

# --- Helper Functions ---
def get_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_BOTS_DIR, str(user_id))
    os.makedirs(user_folder, exist_ok=True)
    return user_folder

def get_user_file_limit(user_id):
    if user_id == OWNER_ID: return OWNER_LIMIT
    if user_id in admin_ids: return ADMIN_LIMIT
    if user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now():
        return SUBSCRIBED_USER_LIMIT
    return FREE_USER_LIMIT

def get_user_file_count(user_id):
    return len(user_files.get(user_id, []))

def is_bot_running(script_owner_id, file_name):
    script_key = f"{script_owner_id}_{file_name}"
    script_info = bot_scripts.get(script_key)
    if script_info and script_info.get('process'):
        try:
            proc = psutil.Process(script_info['process'].pid)
            is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
            if not is_running:
                if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                    try: script_info['log_file'].close()
                    except: pass
                if script_key in bot_scripts: del bot_scripts[script_key]
            return is_running
        except psutil.NoSuchProcess:
            if 'log_file' in script_info and hasattr(script_info['log_file'], 'close') and not script_info['log_file'].closed:
                try: script_info['log_file'].close()
                except: pass
            if script_key in bot_scripts: del bot_scripts[script_key]
            return False
        except Exception as e:
            logger.error(f"Error checking process for {script_key}: {e}", exc_info=True)
            return False
    return False

def kill_process_tree(process_info):
    pid = None
    script_key = process_info.get('script_key', 'N/A')
    try:
        if 'log_file' in process_info and hasattr(process_info['log_file'], 'close') and not process_info['log_file'].closed:
            try: process_info['log_file'].close()
            except: pass
        process = process_info.get('process')
        if process and hasattr(process, 'pid'):
            pid = process.pid
            if pid:
                try:
                    parent = psutil.Process(pid)
                    children = parent.children(recursive=True)
                    for child in children:
                        try: child.terminate()
                        except psutil.NoSuchProcess: pass
                        except Exception:
                            try: child.kill()
                            except: pass
                    psutil.wait_procs(children, timeout=1)
                    try:
                        parent.terminate()
                        try: parent.wait(timeout=1)
                        except psutil.TimeoutExpired: parent.kill()
                    except psutil.NoSuchProcess: pass
                    except Exception:
                        try: parent.kill()
                        except: pass
                except psutil.NoSuchProcess: pass
    except Exception as e:
        logger.error(f"Error killing process tree for PID {pid or 'N/A'} ({script_key}): {e}", exc_info=True)

# --- Automatic Package Installation ---
TELEGRAM_MODULES = {
    'telebot': 'pyTelegramBotAPI', 'telegram': 'python-telegram-bot',
    'aiogram': 'aiogram', 'pyrogram': 'pyrogram', 'telethon': 'telethon',
    'bs4': 'beautifulsoup4', 'requests': 'requests', 'pillow': 'Pillow',
    'cv2': 'opencv-python', 'yaml': 'PyYAML', 'dotenv': 'python-dotenv',
    'pandas': 'pandas', 'numpy': 'numpy', 'flask': 'Flask', 'psutil': 'psutil',
    'asyncio': None, 'json': None, 'datetime': None, 'os': None, 'sys': None,
    're': None, 'time': None, 'math': None, 'random': None, 'logging': None,
    'threading': None, 'subprocess': None, 'zipfile': None, 'tempfile': None,
    'shutil': None, 'sqlite3': None, 'atexit': None
}

def attempt_install_pip(module_name, message):
    package_name = TELEGRAM_MODULES.get(module_name.lower(), module_name)
    if package_name is None: return False
    try:
        bot.reply_to(message, f"Module `{module_name}` not found. Installing `{package_name}`...", parse_mode='Markdown')
        command = [sys.executable, '-m', 'pip', 'install', package_name]
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"Package `{package_name}` installed.", parse_mode='Markdown')
            return True
        else:
            error_msg = f"Failed to install `{package_name}`.\n```\n{result.stderr or result.stdout}\n```"
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (truncated)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False
    except Exception as e:
        bot.reply_to(message, f"Error installing `{package_name}`: {str(e)}")
        return False

def attempt_install_npm(module_name, user_folder, message):
    try:
        bot.reply_to(message, f"Node package `{module_name}` not found. Installing...", parse_mode='Markdown')
        result = subprocess.run(['npm', 'install', module_name], capture_output=True, text=True, check=False, cwd=user_folder, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            bot.reply_to(message, f"Node package `{module_name}` installed.", parse_mode='Markdown')
            return True
        else:
            error_msg = f"Failed to install `{module_name}`.\n```\n{result.stderr or result.stdout}\n```"
            if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (truncated)"
            bot.reply_to(message, error_msg, parse_mode='Markdown')
            return False
    except FileNotFoundError:
        bot.reply_to(message, "Error: 'npm' not found. Install Node.js.")
        return False
    except Exception as e:
        bot.reply_to(message, f"Error installing `{module_name}`: {str(e)}")
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
            if script_owner_id in user_files:
                user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
            remove_user_file_db(script_owner_id, file_name)
            return
        if attempt == 1:
            check_proc = None
            try:
                check_proc = subprocess.Popen([sys.executable, script_path], cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                if return_code != 0 and stderr:
                    match_py = re.search(r"ModuleNotFoundError: No module named '(.+?)'", stderr)
                    if match_py:
                        module_name = match_py.group(1).strip().strip("'\"")
                        if attempt_install_pip(module_name, message_obj_for_reply):
                            bot.reply_to(message_obj_for_reply, f"Retrying '{file_name}'...")
                            time.sleep(2)
                            threading.Thread(target=run_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                            return
                        else:
                            bot.reply_to(message_obj_for_reply, f"Install failed. Cannot run '{file_name}'.")
                            return
                    else:
                        bot.reply_to(message_obj_for_reply, f"Error in '{file_name}':\n```\n{stderr[:500]}\n```", parse_mode='Markdown')
                        return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, f"Python interpreter not found: {sys.executable}")
                return
            except Exception as e:
                bot.reply_to(message_obj_for_reply, f"Error in pre-check: {e}")
                return
            finally:
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"Failed to open log file: {e}")
            return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen([sys.executable, script_path], cwd=user_folder, stdout=log_file, stderr=log_file, stdin=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags, encoding='utf-8', errors='ignore')
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'py', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"Python script '{file_name}' started! (PID: {process.pid})")
        except FileNotFoundError:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"Python interpreter not found for long run.")
            if script_key in bot_scripts: del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"Error starting '{file_name}': {str(e)}")
            if process and process.poll() is None:
                kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        bot.reply_to(message_obj_for_reply, f"Error running '{file_name}': {str(e)}")
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key]); del bot_scripts[script_key]

def run_js_script(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt=1):
    max_attempts = 2
    if attempt > max_attempts:
        bot.reply_to(message_obj_for_reply, f"Failed to run '{file_name}' after {max_attempts} attempts.")
        return
    script_key = f"{script_owner_id}_{file_name}"
    try:
        if not os.path.exists(script_path):
            bot.reply_to(message_obj_for_reply, f"Error: Script '{file_name}' not found!")
            if script_owner_id in user_files:
                user_files[script_owner_id] = [f for f in user_files.get(script_owner_id, []) if f[0] != file_name]
            remove_user_file_db(script_owner_id, file_name)
            return
        if attempt == 1:
            check_proc = None
            try:
                check_proc = subprocess.Popen(['node', script_path], cwd=user_folder, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
                stdout, stderr = check_proc.communicate(timeout=5)
                return_code = check_proc.returncode
                if return_code != 0 and stderr:
                    match_js = re.search(r"Cannot find module '(.+?)'", stderr)
                    if match_js:
                        module_name = match_js.group(1).strip().strip("'\"")
                        if not module_name.startswith('.') and not module_name.startswith('/'):
                            if attempt_install_npm(module_name, user_folder, message_obj_for_reply):
                                bot.reply_to(message_obj_for_reply, f"Retrying '{file_name}'...")
                                time.sleep(2)
                                threading.Thread(target=run_js_script, args=(script_path, script_owner_id, user_folder, file_name, message_obj_for_reply, attempt + 1)).start()
                                return
                            else:
                                bot.reply_to(message_obj_for_reply, f"NPM Install failed. Cannot run '{file_name}'.")
                                return
                    bot.reply_to(message_obj_for_reply, f"Error in JS pre-check for '{file_name}':\n```\n{stderr[:500]}\n```", parse_mode='Markdown')
                    return
            except subprocess.TimeoutExpired:
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
            except FileNotFoundError:
                bot.reply_to(message_obj_for_reply, "Error: 'node' not found. Install Node.js.")
                return
            except Exception as e:
                bot.reply_to(message_obj_for_reply, f"Error in pre-check: {e}")
                return
            finally:
                if check_proc and check_proc.poll() is None: check_proc.kill(); check_proc.communicate()
        log_file_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        log_file = None; process = None
        try: log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
        except Exception as e:
            bot.reply_to(message_obj_for_reply, f"Failed to open log file: {e}")
            return
        try:
            startupinfo = None; creationflags = 0
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW; startupinfo.wShowWindow = subprocess.SW_HIDE
            process = subprocess.Popen(['node', script_path], cwd=user_folder, stdout=log_file, stderr=log_file, stdin=subprocess.PIPE, startupinfo=startupinfo, creationflags=creationflags, encoding='utf-8', errors='ignore')
            bot_scripts[script_key] = {
                'process': process, 'log_file': log_file, 'file_name': file_name,
                'chat_id': message_obj_for_reply.chat.id, 'script_owner_id': script_owner_id,
                'start_time': datetime.now(), 'user_folder': user_folder, 'type': 'js', 'script_key': script_key
            }
            bot.reply_to(message_obj_for_reply, f"JS script '{file_name}' started! (PID: {process.pid})")
        except FileNotFoundError:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, "Error: 'node' not found for long run.")
            if script_key in bot_scripts: del bot_scripts[script_key]
        except Exception as e:
            if log_file and not log_file.closed: log_file.close()
            bot.reply_to(message_obj_for_reply, f"Error starting '{file_name}': {str(e)}")
            if process and process.poll() is None:
                kill_process_tree({'process': process, 'log_file': log_file, 'script_key': script_key})
            if script_key in bot_scripts: del bot_scripts[script_key]
    except Exception as e:
        bot.reply_to(message_obj_for_reply, f"Error running JS '{file_name}': {str(e)}")
        if script_key in bot_scripts:
            kill_process_tree(bot_scripts[script_key]); del bot_scripts[script_key]

# --- Database Operations ---
DB_LOCK = threading.Lock()

def save_user_file(user_id, file_name, file_type='py'):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO user_files (user_id, file_name, file_type) VALUES (?, ?, ?)', (user_id, file_name, file_type))
            conn.commit()
            if user_id not in user_files: user_files[user_id] = []
            user_files[user_id] = [(fn, ft) for fn, ft in user_files[user_id] if fn != file_name]
            user_files[user_id].append((file_name, file_type))
        except sqlite3.Error as e: logger.error(f"SQLite error saving file: {e}")
        finally: conn.close()

def remove_user_file_db(user_id, file_name):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', (user_id, file_name))
            conn.commit()
            if user_id in user_files:
                user_files[user_id] = [f for f in user_files[user_id] if f[0] != file_name]
                if not user_files[user_id]: del user_files[user_id]
        except sqlite3.Error as e: logger.error(f"SQLite error removing file: {e}")
        finally: conn.close()

def add_active_user(user_id):
    active_users.add(user_id)
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
            conn.commit()
        except sqlite3.Error as e: logger.error(f"SQLite error adding active user: {e}")
        finally: conn.close()

def save_subscription(user_id, expiry):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', (user_id, expiry.isoformat()))
            conn.commit()
            user_subscriptions[user_id] = {'expiry': expiry}
        except sqlite3.Error as e: logger.error(f"SQLite error saving subscription: {e}")
        finally: conn.close()

def remove_subscription_db(user_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
            conn.commit()
            if user_id in user_subscriptions: del user_subscriptions[user_id]
        except sqlite3.Error as e: logger.error(f"SQLite error removing sub: {e}")
        finally: conn.close()

def add_admin_db(admin_id):
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (?)', (admin_id,))
            conn.commit()
            admin_ids.add(admin_id)
        except sqlite3.Error as e: logger.error(f"SQLite error adding admin: {e}")
        finally: conn.close()

def remove_admin_db(admin_id):
    if admin_id == OWNER_ID: return False
    with DB_LOCK:
        conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute('SELECT 1 FROM admins WHERE user_id = ?', (admin_id,))
            if c.fetchone():
                c.execute('DELETE FROM admins WHERE user_id = ?', (admin_id,))
                conn.commit()
                admin_ids.discard(admin_id)
                return c.rowcount > 0
            else:
                admin_ids.discard(admin_id)
            return False
        except sqlite3.Error as e: logger.error(f"SQLite error removing admin: {e}"); return False
        finally: conn.close()

# --- Menu Creation ---
def create_main_menu_inline(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Channel button at top
    markup.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
    # Main link button
    markup.add(types.InlineKeyboardButton(MAIN_LINK_TEXT, url=MAIN_LINK_URL))
    
    if user_id in admin_ids:
        # Admin buttons - colorful
        markup.row(
            types.InlineKeyboardButton("📤 Upload File", callback_data='upload'),
            types.InlineKeyboardButton("📂 My Files", callback_data='check_files')
        )
        markup.row(
            types.InlineKeyboardButton("⚡ Bot Speed", callback_data='speed'),
            types.InlineKeyboardButton("📊 Statistics", callback_data='stats')
        )
        markup.row(
            types.InlineKeyboardButton("💳 Subscriptions", callback_data='subscription'),
            types.InlineKeyboardButton("📢 Broadcast", callback_data='broadcast')
        )
        markup.row(
            types.InlineKeyboardButton("🔒 Lock Bot" if not bot_locked else "🔓 Unlock Bot", 
                                       callback_data='lock_bot' if not bot_locked else 'unlock_bot'),
            types.InlineKeyboardButton("🟢 Run All", callback_data='run_all_scripts')
        )
        markup.row(
            types.InlineKeyboardButton("👑 Admin Panel", callback_data='admin_panel')
        )
    else:
        # User buttons - colorful
        markup.row(
            types.InlineKeyboardButton("📤 Upload File", callback_data='upload'),
            types.InlineKeyboardButton("📂 My Files", callback_data='check_files')
        )
        markup.row(
            types.InlineKeyboardButton("⚡ Bot Speed", callback_data='speed'),
            types.InlineKeyboardButton("📊 Statistics", callback_data='stats')
        )
    
    # Owner buttons - show usernames with colors
    markup.row(
        types.InlineKeyboardButton(f"🔴 {YOUR_USERNAME}", callback_data='contact_owner1'),
        types.InlineKeyboardButton(f"🔵 {YOUR_USERNAME_2}", callback_data='contact_owner2')
    )
    return markup

def create_reply_keyboard_main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    layout = ADMIN_COMMAND_BUTTONS_LAYOUT_USER_SPEC if user_id in admin_ids else COMMAND_BUTTONS_LAYOUT_USER_SPEC
    for row in layout:
        markup.add(*[types.KeyboardButton(text) for text in row])
    return markup

def create_control_buttons(script_owner_id, file_name, is_running=True):
    markup = types.InlineKeyboardMarkup(row_width=2)
    if is_running:
        markup.row(
            types.InlineKeyboardButton("🔴 Stop", callback_data=f'stop_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🔄 Restart", callback_data=f'restart_{script_owner_id}_{file_name}')
        )
        markup.row(
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("📜 Logs", callback_data=f'logs_{script_owner_id}_{file_name}')
        )
    else:
        markup.row(
            types.InlineKeyboardButton("🟢 Start", callback_data=f'start_{script_owner_id}_{file_name}'),
            types.InlineKeyboardButton("🗑️ Delete", callback_data=f'delete_{script_owner_id}_{file_name}')
        )
        markup.row(types.InlineKeyboardButton("📜 View Logs", callback_data=f'logs_{script_owner_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back to Files", callback_data='check_files'))
    return markup

def create_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton('➕ Add Admin', callback_data='add_admin'), types.InlineKeyboardButton('➖ Remove Admin', callback_data='remove_admin'))
    markup.row(types.InlineKeyboardButton('📋 List Admins', callback_data='list_admins'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

def create_subscription_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(types.InlineKeyboardButton('➕ Add Subscription', callback_data='add_subscription'), types.InlineKeyboardButton('➖ Remove Subscription', callback_data='remove_subscription'))
    markup.row(types.InlineKeyboardButton('🔍 Check Subscription', callback_data='check_subscription'))
    markup.row(types.InlineKeyboardButton('🔙 Back to Main', callback_data='back_to_main'))
    return markup

# --- File Handling ---
def handle_zip_file(downloaded_file_content, file_name_zip, message):
    user_id = message.from_user.id
    user_folder = get_user_folder(user_id)
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix=f"user_{user_id}_zip_")
        zip_path = os.path.join(temp_dir, file_name_zip)
        with open(zip_path, 'wb') as new_file: new_file.write(downloaded_file_content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.abspath(os.path.join(temp_dir, member.filename))
                if not member_path.startswith(os.path.abspath(temp_dir)):
                    raise zipfile.BadZipFile(f"Zip has unsafe path: {member.filename}")
            zip_ref.extractall(temp_dir)
        extracted_items = os.listdir(temp_dir)
        py_files = [f for f in extracted_items if f.endswith('.py')]
        js_files = [f for f in extracted_items if f.endswith('.js')]
        req_file = 'requirements.txt' if 'requirements.txt' in extracted_items else None
        pkg_json = 'package.json' if 'package.json' in extracted_items else None
        if req_file:
            req_path = os.path.join(temp_dir, req_file)
            bot.reply_to(message, f"Installing Python deps from `{req_file}`...")
            try:
                result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', req_path], capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
                bot.reply_to(message, f"Python deps installed.")
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to install Python deps.\n```\n{e.stderr or e.stdout}\n```"
                if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (truncated)"
                bot.reply_to(message, error_msg, parse_mode='Markdown'); return
            except Exception as e: bot.reply_to(message, f"Error installing Python deps: {e}"); return
        if pkg_json:
            bot.reply_to(message, f"Installing Node deps from `{pkg_json}`...")
            try:
                result = subprocess.run(['npm', 'install'], capture_output=True, text=True, check=True, cwd=temp_dir, encoding='utf-8', errors='ignore')
                bot.reply_to(message, f"Node deps installed.")
            except FileNotFoundError: bot.reply_to(message, "'npm' not found."); return
            except subprocess.CalledProcessError as e:
                error_msg = f"Failed to install Node deps.\n```\n{e.stderr or e.stdout}\n```"
                if len(error_msg) > 4000: error_msg = error_msg[:4000] + "\n... (truncated)"
                bot.reply_to(message, error_msg, parse_mode='Markdown'); return
            except Exception as e: bot.reply_to(message, f"Error installing Node deps: {e}"); return
        main_script_name = None; file_type = None
        preferred_py = ['main.py', 'bot.py', 'app.py']; preferred_js = ['index.js', 'main.js', 'bot.js', 'app.js']
        for p in preferred_py:
            if p in py_files: main_script_name = p; file_type = 'py'; break
        if not main_script_name:
            for p in preferred_js:
                if p in js_files: main_script_name = p; file_type = 'js'; break
        if not main_script_name:
            if py_files: main_script_name = py_files[0]; file_type = 'py'
            elif js_files: main_script_name = js_files[0]; file_type = 'js'
        if not main_script_name:
            bot.reply_to(message, "No `.py` or `.js` script found in archive!"); return
        for item_name in os.listdir(temp_dir):
            src_path = os.path.join(temp_dir, item_name)
            dest_path = os.path.join(user_folder, item_name)
            if os.path.isdir(dest_path): shutil.rmtree(dest_path)
            elif os.path.exists(dest_path): os.remove(dest_path)
            shutil.move(src_path, dest_path)
        save_user_file(user_id, main_script_name, file_type)
        main_script_path = os.path.join(user_folder, main_script_name)
        bot.reply_to(message, f"Extracted. Starting: `{main_script_name}`...", parse_mode='Markdown')
        if file_type == 'py':
            threading.Thread(target=run_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(main_script_path, user_id, user_folder, main_script_name, message)).start()
    except zipfile.BadZipFile as e:
        bot.reply_to(message, f"Invalid ZIP: {e}")
    except Exception as e:
        bot.reply_to(message, f"Error processing zip: {str(e)}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except: pass

def handle_js_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'js')
        threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        bot.reply_to(message, f"Error processing JS file: {str(e)}")

def handle_py_file(file_path, script_owner_id, user_folder, file_name, message):
    try:
        save_user_file(script_owner_id, file_name, 'py')
        threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, message)).start()
    except Exception as e:
        bot.reply_to(message, f"Error processing Python file: {str(e)}")

# ============================================================
# --- LOGIC FUNCTIONS (with channel verification & image) ---
# ============================================================

def _logic_send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_name = message.from_user.first_name
    user_username = message.from_user.username

    # --- Channel verification check ---
    if not is_user_verified(user_id):
        if user_id not in admin_ids:
            if check_channel_membership(user_id):
                verify_user(user_id)
            else:
                send_welcome_with_photo(chat_id,
                    f"{BOT_NAME}\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"Hey {user_name}! 👋\n"
                    f"Join our channel to use the bot.\n"
                    f"━━━━━━━━━━━━━━━━━━",
                    reply_markup=create_join_channel_markup())
                return

    if bot_locked and user_id not in admin_ids:
        send_reply_with_link(message,
            f"{BOT_NAME}\n\n"
            f"⛔ Bot is currently locked.\nTry again later.")
        return

    add_active_user(user_id)

    if user_id not in active_users:
        try:
            owner_notification = (f"🆕 New User Joined!\n\n"
                                  f"👤 Name: {user_name}\n"
                                  f"✳️ Username: @{user_username or 'N/A'}\n"
                                  f"🆔 ID: `{user_id}`")
            bot.send_message(OWNER_ID, owner_notification, parse_mode='Markdown')
        except Exception as e: logger.error(f"Failed to notify owner: {e}")

    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "∞"

    if user_id == OWNER_ID: user_status = "👑 Owner"
    elif user_id in admin_ids: user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"; days_left = (expiry_date - datetime.now()).days
        else: user_status = "🆓 Free (Expired)"; remove_subscription_db(user_id)
    else: user_status = "🆓 Free User"

    # WELCOME with PHOTO
    send_welcome_with_photo(chat_id,
        f"{BOT_NAME}\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"✨ Welcome, {user_name}!\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"🔰 Status: {user_status}\n"
        f"📂 Files: {current_files} / {limit_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🚀 Host & run Python/JS scripts\n"
        f"Upload .py, .js or .zip file",
        reply_markup=create_reply_keyboard_main_menu(user_id),
        parse_mode='Markdown')

def _logic_updates_channel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"📢 {CHANNEL_NAME}", url=CHANNEL_LINK))
    send_reply_with_link(message,
        f"{BOT_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📢 Join our official channel!",
        reply_markup=markup)

def _logic_upload_file(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        send_reply_with_link(message, f"{BOT_NAME}\n\n⚠️ Join channel first! Use /start")
        return
    if bot_locked and user_id not in admin_ids:
        send_reply_with_link(message, f"{BOT_NAME}\n\n🔒 Bot locked by admin.")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "∞"
        send_reply_with_link(message, f"{BOT_NAME}\n\n⚠️ File limit reached ({current_files}/{limit_str})\nDelete files first.")
        return
    send_reply_with_link(message,
        f"{BOT_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📤 Send your file:\n"
        f"• .py (Python)\n"
        f"• .js (Node.js)\n"
        f"• .zip (Archive)\n"
        f"━━━━━━━━━━━━━━━━━━")

def _logic_check_files(message):
    user_id = message.from_user.id
    if not is_user_verified(user_id):
        send_reply_with_link(message, f"{BOT_NAME}\n\n⚠️ Join channel first! Use /start")
        return
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        send_reply_with_link(message, f"{BOT_NAME}\n\n📂 No files uploaded yet.")
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(MAIN_LINK_TEXT, url=MAIN_LINK_URL))
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢" if is_running else "🔴"
        btn_text = f"{status_icon} {file_name} ({file_type})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    send_reply_with_link(message,
        f"{BOT_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📂 Your Files:",
        reply_markup=markup)

def _logic_bot_speed(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    start_time_ping = time.time()
    wait_msg = bot.reply_to(message, f"{BOT_NAME}\n\n⚡ Testing speed...")
    try:
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_time_ping) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID: user_level = "👑 Owner"
        elif user_id in admin_ids: user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now(): user_level = "⭐ Premium"
        else: user_level = "🆓 Free User"
        edit_with_link_button(chat_id, wait_msg.message_id,
            f"{BOT_NAME}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Speed & Status\n\n"
            f"⏱️ Response: {response_time} ms\n"
            f"🚦 Status: {status}\n"
            f"👤 Level: {user_level}\n"
            f"━━━━━━━━━━━━━━━━━━")
    except Exception as e:
        bot.edit_message_text("❌ Error during speed test.", chat_id, wait_msg.message_id)

def _logic_contact_owner(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton(f"🔴 {YOUR_USERNAME}", url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'),
        types.InlineKeyboardButton(f"🔵 {YOUR_USERNAME_2}", url=f'https://t.me/{YOUR_USERNAME_2.replace("@", "")}')
    )
    send_reply_with_link(message,
        f"{BOT_NAME}\n\n"
        f"📞 Contact Owners\n\n"
        f"🔴 {YOUR_USERNAME}\n"
        f"🔵 {YOUR_USERNAME_2}",
        reply_markup=markup)

def show_owner1_profile(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"🔴 {YOUR_USERNAME}", url=f'https://t.me/{YOUR_USERNAME.replace("@", "")}'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    bot.edit_message_text(
        f"{BOT_NAME}\n\n"
        f"🔴 Owner 1\n\n"
        f"Username: {YOUR_USERNAME}\n"
        f"ID: `{OWNER_ID}`",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode='Markdown')

def show_owner2_profile(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"🔵 {YOUR_USERNAME_2}", url=f'https://t.me/{YOUR_USERNAME_2.replace("@", "")}'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    bot.edit_message_text(
        f"{BOT_NAME}\n\n"
        f"🔵 Owner 2\n\n"
        f"Username: {YOUR_USERNAME_2}\n"
        f"ID: `{OWNER_ID_2}`",
        call.message.chat.id, call.message.message_id,
        reply_markup=markup, parse_mode='Markdown')

def _logic_statistics(message):
    user_id = message.from_user.id
    total_users = len(active_users)
    total_files_records = sum(len(files) for files in user_files.values())
    running_bots_count = 0
    user_running_bots = 0
    for script_key_iter, script_info_iter in list(bot_scripts.items()):
        s_owner_id, _ = script_key_iter.split('_', 1)
        if is_bot_running(int(s_owner_id), script_info_iter['file_name']):
            running_bots_count += 1
            if int(s_owner_id) == user_id: user_running_bots += 1
    stats_msg = (f"{BOT_NAME}\n\n"
                 f"━━━━━━━━━━━━━━━━━━\n"
                 f"📊 Statistics\n\n"
                 f"👥 Total Users: {total_users}\n"
                 f"📂 File Records: {total_files_records}\n"
                 f"🟢 Active Bots: {running_bots_count}\n")
    if user_id in admin_ids:
        stats_msg += f"🔒 Status: {'🔴 Locked' if bot_locked else '🟢 Unlocked'}\n"
    stats_msg += f"🤖 Your Bots: {user_running_bots}\n━━━━━━━━━━━━━━━━━━"
    send_reply_with_link(message, stats_msg)

def _logic_subscriptions_panel(message):
    if message.from_user.id not in admin_ids:
        send_reply_with_link(message, f"{BOT_NAME}\n\n⚠️ Admin permissions required.")
        return
    send_reply_with_link(message,
        f"{BOT_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💳 Subscription Management:",
        reply_markup=create_subscription_menu())

def _logic_broadcast_init(message):
    if message.from_user.id not in admin_ids:
        send_reply_with_link(message, f"{BOT_NAME}\n\n⚠️ Admin permissions required.")
        return
    msg = bot.reply_to(message,
        f"{BOT_NAME}\n\n"
        f"📢 Send message to broadcast.\n"
        f"/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def _logic_toggle_lock_bot(message):
    if message.from_user.id not in admin_ids:
        send_reply_with_link(message, f"{BOT_NAME}\n\n⚠️ Admin permissions required.")
        return
    global bot_locked
    bot_locked = not bot_locked
    status = "🔒 Locked" if bot_locked else "🔓 Unlocked"
    send_reply_with_link(message,
        f"{BOT_NAME}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Bot has been {status}\n"
        f"━━━━━━━━━━━━━━━━━━")

def _logic_admin_panel(message):
    if message.from_user.id not in admin_ids:
        send_reply_with_link(message, f"{BOT_NAME}\n\n⚠️ Admin permissions required.")
        return
    send_reply_with_link(message,
        f"{BOT_NAME}\n\n👑 Admin Panel",
        reply_markup=create_admin_panel())

def _logic_run_all_scripts(message_or_call):
    if isinstance(message_or_call, telebot.types.Message):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.chat.id
        reply_func = lambda text, **kwargs: send_reply_with_link(message_or_call, text, **kwargs)
        admin_message_obj = message_or_call
    elif isinstance(message_or_call, telebot.types.CallbackQuery):
        admin_user_id = message_or_call.from_user.id
        admin_chat_id = message_or_call.message.chat.id
        bot.answer_callback_query(message_or_call.id)
        reply_func = lambda text, **kwargs: send_message_with_link(admin_chat_id, text, **kwargs)
        admin_message_obj = message_or_call.message
    else: return
    if admin_user_id not in admin_ids:
        reply_func(f"{BOT_NAME}\n\n⚠️ Admin permissions required.")
        return
    reply_func(f"{BOT_NAME}\n\n⏳ Starting all user scripts...")
    started_count = 0; skipped_files = 0
    all_user_files_snapshot = dict(user_files)
    for target_user_id, files_for_user in all_user_files_snapshot.items():
        if not files_for_user: continue
        user_folder = get_user_folder(target_user_id)
        for file_name, file_type in files_for_user:
            if not is_bot_running(target_user_id, file_name):
                file_path = os.path.join(user_folder, file_name)
                if os.path.exists(file_path):
                    try:
                        if file_type == 'py':
                            threading.Thread(target=run_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj)).start()
                            started_count += 1
                        elif file_type == 'js':
                            threading.Thread(target=run_js_script, args=(file_path, target_user_id, user_folder, file_name, admin_message_obj)).start()
                            started_count += 1
                        else: skipped_files += 1
                        time.sleep(0.7)
                    except: skipped_files += 1
                else: skipped_files += 1
    reply_func(f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n✅ Done!\n\n🚀 Started: {started_count}\n⚠️ Skipped: {skipped_files}\n━━━━━━━━━━━━━━━━━━")

# --- Command Handlers ---
@bot.message_handler(commands=['start', 'help'])
def command_send_welcome(message): _logic_send_welcome(message)

@bot.message_handler(commands=['status'])
def command_show_status(message): _logic_statistics(message)

@bot.message_handler(commands=['ping'])
def ping(message):
    start_ping_time = time.time()
    msg = bot.reply_to(message, "Pong!")
    latency = round((time.time() - start_ping_time) * 1000, 2)
    bot.edit_message_text(f"Pong! Latency: {latency} ms", message.chat.id, msg.message_id)

BUTTON_TEXT_TO_LOGIC = {
    "📢 Updates Channel": _logic_updates_channel,
    "📤 Upload File": _logic_upload_file,
    "📂 Check Files": _logic_check_files,
    "⚡ Bot Speed": _logic_bot_speed,
    "📞 Contact Owner": _logic_contact_owner,
    "📊 Statistics": _logic_statistics,
    "💳 Subscriptions": _logic_subscriptions_panel,
    "📢 Broadcast": _logic_broadcast_init,
    "🔒 Lock Bot": _logic_toggle_lock_bot,
    "🟢 Running All Code": _logic_run_all_scripts,
    "👑 Admin Panel": _logic_admin_panel,
}

@bot.message_handler(func=lambda message: message.text in BUTTON_TEXT_TO_LOGIC)
def handle_button_text(message):
    logic_func = BUTTON_TEXT_TO_LOGIC.get(message.text)
    if logic_func: logic_func(message)

@bot.message_handler(commands=['updateschannel'])
def command_updates_channel(message): _logic_updates_channel(message)
@bot.message_handler(commands=['uploadfile'])
def command_upload_file(message): _logic_upload_file(message)
@bot.message_handler(commands=['checkfiles'])
def command_check_files(message): _logic_check_files(message)
@bot.message_handler(commands=['botspeed'])
def command_bot_speed(message): _logic_bot_speed(message)
@bot.message_handler(commands=['contactowner'])
def command_contact_owner(message): _logic_contact_owner(message)
@bot.message_handler(commands=['subscriptions'])
def command_subscriptions(message): _logic_subscriptions_panel(message)
@bot.message_handler(commands=['statistics'])
def command_statistics(message): _logic_statistics(message)
@bot.message_handler(commands=['broadcast'])
def command_broadcast(message): _logic_broadcast_init(message)
@bot.message_handler(commands=['lockbot'])
def command_lock_bot(message): _logic_toggle_lock_bot(message)
@bot.message_handler(commands=['adminpanel'])
def command_admin_panel(message): _logic_admin_panel(message)
@bot.message_handler(commands=['runningallcode'])
def command_run_all_code(message): _logic_run_all_scripts(message)

# --- Document Handler ---
@bot.message_handler(content_types=['document'])
def handle_file_upload_doc(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    doc = message.document

    if not is_user_verified(user_id):
        bot.reply_to(message, "Please join our channel first! Use /start")
        return

    if bot_locked and user_id not in admin_ids:
        bot.reply_to(message, "Bot locked.")
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.reply_to(message, f"File limit reached ({current_files}/{limit_str}). Delete files first.")
        return
    file_name = doc.file_name
    if not file_name: bot.reply_to(message, "No file name."); return
    file_ext = os.path.splitext(file_name)[1].lower()
    if file_ext not in ['.py', '.js', '.zip']:
        bot.reply_to(message, "Only .py, .js, .zip files allowed.")
        return
    max_file_size = 20 * 1024 * 1024
    if doc.file_size > max_file_size:
        bot.reply_to(message, f"File too large (Max: {max_file_size // 1024 // 1024} MB)."); return
    try:
        try:
            bot.forward_message(OWNER_ID, chat_id, message.message_id)
            bot.send_message(OWNER_ID, f"File '{file_name}' from {message.from_user.first_name} (`{user_id}`)", parse_mode='Markdown')
        except: pass
        download_wait_msg = bot.reply_to(message, f"Downloading `{file_name}`...")
        file_info = bot.get_file(doc.file_id)
        downloaded_content = bot.download_file(file_info.file_path)
        bot.edit_message_text(f"Downloaded. Processing...", chat_id, download_wait_msg.message_id)
        user_folder = get_user_folder(user_id)
        if file_ext == '.zip':
            handle_zip_file(downloaded_content, file_name, message)
        else:
            file_path = os.path.join(user_folder, file_name)
            with open(file_path, 'wb') as f: f.write(downloaded_content)
            if file_ext == '.js': handle_js_file(file_path, user_id, user_folder, file_name, message)
            elif file_ext == '.py': handle_py_file(file_path, user_id, user_folder, file_name, message)
    except Exception as e:
        bot.reply_to(message, f"Error handling file: {str(e)}")

# --- Callback Query Handlers ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    data = call.data

    # --- VERIFY JOIN CALLBACK ---
    if data == 'verify_join':
        if check_channel_membership(user_id):
            verify_user(user_id)
            bot.answer_callback_query(call.id, "Verified! Welcome!")
            bot.edit_message_text(
                f"Welcome {call.from_user.first_name}! Channel verified.\n\nUse /start to continue.",
                call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "You haven't joined the channel yet! Join first.", show_alert=True)
        return

    if bot_locked and user_id not in admin_ids and data not in ['back_to_main', 'speed', 'stats']:
        bot.answer_callback_query(call.id, "Bot locked by admin.", show_alert=True)
        return

    try:
        if data == 'upload': upload_callback(call)
        elif data == 'check_files': check_files_callback(call)
        elif data.startswith('file_'): file_control_callback(call)
        elif data.startswith('start_'): start_bot_callback(call)
        elif data.startswith('stop_'): stop_bot_callback(call)
        elif data.startswith('restart_'): restart_bot_callback(call)
        elif data.startswith('delete_'): delete_bot_callback(call)
        elif data.startswith('logs_'): logs_bot_callback(call)
        elif data == 'speed': speed_callback(call)
        elif data == 'back_to_main': back_to_main_callback(call)
        elif data == 'contact_owner1': show_owner1_profile(call)
        elif data == 'contact_owner2': show_owner2_profile(call)
        elif data == 'noop': bot.answer_callback_query(call.id)  # Do nothing for separator
        elif data.startswith('confirm_broadcast_'): handle_confirm_broadcast(call)
        elif data == 'cancel_broadcast': handle_cancel_broadcast(call)
        elif data == 'subscription': admin_required_callback(call, subscription_management_callback)
        elif data == 'stats': stats_callback(call)
        elif data == 'lock_bot': admin_required_callback(call, lock_bot_callback)
        elif data == 'unlock_bot': admin_required_callback(call, unlock_bot_callback)
        elif data == 'run_all_scripts': admin_required_callback(call, run_all_scripts_callback)
        elif data == 'broadcast': admin_required_callback(call, broadcast_init_callback)
        elif data == 'admin_panel': admin_required_callback(call, admin_panel_callback)
        elif data == 'add_admin': owner_required_callback(call, add_admin_init_callback)
        elif data == 'remove_admin': owner_required_callback(call, remove_admin_init_callback)
        elif data == 'list_admins': admin_required_callback(call, list_admins_callback)
        elif data == 'add_subscription': admin_required_callback(call, add_subscription_init_callback)
        elif data == 'remove_subscription': admin_required_callback(call, remove_subscription_init_callback)
        elif data == 'check_subscription': admin_required_callback(call, check_subscription_init_callback)
        else:
            bot.answer_callback_query(call.id, "Unknown action.")
    except Exception as e:
        logger.error(f"Error handling callback '{data}': {e}", exc_info=True)
        try: bot.answer_callback_query(call.id, "Error.", show_alert=True)
        except: pass

def admin_required_callback(call, func_to_run):
    if call.from_user.id not in admin_ids:
        bot.answer_callback_query(call.id, "Admin permissions required.", show_alert=True)
        return
    func_to_run(call)

def owner_required_callback(call, func_to_run):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "Owner permissions required.", show_alert=True)
        return
    func_to_run(call)

def upload_callback(call):
    user_id = call.from_user.id
    if not is_user_verified(user_id):
        bot.answer_callback_query(call.id, "Join channel first!", show_alert=True)
        return
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    if current_files >= file_limit:
        limit_str = str(file_limit) if file_limit != float('inf') else "Unlimited"
        bot.answer_callback_query(call.id, f"File limit reached ({current_files}/{limit_str}).", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    send_message_with_link(call.message.chat.id, "Send your Python (.py), JS (.js), or ZIP (.zip) file.")

def check_files_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    user_files_list = user_files.get(user_id, [])
    if not user_files_list:
        bot.answer_callback_query(call.id, "No files uploaded.", show_alert=True)
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(MAIN_LINK_TEXT, url=MAIN_LINK_URL))
            markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
            bot.edit_message_text(f"{BOT_NAME}\n\n📂 No files uploaded yet.", chat_id, call.message.message_id, reply_markup=markup)
        except: pass
        return
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(MAIN_LINK_TEXT, url=MAIN_LINK_URL))
    for file_name, file_type in sorted(user_files_list):
        is_running = is_bot_running(user_id, file_name)
        status_icon = "🟢" if is_running else "🔴"
        markup.add(types.InlineKeyboardButton(f"{status_icon} {file_name} ({file_type})", callback_data=f'file_{user_id}_{file_name}'))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
    try:
        bot.edit_message_text(f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n📂 Your Files:", chat_id, call.message.message_id, reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e): logger.error(f"Error editing msg: {e}")
    except Exception as e: logger.error(f"Unexpected error: {e}", exc_info=True)

def file_control_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "You can only manage your own files.", show_alert=True)
            check_files_callback(call)
            return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "File not found.", show_alert=True)
            check_files_callback(call)
            return
        bot.answer_callback_query(call.id)
        is_running = is_bot_running(script_owner_id, file_name)
        status_icon = '🟢 Running' if is_running else '🔴 Stopped'
        file_type = next((f[1] for f in user_files_list if f[0] == file_name), '?')
        try:
            edit_with_link_button(
                call.message.chat.id, call.message.message_id,
                f"{BOT_NAME}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚙️ `{file_name}` ({file_type})\n"
                f"🆔 User: `{script_owner_id}`\n"
                f"📊 Status: {status_icon}\n"
                f"━━━━━━━━━━━━━━━━━━",
                reply_markup=create_control_buttons(script_owner_id, file_name, is_running), parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e): raise
    except (ValueError, IndexError): bot.answer_callback_query(call.id, "Error.", show_alert=True)
    except Exception as e: logger.error(f"Error: {e}", exc_info=True); bot.answer_callback_query(call.id, "Error.", show_alert=True)

def start_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "Permission denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "File not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1]
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"File missing!", show_alert=True)
            remove_user_file_db(script_owner_id, file_name); check_files_callback(call); return
        if is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"Already running.", show_alert=True)
            try: bot.edit_message_reply_markup(chat_id_for_reply, call.message.message_id, reply_markup=create_control_buttons(script_owner_id, file_name, True))
            except: pass
            return
        bot.answer_callback_query(call.id, f"Starting {file_name}...")
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else: bot.send_message(chat_id_for_reply, f"Unknown file type."); return
        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_icon = '🟢 Running' if is_now_running else '⏳ Starting...'
        try:
            edit_with_link_button(
                chat_id_for_reply, call.message.message_id,
                f"{BOT_NAME}\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"⚙️ `{file_name}` ({file_type})\n"
                f"🆔 User: `{script_owner_id}`\n"
                f"📊 Status: {status_icon}\n"
                f"━━━━━━━━━━━━━━━━━━",
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e): raise
    except (ValueError, IndexError): bot.answer_callback_query(call.id, "Error.", show_alert=True)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True); bot.answer_callback_query(call.id, "Error.", show_alert=True)

def stop_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "Permission denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "File not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1]
        script_key = f"{script_owner_id}_{file_name}"
        if not is_bot_running(script_owner_id, file_name):
            bot.answer_callback_query(call.id, f"Already stopped.", show_alert=True)
            try: edit_with_link_button(chat_id_for_reply, call.message.message_id,
                f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n⚙️ `{file_name}` ({file_type})\n🆔 User: `{script_owner_id}`\n📊 Status: 🔴 Stopped\n━━━━━━━━━━━━━━━━━━",
                reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown')
            except: pass
            return
        bot.answer_callback_query(call.id, f"Stopping {file_name}...")
        process_info = bot_scripts.get(script_key)
        if process_info:
            kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
        try:
            edit_with_link_button(chat_id_for_reply, call.message.message_id,
                f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n⚙️ `{file_name}` ({file_type})\n🆔 User: `{script_owner_id}`\n📊 Status: 🔴 Stopped\n━━━━━━━━━━━━━━━━━━",
                reply_markup=create_control_buttons(script_owner_id, file_name, False), parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e): raise
    except (ValueError, IndexError): bot.answer_callback_query(call.id, "Error.", show_alert=True)
    except Exception as e: logger.error(f"Error: {e}", exc_info=True); bot.answer_callback_query(call.id, "Error.", show_alert=True)

def restart_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "Permission denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        file_info = next((f for f in user_files_list if f[0] == file_name), None)
        if not file_info:
            bot.answer_callback_query(call.id, "File not found.", show_alert=True); check_files_callback(call); return
        file_type = file_info[1]; user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name); script_key = f"{script_owner_id}_{file_name}"
        if not os.path.exists(file_path):
            bot.answer_callback_query(call.id, f"File missing!", show_alert=True)
            remove_user_file_db(script_owner_id, file_name)
            if script_key in bot_scripts: del bot_scripts[script_key]
            check_files_callback(call); return
        bot.answer_callback_query(call.id, f"Restarting {file_name}...")
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info: kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
            time.sleep(1.5)
        if file_type == 'py':
            threading.Thread(target=run_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        elif file_type == 'js':
            threading.Thread(target=run_js_script, args=(file_path, script_owner_id, user_folder, file_name, call.message)).start()
        else: bot.send_message(chat_id_for_reply, f"Unknown type."); return
        time.sleep(1.5)
        is_now_running = is_bot_running(script_owner_id, file_name)
        status_icon = '🟢 Running' if is_now_running else '⏳ Starting...'
        try:
            edit_with_link_button(chat_id_for_reply, call.message.message_id,
                f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n⚙️ `{file_name}` ({file_type})\n🆔 User: `{script_owner_id}`\n📊 Status: {status_icon}\n━━━━━━━━━━━━━━━━━━",
                reply_markup=create_control_buttons(script_owner_id, file_name, is_now_running), parse_mode='Markdown')
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e): raise
    except (ValueError, IndexError): bot.answer_callback_query(call.id, "Error.", show_alert=True)
    except Exception as e: logger.error(f"Error: {e}", exc_info=True); bot.answer_callback_query(call.id, "Error.", show_alert=True)

def delete_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "Permission denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "File not found.", show_alert=True); check_files_callback(call); return
        bot.answer_callback_query(call.id, f"Deleting {file_name}...")
        script_key = f"{script_owner_id}_{file_name}"
        if is_bot_running(script_owner_id, file_name):
            process_info = bot_scripts.get(script_key)
            if process_info: kill_process_tree(process_info)
            if script_key in bot_scripts: del bot_scripts[script_key]
            time.sleep(0.5)
        user_folder = get_user_folder(script_owner_id)
        file_path = os.path.join(user_folder, file_name)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass
        if os.path.exists(log_path):
            try: os.remove(log_path)
            except: pass
        remove_user_file_db(script_owner_id, file_name)
        try:
            markup_del = types.InlineKeyboardMarkup()
            markup_del.add(types.InlineKeyboardButton(MAIN_LINK_TEXT, url=MAIN_LINK_URL))
            markup_del.add(types.InlineKeyboardButton("🔙 Back", callback_data='back_to_main'))
            bot.edit_message_text(f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n🗑️ `{file_name}` deleted!\n━━━━━━━━━━━━━━━━━━", chat_id_for_reply, call.message.message_id, reply_markup=markup_del, parse_mode='Markdown')
        except:
            bot.send_message(chat_id_for_reply, f"🗑️ `{file_name}` deleted.", parse_mode='Markdown')
    except (ValueError, IndexError): bot.answer_callback_query(call.id, "Error.", show_alert=True)
    except Exception as e: logger.error(f"Error: {e}", exc_info=True); bot.answer_callback_query(call.id, "Error.", show_alert=True)

def logs_bot_callback(call):
    try:
        _, script_owner_id_str, file_name = call.data.split('_', 2)
        script_owner_id = int(script_owner_id_str)
        requesting_user_id = call.from_user.id
        chat_id_for_reply = call.message.chat.id
        if not (requesting_user_id == script_owner_id or requesting_user_id in admin_ids):
            bot.answer_callback_query(call.id, "Permission denied.", show_alert=True); return
        user_files_list = user_files.get(script_owner_id, [])
        if not any(f[0] == file_name for f in user_files_list):
            bot.answer_callback_query(call.id, "File not found.", show_alert=True); check_files_callback(call); return
        user_folder = get_user_folder(script_owner_id)
        log_path = os.path.join(user_folder, f"{os.path.splitext(file_name)[0]}.log")
        if not os.path.exists(log_path):
            bot.answer_callback_query(call.id, f"No logs.", show_alert=True); return
        bot.answer_callback_query(call.id)
        try:
            log_content = ""; file_size = os.path.getsize(log_path)
            max_log_kb = 100; max_tg_msg = 4096
            if file_size == 0: log_content = "(Log empty)"
            elif file_size > max_log_kb * 1024:
                with open(log_path, 'rb') as f: f.seek(-max_log_kb * 1024, os.SEEK_END); log_bytes = f.read()
                log_content = f"(Last {max_log_kb} KB)\n...\n" + log_bytes.decode('utf-8', errors='ignore')
            else:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f: log_content = f.read()
            if len(log_content) > max_tg_msg:
                log_content = log_content[-max_tg_msg:]
                first_nl = log_content.find('\n')
                if first_nl != -1: log_content = "...\n" + log_content[first_nl+1:]
            if not log_content.strip(): log_content = "(No content)"
            bot.send_message(chat_id_for_reply, f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n📜 Logs: `{file_name}`\n━━━━━━━━━━━━━━━━━━\n```\n{log_content}\n```", parse_mode='Markdown')
        except: bot.send_message(chat_id_for_reply, f"❌ Error reading log.")
    except (ValueError, IndexError): bot.answer_callback_query(call.id, "Error.", show_alert=True)
    except Exception as e: logger.error(f"Error: {e}", exc_info=True); bot.answer_callback_query(call.id, "Error.", show_alert=True)

def speed_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    start_cb_ping_time = time.time()
    try:
        bot.edit_message_text(f"{BOT_NAME}\n\n⚡ Testing speed...", chat_id, call.message.message_id)
        bot.send_chat_action(chat_id, 'typing')
        response_time = round((time.time() - start_cb_ping_time) * 1000, 2)
        status = "🔓 Unlocked" if not bot_locked else "🔒 Locked"
        if user_id == OWNER_ID: user_level = "👑 Owner"
        elif user_id in admin_ids: user_level = "🛡️ Admin"
        elif user_id in user_subscriptions and user_subscriptions[user_id].get('expiry', datetime.min) > datetime.now(): user_level = "⭐ Premium"
        else: user_level = "🆓 Free User"
        bot.answer_callback_query(call.id)
        edit_with_link_button(chat_id, call.message.message_id,
            f"{BOT_NAME}\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Speed & Status\n\n"
            f"⏱️ Response: {response_time} ms\n"
            f"🚦 Status: {status}\n"
            f"👤 Level: {user_level}\n"
            f"━━━━━━━━━━━━━━━━━━",
            reply_markup=create_main_menu_inline(user_id))
    except Exception as e:
        bot.answer_callback_query(call.id, "Error.", show_alert=True)
        try: edit_with_link_button(chat_id, call.message.message_id, f"{BOT_NAME}\n\nMain Menu", reply_markup=create_main_menu_inline(user_id))
        except: pass

def back_to_main_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    file_limit = get_user_file_limit(user_id)
    current_files = get_user_file_count(user_id)
    limit_str = str(file_limit) if file_limit != float('inf') else "∞"
    if user_id == OWNER_ID: user_status = "👑 Owner"
    elif user_id in admin_ids: user_status = "🛡️ Admin"
    elif user_id in user_subscriptions:
        expiry_date = user_subscriptions[user_id].get('expiry')
        if expiry_date and expiry_date > datetime.now():
            user_status = "⭐ Premium"; days_left = (expiry_date - datetime.now()).days
        else: user_status = "🆓 Free (Expired)"
    else: user_status = "🆓 Free User"
    main_menu_text = (f"{BOT_NAME}\n"
                      f"━━━━━━━━━━━━━━━━━━\n\n"
                      f"✨ Welcome, {call.from_user.first_name}!\n\n"
                      f"🆔 User ID: `{user_id}`\n"
                      f"🔰 Status: {user_status}\n"
                      f"📂 Files: {current_files} / {limit_str}\n"
                      f"━━━━━━━━━━━━━━━━━━")
    try:
        bot.answer_callback_query(call.id)
        edit_with_link_button(chat_id, call.message.message_id, main_menu_text,
                              reply_markup=create_main_menu_inline(user_id), parse_mode='Markdown')
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e): logger.error(f"API error: {e}")
    except Exception as e: logger.error(f"Error: {e}", exc_info=True)

# --- Admin Callback Implementations ---
def subscription_management_callback(call):
    bot.answer_callback_query(call.id)
    try: edit_with_link_button(call.message.chat.id, call.message.message_id, f"{BOT_NAME}\n\n━━━━━━━━━━━━━━━━━━\n💳 Subscription Management:", reply_markup=create_subscription_menu())
    except: pass

def stats_callback(call):
    bot.answer_callback_query(call.id)
    _logic_statistics(call.message)
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except: pass

def lock_bot_callback(call):
    global bot_locked; bot_locked = True
    bot.answer_callback_query(call.id, "Bot locked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except: pass

def unlock_bot_callback(call):
    global bot_locked; bot_locked = False
    bot.answer_callback_query(call.id, "Bot unlocked.")
    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=create_main_menu_inline(call.from_user.id))
    except: pass

def run_all_scripts_callback(call): _logic_run_all_scripts(call)

def broadcast_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Send broadcast message.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    user_id = message.from_user.id
    if user_id not in admin_ids: bot.reply_to(message, "Not authorized."); return
    if message.text and message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    broadcast_content = message.text
    if not broadcast_content and not (message.photo or message.video or message.document):
        bot.reply_to(message, "Cannot broadcast empty message. Send text or /cancel.")
        msg = bot.send_message(message.chat.id, "Send broadcast message or /cancel.")
        bot.register_next_step_handler(msg, process_broadcast_message)
        return
    target_count = len(active_users)
    markup = types.InlineKeyboardMarkup()
    markup.row(types.InlineKeyboardButton("Confirm & Send", callback_data=f"confirm_broadcast_{message.message_id}"),
               types.InlineKeyboardButton("Cancel", callback_data="cancel_broadcast"))
    preview_text = broadcast_content[:1000].strip() if broadcast_content else "(Media message)"
    bot.reply_to(message, f"Confirm Broadcast:\n\n{preview_text}\n\nTo {target_count} users?", reply_markup=markup)

def handle_confirm_broadcast(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    if user_id not in admin_ids: bot.answer_callback_query(call.id, "Admin only.", show_alert=True); return
    try:
        original_message = call.message.reply_to_message
        if not original_message: raise ValueError("Could not retrieve message.")
        broadcast_text = original_message.text
        broadcast_photo_id = original_message.photo[-1].file_id if original_message.photo else None
        broadcast_video_id = original_message.video.file_id if original_message.video else None
        if not broadcast_text and not broadcast_photo_id and not broadcast_video_id:
            raise ValueError("No content for broadcast.")
        bot.answer_callback_query(call.id, "Starting broadcast...")
        bot.edit_message_text(f"Broadcasting to {len(active_users)} users...", chat_id, call.message.message_id, reply_markup=None)
        thread = threading.Thread(target=execute_broadcast, args=(broadcast_text, broadcast_photo_id, broadcast_video_id,
            original_message.caption if (broadcast_photo_id or broadcast_video_id) else None, chat_id))
        thread.start()
    except ValueError as ve:
        bot.edit_message_text(f"Error: {ve}", chat_id, call.message.message_id, reply_markup=None)
    except Exception as e:
        bot.edit_message_text("Error.", chat_id, call.message.message_id, reply_markup=None)

def handle_cancel_broadcast(call):
    bot.answer_callback_query(call.id, "Cancelled.")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    if call.message.reply_to_message:
        try: bot.delete_message(call.message.chat.id, call.message.reply_to_message.message_id)
        except: pass

def execute_broadcast(broadcast_text, photo_id, video_id, caption, admin_chat_id):
    sent_count = 0; failed_count = 0; blocked_count = 0
    users_to_broadcast = list(active_users); total_users = len(users_to_broadcast)
    batch_size = 25; delay_batches = 1.5
    for i, user_id_bc in enumerate(users_to_broadcast):
        try:
            if broadcast_text: bot.send_message(user_id_bc, broadcast_text)
            elif photo_id: bot.send_photo(user_id_bc, photo_id, caption=caption)
            elif video_id: bot.send_video(user_id_bc, video_id, caption=caption)
            sent_count += 1
        except telebot.apihelper.ApiTelegramException as e:
            err_desc = str(e).lower()
            if any(s in err_desc for s in ["bot was blocked", "user is deactivated", "chat not found"]): blocked_count += 1
            elif "flood control" in err_desc or "too many requests" in err_desc:
                retry_after = 5; match = re.search(r"retry after (\d+)", err_desc)
                if match: retry_after = int(match.group(1)) + 1
                time.sleep(retry_after)
                try:
                    if broadcast_text: bot.send_message(user_id_bc, broadcast_text)
                    elif photo_id: bot.send_photo(user_id_bc, photo_id, caption=caption)
                    elif video_id: bot.send_video(user_id_bc, video_id, caption=caption)
                    sent_count += 1
                except: failed_count += 1
            else: failed_count += 1
        except: failed_count += 1
        if (i + 1) % batch_size == 0 and i < total_users - 1: time.sleep(delay_batches)
        elif i % 5 == 0: time.sleep(0.2)
    result_msg = (f"Broadcast Complete!\n\nSent: {sent_count}\nFailed: {failed_count}\n"
                  f"Blocked: {blocked_count}\nTargets: {total_users}")
    try: bot.send_message(admin_chat_id, result_msg)
    except: pass

def admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    try: edit_with_link_button(call.message.chat.id, call.message.message_id, f"{BOT_NAME}\n\n👑 Admin Panel", reply_markup=create_admin_panel())
    except: pass

def add_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"{BOT_NAME}\n\n👑 Enter User ID to promote.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_admin_id)

def process_add_admin_id(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id <= 0: raise ValueError("ID must be positive")
        if new_admin_id == OWNER_ID: bot.reply_to(message, "Owner is already Owner."); return
        if new_admin_id in admin_ids: bot.reply_to(message, f"Already Admin."); return
        add_admin_db(new_admin_id)
        bot.reply_to(message, f"User `{new_admin_id}` promoted to Admin.")
        try: bot.send_message(new_admin_id, "You are now an Admin.")
        except: pass
    except ValueError:
        bot.reply_to(message, "Invalid ID. Send numerical ID or /cancel.")
        msg = bot.send_message(message.chat.id, "Enter User ID or /cancel.")
        bot.register_next_step_handler(msg, process_add_admin_id)
    except Exception as e: bot.reply_to(message, "Error.")

def remove_admin_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter Admin ID to remove.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_admin_id)

def process_remove_admin_id(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "Owner only."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        admin_id_remove = int(message.text.strip())
        if admin_id_remove <= 0: raise ValueError("ID must be positive")
        if admin_id_remove == OWNER_ID: bot.reply_to(message, "Cannot remove self."); return
        if admin_id_remove not in admin_ids: bot.reply_to(message, f"Not Admin."); return
        if remove_admin_db(admin_id_remove):
            bot.reply_to(message, f"Admin `{admin_id_remove}` removed.")
            try: bot.send_message(admin_id_remove, "You are no longer an Admin.")
            except: pass
        else: bot.reply_to(message, f"Failed to remove.")
    except ValueError:
        bot.reply_to(message, "Invalid ID or /cancel.")
        msg = bot.send_message(message.chat.id, "Enter Admin ID or /cancel.")
        bot.register_next_step_handler(msg, process_remove_admin_id)
    except Exception as e: bot.reply_to(message, "Error.")

def list_admins_callback(call):
    bot.answer_callback_query(call.id)
    try:
        admin_list_str = "\n".join(f"• `{aid}` {'👑' if aid == OWNER_ID else ''}" for aid in sorted(list(admin_ids)))
        edit_with_link_button(call.message.chat.id, call.message.message_id, f"{BOT_NAME}\n\n👑 Admins\n\n{admin_list_str}", reply_markup=create_admin_panel(), parse_mode='Markdown')
    except: pass

def add_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, f"{BOT_NAME}\n\n💳 Enter User ID & days (e.g., `12345678 30`).\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_add_subscription_details)

def process_add_subscription_details(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        parts = message.text.split()
        if len(parts) != 2: raise ValueError("Format: ID days")
        sub_user_id = int(parts[0].strip()); days = int(parts[1].strip())
        if sub_user_id <= 0 or days <= 0: raise ValueError("Must be positive")
        current_expiry = user_subscriptions.get(sub_user_id, {}).get('expiry')
        start_date = datetime.now()
        if current_expiry and current_expiry > start_date: start_date = current_expiry
        new_expiry = start_date + timedelta(days=days)
        save_subscription(sub_user_id, new_expiry)
        bot.reply_to(message, f"Sub for `{sub_user_id}` extended by {days} days.\nNew expiry: {new_expiry:%Y-%m-%d}")
        try: bot.send_message(sub_user_id, f"Your subscription has been extended! Expires: {new_expiry:%Y-%m-%d}")
        except: pass
    except ValueError as e:
        bot.reply_to(message, f"Invalid: {e}. Format: `ID days` or /cancel.")
        msg = bot.send_message(message.chat.id, "Enter User ID & days, or /cancel.")
        bot.register_next_step_handler(msg, process_add_subscription_details)
    except Exception as e: bot.reply_to(message, "Error.")

def remove_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID to remove sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_remove_subscription_id)

def process_remove_subscription_id(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        sub_user_id = int(message.text.strip())
        if sub_user_id <= 0: raise ValueError("ID must be positive")
        if sub_user_id not in user_subscriptions:
            bot.reply_to(message, f"No active sub."); return
        remove_subscription_db(sub_user_id)
        bot.reply_to(message, f"Sub for `{sub_user_id}` removed.")
        try: bot.send_message(sub_user_id, "Your subscription has been removed.")
        except: pass
    except ValueError:
        bot.reply_to(message, "Invalid ID or /cancel.")
        msg = bot.send_message(message.chat.id, "Enter User ID or /cancel.")
        bot.register_next_step_handler(msg, process_remove_subscription_id)
    except Exception as e: bot.reply_to(message, "Error.")

def check_subscription_init_callback(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Enter User ID to check sub.\n/cancel to abort.")
    bot.register_next_step_handler(msg, process_check_subscription_id)

def process_check_subscription_id(message):
    if message.from_user.id not in admin_ids: bot.reply_to(message, "Not authorized."); return
    if message.text.lower() == '/cancel': bot.reply_to(message, "Cancelled."); return
    try:
        sub_user_id = int(message.text.strip())
        if sub_user_id <= 0: raise ValueError("ID must be positive")
        if sub_user_id in user_subscriptions:
            expiry_dt = user_subscriptions[sub_user_id].get('expiry')
            if expiry_dt:
                if expiry_dt > datetime.now():
                    days_left = (expiry_dt - datetime.now()).days
                    bot.reply_to(message, f"Active sub.\nExpires: {expiry_dt:%Y-%m-%d %H:%M:%S} ({days_left} days left)")
                else:
                    bot.reply_to(message, f"Expired sub (Was: {expiry_dt:%Y-%m-%d %H:%M:%S})")
                    remove_subscription_db(sub_user_id)
            else: bot.reply_to(message, f"Expiry missing. Re-add.")
        else: bot.reply_to(message, f"No sub record.")
    except ValueError:
        bot.reply_to(message, "Invalid ID or /cancel.")
        msg = bot.send_message(message.chat.id, "Enter User ID or /cancel.")
        bot.register_next_step_handler(msg, process_check_subscription_id)
    except Exception as e: bot.reply_to(message, "Error.")

# --- Cleanup ---
def cleanup():
    logger.warning("Shutdown. Cleaning up processes...")
    script_keys_to_stop = list(bot_scripts.keys())
    if not script_keys_to_stop: return
    for key in script_keys_to_stop:
        if key in bot_scripts: kill_process_tree(bot_scripts[key])
atexit.register(cleanup)

# --- Main ---
if __name__ == '__main__':
    logger.info("="*40 + "\nBot Starting...\n" + f"Python: {sys.version.split()[0]}\n" +
                f"Base Dir: {BASE_DIR}\n" + f"Owner ID: {OWNER_ID}\n" + "="*40)
    keep_alive()
    logger.info("Starting polling...")
    while True:
        try:
            bot.infinity_polling(logger_level=logging.INFO, timeout=60, long_polling_timeout=30)
        except requests.exceptions.ReadTimeout: time.sleep(5)
        except requests.exceptions.ConnectionError: time.sleep(15)
        except Exception as e:
            logger.critical(f"Polling error: {e}", exc_info=True); time.sleep(30)
        finally: time.sleep(1)
