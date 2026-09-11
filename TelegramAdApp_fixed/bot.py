import os
import json
import threading
from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__, static_folder='static')

# ============================================
# ⚙️ الإعدادات — اقرأ من متغيرات البيئة أولاً
# (على Render: أضف BOT_TOKEN و APP_URL في Environment Variables)
# محلياً: ممكن تحطهم في الكود هنا كاحتياطي
# ============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# رابط الموقع العام — على Render خده من: https://your-service.onrender.com
APP_URL = os.environ.get("APP_URL", "").rstrip("/")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# قاعدة بيانات بسيطة (JSON file)
DB_FILE = os.environ.get("DB_FILE", "users.json")
db_lock = threading.Lock()

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

def save_db(db):
    with db_lock:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)

def get_user(user_id):
    with db_lock:
        db = load_db()
        user_id = str(user_id)
        if user_id not in db:
            db[user_id] = {
                "points": 0,
                "ads_watched": 0,
                "referral_code": str(user_id),
                "referred_by": None,
                "daily_tasks": {
                    "ads": 0,
                    "last_reset": ""
                }
            }
            save_db(db)
        return db[user_id]

def update_user(user_id, data):
    with db_lock:
        db = load_db()
        db[str(user_id)] = data
        save_db(db)

# ========== WEB APP ENDPOINTS ==========

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/health")
def health():
    """للتحقق إن السيرفر شغال"""
    return jsonify({
        "ok": True,
        "bot_configured": BOT_TOKEN != "YOUR_BOT_TOKEN_HERE",
        "app_url": APP_URL or "NOT SET"
    })

@app.route("/api/config")
def api_config():
    """إعدادات يحتاجها التطبيق (رابط API نفسه + اسم البوت)"""
    return jsonify({"api_url": "/api"})

@app.route("/api/user/<user_id>")
def get_user_data(user_id):
    user = get_user(user_id)
    return jsonify(user)

@app.route("/api/watch_ad", methods=["POST"])
def watch_ad():
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id", ""))
    if not user_id:
        return jsonify({"success": False, "error": "مفيش user_id"}), 400
    user = get_user(user_id)

    # مكافأة مشاهدة الإعلان
    user["points"] += 10
    user["ads_watched"] += 1
    user["daily_tasks"]["ads"] += 1

    update_user(user_id, user)
    return jsonify({"success": True, "points": user["points"], "reward": 10})

@app.route("/api/referral", methods=["POST"])
def use_referral():
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id", ""))
    code = str(data.get("code", "")).strip()
    if not user_id or not code:
        return jsonify({"success": False, "error": "بيانات ناقصة"}), 400

    with db_lock:
        db = load_db()
        user = db.get(str(user_id)) or get_user(user_id)

        if code == user["referral_code"]:
            return jsonify({"success": False, "error": "لا يمكنك استخدام كودك"})

        if user.get("referred_by"):
            return jsonify({"success": False, "error": "استخدمت كود من قبل"})

        # البحث عن صاحب الكود
        for uid, udata in db.items():
            if udata.get("referral_code") == code:
                user["points"] += 100
                user["referred_by"] = code
                udata["points"] = udata.get("points", 0) + 50
                db[str(user_id)] = user
                db[uid] = udata
                save_db(db)
                return jsonify({"success": True, "points": user["points"], "reward": 100})

    return jsonify({"success": False, "error": "كود غير صحيح"})

# ========== TELEGRAM BOT WEBHOOK ==========

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if text.startswith("/start"):
            user = get_user(user_id)
            welcome = f"""🎉 أهلاً بيك في AdWatch!

💰 نقاطك: {user['points']}
📺 إعلانات شاهدتها: {user['ads_watched']}
👥 كود دعوتك: `{user['referral_code']}`

اضغط الزر تحت لفتح التطبيق 👇"""

            # ✅ بناء رابط التطبيق من نفس الدومين — مفيش حاجة ثابتة
            webapp_url = APP_URL or request.host_url.rstrip("/")

            keyboard = {
                "inline_keyboard": [[
                    {
                        "text": "🚀 فتح التطبيق",
                        "web_app": {"url": webapp_url}
                    }
                ]]
            }
            send_message(chat_id, welcome, keyboard)

    return "OK", 200

def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)

    try:
        requests.post(f"{BASE_URL}/sendMessage", json=payload, timeout=10)
    except requests.RequestException:
        pass

# ========== SET WEBHOOK ==========
@app.route("/set_webhook")
def set_webhook():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return jsonify({
            "ok": False,
            "error": "التوكن مش متظبط! ضيف BOT_TOKEN في Environment Variables"
        }), 400

    # ✅ استخدم نفس الدومين اللي الريكويست جاي منه
    webhook_url = f"{APP_URL or request.host_url.rstrip('/')}/webhook/{BOT_TOKEN}"
    r = requests.get(f"{BASE_URL}/setWebhook?url={webhook_url}", timeout=15)
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
