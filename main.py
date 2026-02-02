import threading
from bot import run_bot

# ... (keep existing imports)
import os
import json
import logging
import requests
import random
import uuid
import time
import hashlib
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from functools import wraps

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IG_Report_API")

app = Flask(__name__)
API_DB_FILE = "api_keys.json"
CREDIT = "@PR_Bot_Services"

# Updated device info for 2026
DEVICE_PRESETS = [
    {
        "model": "SM-S918B",
        "manufacturer": "samsung",
        "android_version": "33",
        "dpi": "480dpi",
        "resolution": "1080x2400",
        "cpu": "qcom",
        "app_version": "275.0.0.27.98"
    },
    {
        "model": "Pixel 8 Pro",
        "manufacturer": "Google",
        "android_version": "34",
        "dpi": "560dpi",
        "resolution": "1440x3088",
        "cpu": "tensor",
        "app_version": "275.0.0.27.98"
    },
    {
        "model": "2211133C",
        "manufacturer": "Xiaomi",
        "android_version": "32",
        "dpi": "440dpi",
        "resolution": "1080x2340",
        "cpu": "qcom",
        "app_version": "275.0.0.27.98"
    }
]

# Report types matching Instagram's current system
REPORT_TYPES = {
    'spam': {'reason_id': '1', 'tag': 'spam'},
    'harassment': {'reason_id': '2', 'tag': 'bullying'},
    'hate': {'reason_id': '5', 'tag': 'hate_speech'},
    'violence': {'reason_id': '4', 'tag': 'violence'},
    'nudity': {'reason_id': '3', 'tag': 'nudity'},
    'self_harm': {'reason_id': '6', 'tag': 'self_harm'},
    'scam': {'reason_id': '1', 'tag': 'scam'},
    'fake': {'reason_id': '7', 'tag': 'impersonation'},
    'underage': {'reason_id': '8', 'tag': 'underage'}
}

def error_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return jsonify({"status": "error", "message": str(e), "credit": CREDIT}), 500
    return wrapper

