// Telegram Web App SDK
let tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// بيانات المستخدم
let userId = null;
let userData = null;
let adTimer = null;

// ✅ مسار نسبي — يشتغل على أي دومين تلقائياً
const API_URL = "/api";

// تهيئة التطبيق
async function init() {
    try {
        // الحصول على بيانات المستخدم من Telegram
        if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
            userId = tg.initDataUnsafe.user.id;
        } else {
            // للاختبار بدون Telegram
            userId = "test_user_" + Math.floor(Math.random() * 100000);
        }

        // جلب بيانات المستخدم
        await loadUserData();

        // إخفاء التحميل وإظهار التطبيق
        document.getElementById('loading').classList.remove('active');
        document.getElementById('app').style.display = 'block';

        // تفعيل زر Telegram الرئيسي
        tg.MainButton.setText("🚀 شاهد إعلان");
        tg.MainButton.onClick(startAd);
        tg.MainButton.show();

    } catch (err) {
        console.error("Init error:", err);
        showToast("❌ خطأ في التحميل");
    }
}

// جلب بيانات المستخدم
async function loadUserData() {
    try {
        const res = await fetch(`${API_URL}/user/${userId}`);
        userData = await res.json();
        updateUI();
    } catch (err) {
        console.error("Load error:", err);
        // بيانات افتراضية
        userData = {
            points: 0,
            ads_watched: 0,
            referral_code: userId,
            daily_tasks: { ads: 0 }
        };
        updateUI();
    }
}

// تحديث الواجهة
function updateUI() {
    if (!userData) return;

    document.getElementById('points').textContent = userData.points || 0;
    document.getElementById('ads-count').textContent = userData.ads_watched || 0;
    document.getElementById('ref-code').textContent = userData.referral_code || userId;

    // تحديث المهمات
    const adsTask = document.getElementById('task-ads');
    if (userData.daily_tasks && userData.daily_tasks.ads >= 5) {
        adsTask.classList.add('completed');
        adsTask.querySelector('.task-reward').textContent = '✅';
    }

    // تحديث عدد المهمات المكتملة
    let completed = 0;
    if (userData.daily_tasks && userData.daily_tasks.ads >= 5) completed++;
    if (userData.referred_by) completed++;
    document.getElementById('tasks-count').textContent = `${completed}/3`;
}

// بدء مشاهدة الإعلان
function startAd() {
    const overlay = document.getElementById('ad-overlay');
    const timerEl = document.getElementById('ad-timer');
    const progressEl = document.getElementById('ad-progress');
    const btn = document.getElementById('watch-btn');

    btn.disabled = true;
    overlay.classList.add('active');

    let seconds = 15;
    timerEl.textContent = seconds;
    progressEl.style.width = '0%';

    // عداد تنازلي
    adTimer = setInterval(() => {
        seconds--;
        timerEl.textContent = seconds;
        progressEl.style.width = `${((15 - seconds) / 15) * 100}%`;

        if (seconds <= 0) {
            clearInterval(adTimer);
            finishAd();
        }
    }, 1000);
}

// إنهاء الإعلان
async function finishAd() {
    const overlay = document.getElementById('ad-overlay');
    const btn = document.getElementById('watch-btn');

    overlay.classList.remove('active');
    btn.disabled = false;

    try {
        const res = await fetch(`${API_URL}/watch_ad`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });

        const result = await res.json();
        if (result.success) {
            userData.points = result.points;
            userData.ads_watched = (userData.ads_watched || 0) + 1;
            if (userData.daily_tasks) {
                userData.daily_tasks.ads = (userData.daily_tasks.ads || 0) + 1;
            }
            updateUI();
            showToast(`🎉 +${result.reward} نقطة!`);

            // اهتزاز (لو متاح)
            if (tg.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
        }
    } catch (err) {
        console.error("Ad error:", err);
        // محاكاة لو السيرفر مش شغال
        userData.points = (userData.points || 0) + 10;
        userData.ads_watched = (userData.ads_watched || 0) + 1;
        updateUI();
        showToast("🎉 +10 نقاط! (وضع عدم الاتصال)");
    }
}

// نسخ الكود
function copyCode() {
    const code = document.getElementById('ref-code').textContent;
    navigator.clipboard.writeText(code).then(() => {
        showToast("📋 تم نسخ الكود!");
        if (tg.HapticFeedback) {
            tg.HapticFeedback.impactOccurred('light');
        }
    });
}

// إرسال كود الدعوة
async function submitRef() {
    const input = document.getElementById('ref-input');
    const code = input.value.trim();

    if (!code || code.length < 4) {
        showToast("❌ أدخل كود صحيح");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/referral`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, code: code })
        });

        const result = await res.json();
        if (result.success) {
            userData.points = result.points;
            userData.referred_by = code;
            updateUI();
            showToast(`🎉 +${result.reward} نقطة!`);
            input.value = '';
        } else {
            showToast("❌ " + (result.error || "كود غير صحيح"));
        }
    } catch (err) {
        showToast("❌ خطأ في الاتصال");
    }
}

// إظهار Toast
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

// مشاركة التطبيق
function shareApp() {
    const text = `🎉 انضم لـ AdWatch واكسب نقاط!\n\nكودي: ${userData.referral_code}\n\nاضغط للبدء:`;
    const url = `https://t.me/YOUR_BOT_USERNAME?start=${userData.referral_code}`;

    if (tg.openTelegramLink) {
        tg.openTelegramLink(url);
    } else {
        showToast("📤 تم نسخ الرابط!");
    }
}

// تشغيل
init();
          
