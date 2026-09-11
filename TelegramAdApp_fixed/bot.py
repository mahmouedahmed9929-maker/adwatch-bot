import os
import json
from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__, static_folder='static')

# ⚠️ غير دي لـ Token بتاعك من BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# قاعدة بيانات بسيطة (JSON file)
DB_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_user(user_id):
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
    db = load_db()
    db[str(user_id)] = data
    save_db(db)

# ========== WEB APP ENDPOINTS ==========

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/api/user/<user_id>")
def get_user_data(user_id):
    user = get_user(user_id)
    return jsonify(user)

@app.route("/api/watch_ad", methods=["POST"])
def watch_ad():
    data = request.json
    user_id = str(data.get("user_id"))
    user = get_user(user_id)

    # مكافأة مشاهدة الإعلان
    user["points"] += 10
    user["ads_watched"] += 1
    user["daily_tasks"]["ads"] += 1

    update_user(user_id, user)
    return jsonify({"success": True, "points": user["points"], "reward": 10})

@app.route("/api/referral", methods=["POST"])
def use_referral():
    data = request.json
    user_id = str(data.get("user_id"))
    code = str(data.get("code"))

    db = load_db()
    user = get_user(user_id)

    # التحقق من الكود
    if code == user["referral_code"]:
        return jsonify({"success": False, "error": "لا يمكنك استخدام كودك"})

    if user["referred_by"]:
        return jsonify({"success": False, "error": "استخدمت كود من قبل"})

    # البحث عن صاحب الكود
    for uid, udata in db.items():
        if udata["referral_code"] == code:
            # مكافأة للطرفين
            user["points"] += 100
            user["referred_by"] = code
            udata["points"] += 50
            update_user(user_id, user)
            update_user(uid, udata)
            return jsonify({"success": True, "points": user["points"], "reward": 100})

    return jsonify({"success": False, "error": "كود غير صحيح"})

# ========== TELEGRAM BOT WEBHOOK ==========

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = request.get_json()

    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        user_id = msg["from"]["id"]
        text = msg.get("text", "")

        if text == "/start":
            user = get_user(user_id)
            welcome = f"""🎉 أهلاً بيك في AdWatch!

💰 نقاطك: {user['points']}
📺 إعلانات شاهدتها: {user['ads_watched']}
👥 كود دعوتك: `{user['referral_code']}`

اضغط الزر تحت لفتح التطبيق 👇"""

            keyboard = {
                "inline_keyboard": [[
                    {
                        "text": "🚀 فتح التطبيق",
                        "web_app": {"url": "https://your-domain.com"}
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

    requests.post(f"{BASE_URL}/sendMessage", json=payload)

# ========== SET WEBHOOK ==========
@app.route("/set_webhook")
def set_webhook():
    # غير الرابط لـ domain بتاعك
    webhook_url = f"https://your-domain.com/webhook/{BOT_TOKEN}"
    r = requests.get(f"{BASE_URL}/setWebhook?url={webhook_url}")
    return r.json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
  