def load_apis():
    if os.path.exists(API_DB_FILE):
        try:
            with open(API_DB_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_apis(data):
    try:
        with open(API_DB_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

def get_device_headers(session_id):
    """Generate proper Instagram headers with device fingerprint"""
    device = random.choice(DEVICE_PRESETS)
    device_id = str(uuid.uuid4())
    android_id = f"android-{device_id[:16]}"
    
    return {
        'User-Agent': f"Instagram {device['app_version']} Android ({device['android_version']}/9; {device['dpi']}; {device['resolution']}; {device['manufacturer']}; {device['model']}; {device['model']}; {device['cpu']}; en_US; 458229257)",
        'X-IG-App-Locale': 'en_US',
        'X-IG-Device-Locale': 'en_US',
        'X-IG-Mapped-Locale': 'en_US',
        'X-Pigeon-Session-Id': f"UFS-{str(uuid.uuid4())[:8]}-0",
        'X-Pigeon-Rawclienttime': str(time.time()),
        'X-IG-Bandwidth-Speed-Kbps': str(random.randint(2000, 5000)),
        'X-IG-Bandwidth-TotalBytes-B': str(random.randint(5000000, 10000000)),
        'X-IG-Bandwidth-TotalTime-MS': str(random.randint(200, 500)),
        'X-Bloks-Version-Id': '8ca96ca267e30c02cf90888d91eeff09627f0e3fd2bd9df472278c9a6c022cbb',
        'X-IG-WWW-Claim': '0',
        'X-Bloks-Is-Layout-RTL': 'false',
        'X-IG-Device-ID': device_id,
        'X-IG-Family-Device-ID': str(uuid.uuid4()),
        'X-IG-Android-ID': android_id,
        'X-IG-Timezone-Offset': '19800',
        'X-IG-Connection-Type': 'WIFI',
        'X-IG-Capabilities': '3brTv10=',
        'X-IG-App-ID': '567067343352427',
        'X-FB-HTTP-Engine': 'Liger',
        'X-FB-Client-IP': 'True',
        'X-FB-Server-Cluster': 'True',
        'Cookie': f'sessionid={session_id}',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'gzip, deflate',
        'Host': 'i.instagram.com',
        'Connection': 'Keep-Alive'
    }

def extract_csrf_from_session(session_id):
    """Extract CSRF token from session ID - handles both encoded and decoded formats"""
    parts = session_id.split('%3A') if '%3A' in session_id else session_id.split(':')
    if len(parts) >= 3:
        return parts[2][:32]
    return session_id[:32]

def get_user_id_from_username(session_id, username):
    """Get Instagram user ID from username - improved method"""
    logger.info(f"Resolving username: {username}")
    logger.info(f"Session ID format: {session_id[:20]}...")
    
    csrf = extract_csrf_from_session(session_id)
    
    # Method 1: Mobile API with search endpoint
    try:
        headers = get_device_headers(session_id)
        url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
        
        resp = requests.get(url, headers=headers, timeout=15)
        logger.info(f"Mobile web_profile_info response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and 'user' in data['data']:
                user_id = str(data['data']['user']['id'])
                logger.info(f"Resolved via Mobile web_profile: {user_id}")
                return user_id
    except Exception as e:
        logger.warning(f"Mobile web_profile failed: {e}")
    
    # Method 2: Mobile usernameinfo endpoint
    try:
        headers = get_device_headers(session_id)
        url = f'https://i.instagram.com/api/v1/users/{username}/usernameinfo/'
        
        resp = requests.get(url, headers=headers, timeout=15)
        logger.info(f"Mobile usernameinfo response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            if 'user' in data and 'pk' in data['user']:
                user_id = str(data['user']['pk'])
                logger.info(f"Resolved via Mobile usernameinfo: {user_id}")
                return user_id
        else:
            logger.warning(f"Mobile usernameinfo body: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Mobile usernameinfo failed: {e}")
    
    # Method 3: Web API with proper headers
    try:
        time.sleep(1)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-IG-App-ID': '936619743392459',
            'X-ASBD-ID': '129477',
            'X-CSRFToken': csrf,
            'X-IG-WWW-Claim': 'hmac.AR3W0DThY2Mu5Fag4sW5u3RhaR0iFjP2xVD3nVnrJAqHJpo8',
            'Cookie': f'sessionid={session_id}; csrftoken={csrf}; ig_did={str(uuid.uuid4())}',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f'https://www.instagram.com/{username}/',
            'Origin': 'https://www.instagram.com'
        }
        
        url = f'https://www.instagram.com/api/v1/users/web_profile_info/?username={username}'
        resp = requests.get(url, headers=headers, timeout=15)
        
        logger.info(f"Web API response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and 'user' in data['data']:
                user_id = str(data['data']['user']['id'])
                logger.info(f"Resolved via Web API: {user_id}")
                return user_id
        else:
            logger.warning(f"Web API body: {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Web API failed: {e}")
    
    # Method 4: GraphQL query
    try:
        time.sleep(1)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'X-IG-App-ID': '936619743392459',
            'Cookie': f'sessionid={session_id}; csrftoken={csrf}',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        url = f'https://www.instagram.com/{username}/?__a=1&__d=dis'
        resp = requests.get(url, headers=headers, timeout=15)
        
        logger.info(f"GraphQL response: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            if 'graphql' in data and 'user' in data['graphql']:
                user_id = str(data['graphql']['user']['id'])
                logger.info(f"Resolved via GraphQL: {user_id}")
                return user_id
    except Exception as e:
        logger.warning(f"GraphQL failed: {e}")
    
    logger.error(f"Failed to resolve: {username}")
    return None

def send_report_to_instagram(session_id, user_id, report_type='spam'):
    """Send report using multiple methods"""
    report_info = REPORT_TYPES.get(report_type.lower(), REPORT_TYPES['spam'])
    logger.info(f"Sending report: {report_type} for user {user_id}")
    
    # Method 1: Mobile flag_user endpoint (Primary)
    try:
        headers = get_device_headers(session_id)
        
        data = {
            'user_id': str(user_id),
            'source_name': 'profile',
            'reason_id': report_info['reason_id'],
            'is_spam': 'true'
        }
        
        url = f'https://i.instagram.com/api/v1/users/{user_id}/flag_user/'
        resp = requests.post(url, headers=headers, data=data, timeout=20)
        
        logger.info(f"Mobile flag_user: {resp.status_code}")
        
        if resp.status_code in [200, 201]:
            logger.info("✓ Report sent via Mobile API")
            return {"success": True, "method": "mobile_api"}
    except Exception as e:
        logger.warning(f"Mobile method failed: {e}")
    
    # Method 2: Web report endpoint (Fallback)
    try:
        time.sleep(1)
        
        csrf = extract_csrf_from_session(session_id)
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-IG-App-ID': '936619743392459',
            'X-ASBD-ID': '129477',
            'X-CSRFToken': csrf,
            'X-Requested-With': 'XMLHttpRequest',
            'Cookie': f'sessionid={session_id}; csrftoken={csrf}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'https://www.instagram.com/',
            'Origin': 'https://www.instagram.com'
        }
        
        data = f'user_id={user_id}&source_name=profile&reason_id={report_info["reason_id"]}'
        
        url = 'https://www.instagram.com/users/report/'
        resp = requests.post(url, headers=headers, data=data, timeout=20)
        
        logger.info(f"Web report: {resp.status_code}")
        
        if resp.status_code in [200, 201]:
            logger.info("✓ Report sent via Web API")
            return {"success": True, "method": "web_api"}
    except Exception as e:
        logger.warning(f"Web method failed: {e}")
    
    # Method 3: Bloks report (Final fallback)
    try:
        time.sleep(1)
        
        headers = get_device_headers(session_id)
        
        params = {
            "user_id": str(user_id),
            "source_name": "profile",
            "reason_id": report_info['reason_id']
        }
        
        data = f"params={json.dumps(params)}&bk_client_context=%7B%22bloks_version%22%3A%229fc6a7a4a577456e492c189810755fe22a6300efc23e4532268bca150fe3e27a%22%2C%22styles_id%22%3A%22instagram%22%7D&bloks_versioning_id=9fc6a7a4a577456e492c189810755fe22a6300efc23e4532268bca150fe3e27a"
        
        url = 'https://i.instagram.com/api/v1/bloks/apps/com.instagram.bloks.reporting.report/'
        resp = requests.post(url, headers=headers, data=data, timeout=20)
        
        logger.info(f"Bloks report: {resp.status_code}")
        
        if resp.status_code in [200, 201]:
            logger.info("✓ Report sent via Bloks API")
            return {"success": True, "method": "bloks_api"}
    except Exception as e:
        logger.warning(f"Bloks method failed: {e}")
    
    return {"success": False, "message": "All reporting methods failed"}

@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "name": "Instagram Report API",
        "version": "2.0",
        "endpoints": {
            "report": "/api/report?key=KEY&ses=SESSION&rep=TYPE&target=USERNAME&delay=SECONDS",
            "create_key": "/api/create_key?admin=PASS&expires_days=30",
            "check_key": "/api/check_key?key=KEY"
        },
        "report_types": list(REPORT_TYPES.keys()),
        "credit": CREDIT
    })

@app.route('/api/report')
@error_handler
def report():
    key = request.args.get('key', '').strip()
    session_id = request.args.get('ses', '').strip()
    report_type = request.args.get('rep', 'spam').strip().lower()
    target = request.args.get('target', '').strip().replace('@', '')
    delay = int(request.args.get('delay', 0))
    
    # Validate required params
    if not all([key, session_id, target]):
        return jsonify({
            "status": "error",
            "message": "Missing required parameters: key, ses, target",
            "credit": CREDIT
        }), 400
    
    # Validate API key
    apis = load_apis()
    if key not in apis:
        return jsonify({
            "status": "error",
            "message": "Invalid API key",
            "credit": CREDIT
        }), 401
    
    api_data = apis[key]
    
    # Check expiry
    try:
        if datetime.now() > datetime.fromisoformat(api_data['expires_at']):
            return jsonify({
                "status": "error",
                "message": "API key expired",
                "credit": CREDIT
            }), 403
    except:
        pass
    
    if not api_data.get('active', True):
        return jsonify({
            "status": "error",
            "message": "API key disabled",
            "credit": CREDIT
        }), 403
    
    # Validate report type
    if report_type not in REPORT_TYPES:
        return jsonify({
            "status": "error",
            "message": f"Invalid report type. Valid types: {list(REPORT_TYPES.keys())}",
            "credit": CREDIT
        }), 400
    
    # Apply delay
    if delay > 0:
        time.sleep(min(delay, 30))
    
    # Get target user ID
    user_id = get_user_id_from_username(session_id, target)
    if not user_id:
        return jsonify({
            "status": "error",
            "message": "Target user not found or invalid session",
            "credit": CREDIT
        }), 404
    
    # Send report
    result = send_report_to_instagram(session_id, user_id, report_type)
    
    if result['success']:
        # Update usage stats
        apis[key]['usage'] = apis[key].get('usage', 0) + 1
        apis[key]['last_used'] = datetime.now().isoformat()
        save_apis(apis)
        
        return jsonify({
            "status": "success",
            "message": "Successfully reported",
            "target": target,
            "user_id": user_id,
            "report_type": report_type,
            "method": result.get('method', 'unknown'),
            "credit": CREDIT
        })
    else:
        return jsonify({
            "status": "error",
            "message": result.get('message', 'Report failed'),
            "target": target,
            "credit": CREDIT
        }), 500

@app.route('/api/create_key')
@error_handler
def create_key():
    admin_pass = request.args.get('admin', '')
    expires_days = int(request.args.get('expires_days', 30))
    
    # Change this password!
    if admin_pass != 'pr_bot_admin_2026':
        return jsonify({
            "status": "error",
            "message": "Unauthorized",
            "credit": CREDIT
        }), 401
    
    new_key = str(uuid.uuid4()).replace('-', '')[:24]
    expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
    
    apis = load_apis()
    apis[new_key] = {
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at,
        "active": True,
        "usage": 0,
        "last_used": None
    }
    save_apis(apis)
    
    return jsonify({
        "status": "success",
        "api_key": new_key,
        "expires_at": expires_at,
        "expires_days": expires_days,
        "credit": CREDIT
    })

@app.route('/api/check_key')
@error_handler
def check_key():
    key = request.args.get('key', '')
    apis = load_apis()
    
    if key in apis:
        data = apis[key].copy()
        try:
            is_expired = datetime.now() > datetime.fromisoformat(data['expires_at'])
            data['is_expired'] = is_expired
        except:
            pass
        return jsonify({
            "status": "success",
            "data": data,
            "credit": CREDIT
        })
    
    return jsonify({
        "status": "error",
        "message": "Key not found",
        "credit": CREDIT
    }), 404

if __name__ == '__main__':
    print("=" * 70)
    print("  Instagram Report API v2.0 - Starting...")
    print("  " + CREDIT)
    print("=" * 70)
    print(f"\n  Available Report Types: {', '.join(REPORT_TYPES.keys())}")
    print("\n  Endpoints:")
    print("    POST /api/report - Submit report")
    print("    GET  /api/create_key - Generate API key")
    print("    GET  /api/check_key - Check key status")
    print("\n" + "=" * 70)
    
    # Start Telegram Bot in a background thread
    if os.getenv("BOT_TOKEN") and os.getenv("OWNER_ID"):
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        logger.info("Bot thread started")
    else:
        logger.warning("BOT_TOKEN or OWNER_ID not set, Telegram bot thread not started")
    
    # Using a slightly different port or just ensuring it's clean
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)