import os
import json
import random
import string
import logging
import platform
import psutil
from datetime import datetime, timedelta
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TelegramBot")

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

API_DB_FILE = "api_keys.json"
DOMAIN_FILE = "domain.json"
START_TIME = datetime.now()

def load_apis():
    try:
        if os.path.exists(API_DB_FILE):
            with open(API_DB_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load APIs: {e}")
    return {}

def save_apis(apis):
    try:
        with open(API_DB_FILE, 'w') as f:
            json.dump(apis, f, indent=2)
            return True
    except Exception as e:
        logger.error(f"Failed to save APIs: {e}")
        return False

def load_domain():
    try:
        if os.path.exists(DOMAIN_FILE):
            with open(DOMAIN_FILE, 'r') as f:
                data = json.load(f)
                return data.get('domain', '')
    except Exception as e:
        logger.error(f"Failed to load domain: {e}")
    return ''

def save_domain(domain):
    try:
        with open(DOMAIN_FILE, 'w') as f:
            json.dump({'domain': domain}, f)
            return True
    except Exception as e:
        logger.error(f"Failed to save domain: {e}")
        return False

def generate_api_key():
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"PR_{random_part}"

def run_bot():
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN not set, Telegram bot disabled")
        return
    if not OWNER_ID:
        logger.warning("OWNER_ID not set, Telegram bot disabled")
        return
    
    import telebot
    from telebot import types as telebot_types
    
    bot = telebot.TeleBot(BOT_TOKEN)
    
    def get_main_keyboard():
        markup = telebot_types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            telebot_types.InlineKeyboardButton("+ Create API", callback_data="create_api"),
            telebot_types.InlineKeyboardButton("All APIs", callback_data="all_apis")
        )
        markup.add(
            telebot_types.InlineKeyboardButton("Status", callback_data="status"),
            telebot_types.InlineKeyboardButton("Set Domain", callback_data="set_domain")
        )
        return markup

    @bot.message_handler(commands=['start'])
    def start(message):
        try:
            if message.from_user.id == OWNER_ID:
                text = """<b>Instagram Report API Panel</b>

Welcome! Use the buttons below to manage your APIs.

<b>Features:</b>
- Create unlimited APIs with custom validity
- Track API usage and status
- Set custom domain for API endpoints"""
                bot.send_message(message.chat.id, text, reply_markup=get_main_keyboard(), parse_mode='HTML')
            else:
                bot.send_message(message.chat.id, "<b>Access Denied</b>\n\nThis bot is for owner only!", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in start command: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "create_api")
    def create_api_callback(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            text = "<b>Create New API</b>\n\nEnter API name:"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
            bot.register_next_step_handler(call.message, process_api_name)
        except Exception as e:
            logger.error(f"Error in create_api_callback: {e}")

    def process_api_name(message):
        try:
            if message.from_user.id != OWNER_ID:
                return
            
            api_name = message.text.strip()
            if not api_name or api_name.startswith('/'):
                bot.send_message(message.chat.id, "Invalid name. Try again.", reply_markup=get_main_keyboard())
                return
            
            text = f"Name: <b>{api_name}</b>\n\n" \
                   "Enter validity period:\n" \
                   "- <code>1h</code> = 1 hour\n" \
                   "- <code>1d</code> = 1 day\n" \
                   "- <code>7d</code> = 7 days\n" \
                   "- <code>30d</code> = 30 days\n" \
                   "- <code>unlimited</code> = No expiry"
            
            msg = bot.send_message(message.chat.id, text, parse_mode='HTML')
            bot.register_next_step_handler(msg, lambda m: process_api_validity(m, api_name))
        except Exception as e:
            logger.error(f"Error in process_api_name: {e}")

    def process_api_validity(message, api_name):
        try:
            if message.from_user.id != OWNER_ID:
                return
            
            validity = message.text.strip().lower()
            
            if validity == 'unlimited':
                expires_at = datetime.now() + timedelta(days=36500)
                validity_text = "Unlimited"
            elif validity.endswith('h'):
                try:
                    hours = int(validity[:-1])
                    expires_at = datetime.now() + timedelta(hours=hours)
                    validity_text = f"{hours} hour(s)"
                except:
                    bot.send_message(message.chat.id, "Invalid format. Try again.", reply_markup=get_main_keyboard())
                    return
            elif validity.endswith('d'):
                try:
                    days = int(validity[:-1])
                    expires_at = datetime.now() + timedelta(days=days)
                    validity_text = f"{days} day(s)"
                except:
                    bot.send_message(message.chat.id, "Invalid format. Try again.", reply_markup=get_main_keyboard())
                    return
            else:
                bot.send_message(message.chat.id, "Invalid format. Use: 1h, 1d, 7d, 30d, or unlimited", reply_markup=get_main_keyboard())
                return
            
            api_key = generate_api_key()
            
            apis = load_apis()
            apis[api_key] = {
                'name': api_name,
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'active': True,
                'usage': 0,
                'last_used': None
            }
            save_apis(apis)
            
            domain = load_domain() or "https://your-domain.com"
            api_url = f"{domain}/api/report?key={{KEY}}&ses={{SESSION_ID}}&rep={{REPORT_TYPE}}&target={{TARGET_USERNAME}}&delay=5"
            
            text = f"""<b>API Created Successfully!</b>

<b>Name:</b> {api_name}
<b>Key:</b> <code>{api_key}</code>
<b>Validity:</b> {validity_text}
<b>Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M')}

<b>API URL Template:</b>
<code>{api_url}</code>

<b>Replace placeholders:</b>
- <code>{{KEY}}</code> -> <code>{api_key}</code>
- <code>{{SESSION_ID}}</code> -> Your Instagram session
- <code>{{REPORT_TYPE}}</code> -> spam/nudity/hate/violence/scam/bullying/fake
- <code>{{TARGET_USERNAME}}</code> -> Target Instagram username"""
            
            markup = telebot_types.InlineKeyboardMarkup()
            markup.add(telebot_types.InlineKeyboardButton("Back to Menu", callback_data="back_main"))
            
            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in process_api_validity: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "all_apis")
    def all_apis_callback(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            apis = load_apis()
            if not apis:
                bot.edit_message_text("<b>No APIs created yet.</b>", call.message.chat.id, call.message.message_id, 
                                     reply_markup=get_main_keyboard(), parse_mode='HTML')
                return
            
            markup = telebot_types.InlineKeyboardMarkup()
            for key, data in apis.items():
                markup.add(telebot_types.InlineKeyboardButton(
                    f"{data.get('name', 'Unnamed')} ({key})", 
                    callback_data=f"manage_{key}"
                ))
            markup.add(telebot_types.InlineKeyboardButton("Back", callback_data="back_main"))
            
            bot.edit_message_text("<b>Select API to Manage:</b>", call.message.chat.id, call.message.message_id, 
                                 reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in all_apis_callback: {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("manage_"))
    def manage_api(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            api_key = call.data[7:]
            apis = load_apis()
            
            if api_key not in apis:
                bot.edit_message_text("API not found.", call.message.chat.id, call.message.message_id, 
                                     reply_markup=get_main_keyboard())
                return
            
            data = apis[api_key]
            try:
                expires_at = datetime.fromisoformat(data['expires_at'])
                is_expired = datetime.now() > expires_at
            except:
                is_expired = False
                expires_at = datetime.now()
                
            status = "Expired" if is_expired else ("Active" if data.get('active', True) else "Disabled")
            
            text = f"""<b>Manage API: {data.get('name', 'Unnamed')}</b>

Key: <code>{api_key}</code>
Status: {status}
Usage: {data.get('usage', 0)} reports
Expires: {expires_at.strftime('%Y-%m-%d %H:%M')}"""

            markup = telebot_types.InlineKeyboardMarkup(row_width=2)
            
            active = data.get('active', True)
            toggle_text = "Disable" if active else "Enable"
            toggle_data = f"toggle_{api_key}"
            
            markup.add(
                telebot_types.InlineKeyboardButton(toggle_text, callback_data=toggle_data),
                telebot_types.InlineKeyboardButton("Delete", callback_data=f"del_{api_key}")
            )
            markup.add(
                telebot_types.InlineKeyboardButton("Edit Name", callback_data=f"edit_name_{api_key}"),
                telebot_types.InlineKeyboardButton("Back", callback_data="all_apis")
            )
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 reply_markup=markup, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in manage_api: {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
    def toggle_api(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            api_key = call.data[7:]
            apis = load_apis()
            
            if api_key in apis:
                apis[api_key]['active'] = not apis[api_key].get('active', True)
                save_apis(apis)
                manage_api(call)
            else:
                bot.answer_callback_query(call.id, "API not found.")
        except Exception as e:
            logger.error(f"Error in toggle_api: {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edit_name_"))
    def edit_name_start(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            api_key = call.data[10:]
            text = "Enter new name for the API:"
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
            bot.register_next_step_handler(call.message, lambda m: process_edit_name(m, api_key))
        except Exception as e:
            logger.error(f"Error in edit_name_start: {e}")

    def process_edit_name(message, api_key):
        try:
            if message.from_user.id != OWNER_ID:
                return
            
            new_name = message.text.strip()
            if not new_name or new_name.startswith('/'):
                bot.send_message(message.chat.id, "Invalid name.")
                return
            
            apis = load_apis()
            if api_key in apis:
                apis[api_key]['name'] = new_name
                save_apis(apis)
                bot.send_message(message.chat.id, f"API name updated to: <b>{new_name}</b>", 
                                reply_markup=get_main_keyboard(), parse_mode='HTML')
            else:
                bot.send_message(message.chat.id, "API not found.")
        except Exception as e:
            logger.error(f"Error in process_edit_name: {e}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
    def delete_api(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            api_key = call.data[4:]
            apis = load_apis()
            
            if api_key in apis:
                api_name = apis[api_key].get('name', 'Unnamed')
                del apis[api_key]
                save_apis(apis)
                bot.edit_message_text(f"API <b>{api_name}</b> (<code>{api_key}</code>) deleted!", 
                                     call.message.chat.id, call.message.message_id, 
                                     reply_markup=get_main_keyboard(), parse_mode='HTML')
            else:
                bot.edit_message_text("API not found.", call.message.chat.id, call.message.message_id, 
                                     reply_markup=get_main_keyboard())
        except Exception as e:
            logger.error(f"Error in delete_api: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "status")
    def status_callback(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            apis = load_apis()
            domain = load_domain() or "Not Set"
            
            total = len(apis)
            active = 0
            expired = 0
            total_usage = 0
            
            for a in apis.values():
                try:
                    exp = datetime.fromisoformat(a['expires_at'])
                    is_exp = datetime.now() > exp
                    if is_exp:
                        expired += 1
                    elif a.get('active', True):
                        active += 1
                except:
                    pass
                total_usage += a.get('usage', 0)
            
            uptime = datetime.now() - START_TIME
            uptime_str = str(uptime).split('.')[0]
            
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent
            
            text = f"""<b>System & API Status</b>

<b>Domain:</b> <code>{domain}</code>
<b>Uptime:</b> <code>{uptime_str}</code>

<b>API Statistics:</b>
Total APIs: <code>{total}</code>
Active: <code>{active}</code>
Expired: <code>{expired}</code>
Total Reports: <code>{total_usage}</code>

<b>System Info:</b>
CPU Usage: <code>{cpu_usage}%</code>
RAM Usage: <code>{ram_usage}%</code>
OS: <code>{platform.system()}</code>
Bot: <code>Online</code>

<b>Credits:</b> <code>@kissuHQ</code>"""
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 reply_markup=get_main_keyboard(), parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in status_callback: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "set_domain")
    def set_domain_callback(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            current_domain = load_domain()
            
            if current_domain:
                text = f"""<b>Domain already set!</b>

Current Domain: <code>{current_domain}</code>

Do you want to change it? If yes, please enter the <b>New Domain</b> (with https://).
Example: <code>https://api.example.com</code>

Otherwise, click <b>Back</b>."""
            else:
                text = """<b>Set Domain</b>

Enter your API domain (with https://):
Example: <code>https://myapi.example.com</code>"""
            
            markup = telebot_types.InlineKeyboardMarkup()
            markup.add(telebot_types.InlineKeyboardButton("Back", callback_data="back_main"))
            
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 reply_markup=markup, parse_mode='HTML')
            bot.register_next_step_handler(call.message, process_domain)
        except Exception as e:
            logger.error(f"Error in set_domain_callback: {e}")

    def process_domain(message):
        try:
            if message.from_user.id != OWNER_ID:
                return
            
            if message.text and message.text.startswith('/'):
                return

            domain = message.text.strip()
            
            if not domain.startswith('http'):
                bot.send_message(message.chat.id, 
                    "Invalid domain. Must start with http:// or https://", 
                    reply_markup=get_main_keyboard())
                return
            
            domain = domain.rstrip('/')
            save_domain(domain)
            
            bot.send_message(message.chat.id, 
                f"Domain successfully updated to: <code>{domain}</code>", 
                reply_markup=get_main_keyboard(), parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in process_domain: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "back_main")
    def back_main(call):
        try:
            if call.from_user.id != OWNER_ID:
                return
            
            text = """<b>Instagram Report API Panel</b>

Welcome! Use the buttons below to manage your APIs.

<b>Features:</b>
- Create unlimited APIs with custom validity
- Track API usage and status
- Set custom domain for API endpoints"""

            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, 
                                 reply_markup=get_main_keyboard(), parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error in back_main: {e}")

    try:
        logger.info("Telegram Bot polling started...")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")

if __name__ == "__main__":
    run_bot()
