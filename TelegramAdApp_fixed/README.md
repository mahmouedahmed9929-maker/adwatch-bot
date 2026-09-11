# AdWatch — تطبيق تليجرام لمشاهدة الإعلانات

## 🔧 الإصلاحات في النسخة دي (سبب مشكلة "تم رفض الوصول")

1. **التوكن كان مكتوب placeholder والكود مش بيقرا من Environment Variables** ← أصلحناه: `BOT_TOKEN` و `APP_URL` بيقروا من env.
2. **رابط التطبيق كان ثابت `https://your-domain.com` في 3 أماكن** ← دلوقتي `app.js` بيستخدم مسار نسبي `/api` وبوت تليجرام بيبني الرابط من الدومين نفسه تلقائياً.
3. **اضفنا `/health`** للتأكد إن السيرفر شغال والتوكن متظبط.

## 🚀 النشر على Render

1. ارفع الملفات على GitHub
2. Render → New → Web Service → اربط الـ repo
3. أضف Environment Variables:
   - `BOT_TOKEN` = التوكن الجديد من BotFather
   - `APP_URL` = رابط Render بتاعك (مثال: `https://adwatch-bot.onrender.com`)
4. Deploy
5. بعد ما يخلص، افتح: `https://your-app.onrender.com/set_webhook`
   - لازم يرجعلك: `{"ok": true, "result": true, "description": "Webhook was set"}`
6. افتح `/health` — تأكد `bot_configured: true`
7. في BotFather: `/mybots` → Menu Button → حط نفس رابط Render
8. اكتب /start للبوت → اضغط "🚀 فتح التطبيق" → جرّب

## 🖥️ تشغيل محلي للاختبار

```bash
pip install -r requirements.txt
export BOT_TOKEN="توكنك"
python bot.py
```

وفي تيرمنال تاني:
```bash
ngrok http 5000
```
وخد رابط ngrok وحطه في `APP_URL` وفي BotFather.

## ⚠️ ملاحظة مهمة

`users.json` بيتمسح على Render مع كل redeploy. للإنتاج استخدم PostgreSQL.

## 🔑 تذكير

**التوكن اللي اتبعت في الشات اتكشف — اعمل /revoke في BotFather فوراً واستخدم التوكن الجديد.**
