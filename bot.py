#صالح میرزایی و استاد محمد و داریوش تیم برنامه نویسی وی ای پی

"""
ربات جنگ جهانی - نسخه نهایی کامل
برای پیام‌رسان بله
"""

import os
import requests
import json
import sqlite3
import time
import random
import threading
from datetime import datetime, timedelta

# دریافت توکن‌ها از تنظیمات خود رایلی (Railway Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN", "1610685733:rWgWdD7Zyka0PdyDvqKtewTuqFRPRxsd7rM")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN", "توکن پرداخت")

BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
PAYMENT_TEST_TOKEN = "WALLET-TEST-1111111111111111"

# آیدی عددی ادمین اصلی (همیشه دسترسی کامل دارد)
MAIN_ADMIN_ID = 223726163

# کانال و گروه اجباری
FORCE_CHANNEL = "@Mr_TOMAS_CHANEL"
FORCE_GROUP = "@Mr_TOMAS_CHANEL"

# لیست کامل ۱۹۵ کشور
COUNTRIES = [
    "ایران", "آمریکا", "آلمان", "انگلیس", "فرانسه", "روسیه", "چین", "ژاپن",
    "کره جنوبی", "ترکیه", "عربستان", "امارات", "قطر", "مصر", "مراکش", "نیجریه",
    "برزیل", "آرژانتین", "مکزیک", "کانادا", "استرالیا", "هند", "پاکستان",
    "افغانستان", "عراق"
]

# اتصال به دیتابیس
def get_db():
    conn = sqlite3.connect("bale_bot.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # جدول کاربران
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        country TEXT,
        coins INTEGER DEFAULT 1000,
        diamonds INTEGER DEFAULT 10,
        wood INTEGER DEFAULT 100,
        iron INTEGER DEFAULT 50,
        oil INTEGER DEFAULT 20,
        army_level INTEGER DEFAULT 1,
        soldiers INTEGER DEFAULT 10,
        tanks INTEGER DEFAULT 0,
        jets INTEGER DEFAULT 0,
        shield_until TEXT,
        alliance_id INTEGER,
        is_admin INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0,
        last_daily TEXT,
        last_attack TEXT,
        last_mine TEXT,
        vip_until TEXT
    )
    """)
    
    # جدول اتحادها
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alliances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        creator_id INTEGER,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        wood_bank INTEGER DEFAULT 0,
        iron_bank INTEGER DEFAULT 0,
        oil_bank INTEGER DEFAULT 0,
        coins_bank INTEGER DEFAULT 0
    )
    """)
    
    # جدول بورس / سهام کشورها
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock_market (
        country TEXT PRIMARY KEY,
        base_price REAL,
        current_price REAL,
        last_change REAL
    )
    """)
    
    # جدول سبد سهام کاربران
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_stocks (
        user_id INTEGER,
        country TEXT,
        shares INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, country)
    )
    """)
    
    # جدول کارخانه‌ها
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS factories (
        user_id INTEGER PRIMARY KEY,
        wood_mill INTEGER DEFAULT 0,
        iron_mine INTEGER DEFAULT 0,
        oil_rig INTEGER DEFAULT 0,
        last_collect TEXT
    )
    """)

    conn.commit()
    
    # مقداردهی اولیه بورس
    cursor.execute("SELECT COUNT(*) FROM stock_market")
    if cursor.fetchone()[0] == 0:
        for c in COUNTRIES[:15]:  # ۱۵ کشور اول در بورس
            price = random.randint(50, 200)
            cursor.execute("INSERT INTO stock_market VALUES (?, ?, ?, 0)", (c, price, price))
        conn.commit()
    conn.close()

# توابع ارسال پیام بله
def send_message(chat_id, text, reply_markup=None):
    url = BASE_URL + "sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.json()
    except:
        return None

def answer_callback(callback_query_id, text=None, show_alert=False):
    url = BASE_URL + "answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
        payload["show_alert"] = show_alert
    try: requests.post(url, json=payload, timeout=5)
    except: pass

# --- دکمه‌های اصلی منو ---
def main_menu_keyboard():
    return {
        "keyboard": [
            [{"text": "🌍 کشور من"}, {"text": "⚔️ حمله / غارت"}],
            [{"text": "⛏️ استخراج منابع"}, {"text": "🏭 کارخانه‌ها"}],
            [{"text": "🛡️ ارتش و نظامی"}, {"text": "🤝 اتحادها (Clans)"}],
            [{"text": "📈 بورس و سهام"}, {"text": "💎 فروشگاه VIP / الماس"}],
            [{"text": "🏆 برترین‌ها"}, {"text": "ℹ️ راهنما / پشتیبانی"}]
        ],
        "resize_keyboard": True
    }

# --- هندل کردن دستورات متنی ---
def handle_text_message(chat_id, user_id, text):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if text == "/start":
        if not user:
            # ثبت‌نام اولیه
            cursor.execute("INSERT INTO users (user_id, coins) VALUES (?, 1000)", (user_id,))
            conn.commit()
            send_message(chat_id, "✨ به **ربات استراتژیک جنگ جهانی** خوش آمدید!\n\nلطفاً ابتدا کشور خود را انتخاب کنید تا بازی شروع شود:", choose_country_inline())
        else:
            if not user["country"]:
                send_message(chat_id, "🌍 لطفا کشور خود را انتخاب کنید:", choose_country_inline())
            else:
                send_message(chat_id, f"⚔️ فرمانده خوش آمدید! کشور شما: **{user['country']}**", main_menu_keyboard())
        conn.close()
        return True

    if not user or not user["country"]:
        send_message(chat_id, "❌ ابتدا باید با دستور /start کشور خود را انتخاب کنید.")
        conn.close()
        return True

    # منوهای اصلی
    if text == "🌍 کشور من":
        show_my_country(chat_id, user)
    elif text == "⛏️ استخراج منابع":
        mine_resources(chat_id, user_id)
    elif text == "🛡️ ارتش و نظامی":
        show_army_panel(chat_id, user)
    elif text == "📈 بورس و سهام":
        show_stock_market(chat_id, user_id)
    elif text == "💎 فروشگاه VIP / الماس":
        show_shop(chat_id)
    elif text == "⚔️ حمله / غارت":
        show_attack_menu(chat_id, user_id)
    elif text == "🏭 کارخانه‌ها":
        show_factory_menu(chat_id, user_id)
    elif text == "🤝 اتحادها (Clans)":
        show_alliance_menu(chat_id, user)
    elif text == "🏆 برترین‌ها":
        show_leaderboard(chat_id)
    elif text == "ℹ️ راهنما / پشتیبانی":
        send_message(chat_id, "📚 **راهنمای بازی جنگ جهانی**\n\nشما در این بازی فرمانده یک کشور هستید. باید با استخراج منابع، ساخت کارخانه و ارتقای ارتش به کشورهای دیگر حمله کنید و رتبه خود را بالا ببرید.\n\n👑 طراحان: صالح میرزایی، استاد محمد، داریوش (تیم VIP)")
    else:
        conn.close()
        return False

    conn.close()
    return True

def choose_country_inline():
    # نمایش چند کشور رندوم برای شلوغ نشدن کیبورد اینلاین
    random_countries = random.sample(COUNTRIES, 6)
    buttons = []
    for i in range(0, len(random_countries), 2):
        buttons.append([
            {"text": random_countries[i], "callback_data": f"set_country_{random_countries[i]}"},
            {"text": random_countries[i+1], "callback_data": f"set_country_{random_countries[i+1]}"}
        ])
    return {"inline_keyboard": buttons}

def show_my_country(chat_id, user):
    msg = f"🌍 **مشخصات کشور شما:**\n\n" \
          f"🏳️ نام کشور: {user['country']}\n" \
          f"💰 سکه: {user['coins']} | 💎 الماس: {user['diamonds']}\n" \
          f"🪵 چوب: {user['wood']} | ⚙️ آهن: {user['iron']} | 🛢️ نفت: {user['oil']}\n\n" \
          f"🎖️ سطح ارتش: {user['army_level']}\n" \
          f"👥 کل سربازان: {user['soldiers']}\n" \
          f"👑 وضعیت: " + ("کاربر VIP 👑" if user['vip_until'] else "کاربر عادی")
    
    markup = {"inline_keyboard": [[{"text": "🎁 دریافت هدیه روزانه", "callback_data": "claim_daily"}]]}
    send_message(chat_id, msg, markup)

def mine_resources(chat_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    now = datetime.now()
    if user["last_mine"]:
        last = datetime.fromisoformat(user["last_mine"])
        if now - last < timedelta(minutes=5):
            rem = timedelta(minutes=5) - (now - last)
            send_message(chat_id, f"⏳ کارگران خسته هستند! {int(rem.total_seconds())} ثانیه دیگر صبر کنید.")
            conn.close()
            return
            
    # استخراج رندوم
    w = random.randint(10, 30)
    i = random.randint(5, 15)
    o = random.randint(2, 8)
    
    cursor.execute("""
        UPDATE users 
        SET wood = wood + ?, iron = iron + ?, oil = oil + ?, last_mine = ? 
        WHERE user_id = ?
    """, (w, i, o, now.isoformat(), user_id))
    conn.commit()
    conn.close()
    
    send_message(chat_id, f"⛏️ **نتیجه استخراج موفقیت‌آمیز:**\n\n🪵 +{w} چوب\n⚙️ +{i} آهن\n🛢️ +{o} نفت")

def show_army_panel(chat_id, user):
    msg = f"🛡️ **بخش نظامی و ارتش کشور**\n\n" \
          f"🎖️ لول ارتش: {user['army_level']}\n" \
          f"💂 سرباز: {user['soldiers']} نفر\n" \
          f"🚜 تانک: {user['tanks']} دستگاه\n" \
          f"🛩️ جنگنده: {user['jets']} فروند\n\n" \
          f"💵 قیمت ارتقای لول ارتش: {user['army_level'] * 2000} سکه"
          
    markup = {
        "inline_keyboard": [
            [{"text": "💂 خرید سرباز (۵۰ سکه)", "callback_data": "buy_soldier"}, {"text": "🚜 خرید تانک (۳۰۰ سکه)", "callback_data": "buy_tank"}],
            [{"text": "🛩️ خرید جنگنده (۱۰۰۰ سکه)", "callback_data": "buy_jet"}, {"text": "🎖️ ارتقای لول ارتش", "callback_data": "upgrade_army"}]
        ]
    }
    send_message(chat_id, msg, markup)

def show_stock_market(chat_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_market")
    stocks = cursor.fetchall()
    
    msg = "📈 **بازار بورس و سهام بین‌الملل**\n\n"
    buttons = []
    for s in stocks:
        msg += f"🏳️ سهام {s['country']}: {s['current_price']:.1f} سکه ({s['last_change']:+.1f}%)\n"
        buttons.append([{"text": f"📊 معامله سهام {s['country']}", "callback_data": f"trade_{s['country']}"}])
        
    conn.close()
    markup = {"inline_keyboard": buttons[:6]} # نمایش ۶ تای اول برای خلوتی
    send_message(chat_id, msg, markup)

def show_shop(chat_id):
    msg = "💎 **فروشگاه الماس و قابلیت‌های ویژه VIP**\n\n" \
          "۱. پکیج ۱۰۰ الماس ➡️ ۵,۰۰۰ تومان\n" \
          "۲. پکیج ۵۰۰ الماس ➡️ ۲۰,۰۰۰ تومان\n" \
          "۳. اشتراک ۱ ماهه VIP (منابع ۲ برابر) ➡️ ۳۰,۰۰۰ تومان\n\n" \
          "👇 جهت خرید روی پکیج موردنظر کلیک کنید:"
          
    markup = {
        "inline_keyboard": [
            [{"text": "💎 ۱۰۰ الماس (۵هزارتومان)", "callback_data": "buy_pack_100"}],
            [{"text": "💎 ۵۰۰ الماس (۲۰هزارتومان)", "callback_data": "buy_pack_500"}],
            [{"text": "👑 ۱ ماه VIP (۳۰هزارتومان)", "callback_data": "buy_pack_vip"}]
        ]
    }
    send_message(chat_id, msg, markup)

def send_invoice(chat_id, title, description, payload, amount):
    url = BASE_URL + "sendInvoice"
    invoice = {
        "chat_id": chat_id,
        "title": title,
        "description": description,
        "payload": payload,
        "provider_token": PAYMENT_TOKEN if PAYMENT_TOKEN != "توکن پرداخت" else PAYMENT_TEST_TOKEN,
        "currency": "IRR",
        "prices": [{"label": title, "amount": amount * 10}] # تبدیل به ریال در بله
    }
    requests.post(url, json=invoice)

def show_attack_menu(chat_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, country, army_level FROM users WHERE user_id != ? AND country IS NOT NULL LIMIT 5", (user_id,))
    targets = cursor.fetchall()
    
    if not targets:
        send_message(chat_id, "❌ هیچ کشور دیگری برای حمله یافت نشد! شما اولین کشور هستید.")
        conn.close()
        return
        
    msg = "⚔️ **منوی جنگ و غارت کشورها**\n\nیک هدف را برای حمله انتخاب کنید:"
    buttons = []
    for t in targets:
        buttons.append([{"text": f"🔥 حمله به {t['country']} (لول {t['army_level']})", "callback_data": f"attack_target_{t['user_id']}"}])
        
    conn.close()
    markup = {"inline_keyboard": buttons}
    send_message(chat_id, msg, markup)

def show_factory_menu(chat_id, user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO factories (user_id) VALUES (?)", (user_id,))
    conn.commit()
    
    cursor.execute("SELECT * FROM factories WHERE user_id = ?", (user_id,))
    f = cursor.fetchone()
    conn.close()
    
    msg = f"🏭 **کارخانه‌های تولید منابع کشور شما:**\n\n" \
          f"🪵 چوب‌بری: لول {f['wood_mill']}\n" \
          f"⚙️ ذوب آهن: لول {f['iron_mine']}\n" \
          f"🛢️ پالایشگاه نفت: لول {f['oil_rig']}\n\n" \
          f"💡 کارخانه‌ها به صورت خودکار در ساعت منابع تولید می‌کنند."
          
    markup = {
        "inline_keyboard": [
            [{"text": "➕ ارتقا چوب‌بری (۵۰۰ چوب)", "callback_data": "up_f_wood"}, {"text": "➕ ارتقا آهن (۵۰۰ آهن)", "callback_data": "up_f_iron"}],
            [{"text": "➕ ارتقا پالایشگاه (۵۰۰ نفت)", "callback_data": "up_f_oil"}]
        ]
    }
    send_message(chat_id, msg, markup)

def show_alliance_menu(chat_id, user):
    conn = get_db()
    cursor = conn.cursor()
    
    if not user["alliance_id"]:
        msg = "🤝 **سیستم اتحادها (Clans)**\n\nشما هنوز عضو هیچ اتحادی نیستید. می‌توانید یک اتحاد جدید بسازید یا به اتحادهای برتر ملحق شوید."
        markup = {
            "inline_keyboard": [
                [{"text": "🛠️ ساخت اتحاد جدید (۵۰۰۰ سکه)", "callback_data": "create_alliance"}],
                [{"text": "📜 لیست اتحادها", "callback_data": "list_alliances"}]
            ]
        }
    else:
        cursor.execute("SELECT * FROM alliances WHERE id = ?", (user["alliance_id"],))
        allian = cursor.fetchone()
        msg = f"🤝 **اتحاد شما: {allian['name']}**\n\n" \
              f"🎖️ لول اتحاد: {allian['level']} | 🌟 تجربه: {allian['xp']}\n" \
              f"💰 بانک سکه اتحاد: {allian['coins_bank']} سکه\n" \
              f"🪵 چوب بانک: {allian['wood_bank']} | ⚙️ آهن: {allian['iron_bank']}"
        markup = {
            "inline_keyboard": [
                [{"text": "💰 کمک مالی به اتحاد", "callback_data": "donate_alliance"}],
                [{"text": "❌ خروج از اتحاد", "callback_data": "leave_alliance"}]
            ]
        }
        
    conn.close()
    send_message(chat_id, msg, markup)

def show_leaderboard(chat_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT country, coins FROM users WHERE country IS NOT NULL ORDER BY coins DESC LIMIT 10")
    leaders = cursor.fetchall()
    conn.close()
    
    msg = "🏆 **جدول ثروتمندترین کشورهای جهان:**\n\n"
    for idx, l in enumerate(leaders, 1):
        msg += f"{idx}. 🏳️ {l['country']} ➡️ {l['coins']} سکه\n"
    send_message(chat_id, msg)


# --- بخش کالبک دکمه‌های اینلاین ---
def handle_callback(chat_id, user_id, data):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if data.startswith("set_country_"):
        country = data.replace("set_country_", "")
        cursor.execute("UPDATE users SET country = ? WHERE user_id = ?", (country, user_id))
        conn.commit()
        send_message(chat_id, f"🏳️ کشور شما با موفقیت به **{country}** تغییر یافت! بازی شروع شد.", main_menu_keyboard())
        
    elif data == "claim_daily":
        now = datetime.now()
        if user["last_daily"] and datetime.fromisoformat(user["last_daily"]).date() == now.date():
            send_message(chat_id, "❌ شما هدیه روزانه امروز را دریافت کرده‌اید!")
        else:
            reward = 500 if not user["vip_until"] else 1200
            cursor.execute("UPDATE users SET coins = coins + ?, last_daily = ? WHERE user_id = ?", (reward, now.isoformat(), user_id))
            conn.commit()
            send_message(chat_id, f"🎁 هدیه روزانه دریافت شد: **+{reward} سکه**")
            
    elif data == "buy_soldier":
        if user["coins"] >= 50:
            cursor.execute("UPDATE users SET coins = coins - 50, soldiers = soldiers + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            send_message(chat_id, "💂 یک سرباز جدید استخدام شد!")
        else: send_message(chat_id, "❌ سکه کافی نیست!")
        
    elif data == "buy_tank":
        if user["coins"] >= 300:
            cursor.execute("UPDATE users SET coins = coins - 300, tanks = tanks + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            send_message(chat_id, "🚜 یک تانک جدید خریداری شد!")
        else: send_message(chat_id, "❌ سکه کافی نیست!")

    elif data == "buy_jet":
        if user["coins"] >= 1000:
            cursor.execute("UPDATE users SET coins = coins - 1000, jets = jets + 1 WHERE user_id = ?", (user_id,))
            conn.commit()
            send_message(chat_id, "🛩️ یک جنگنده پیشرفته به ارتش اضافه شد!")
        else: send_message(chat_id, "❌ سکه کافی نیست!")

    elif data == "upgrade_army":
        cost = user["army_level"] * 2000
        if user["coins"] >= cost:
            cursor.execute("UPDATE users SET coins = coins - ?, army_level = army_level + 1 WHERE user_id = ?", (cost, user_id))
            conn.commit()
            send_message(chat_id, f"🎖️ سطح ارتش کشور به لول {user['army_level']+1} ارتقا یافت!")
        else: send_message(chat_id, f"❌ سکه کافی نیست! نیاز به {cost} سکه دارید.")

    # خرید فروشگاهی
    elif data == "buy_pack_100":
        send_invoice(chat_id, "پکیج ۱۰۰ الماس", "خرید ۱۰۰ الماس برای بازی جنگ جهانی", "pack_100", 5000)
    elif data == "buy_pack_500":
        send_invoice(chat_id, "پکیج ۵۰۰ الماس", "خرید ۵۰۰ الماس برای بازی جنگ جهانی", "pack_500", 2000)
    elif data == "buy_pack_vip":
        send_invoice(chat_id, "اشتراک ۱ ماهه VIP", "فعالسازی حالت ویژه VIP به مدت یک ماه", "pack_vip", 30000)

    # سیستم حمله
    elif data.startswith("attack_target_"):
        target_id = int(data.replace("attack_target_", ""))
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (target_id,))
        target = cursor.fetchone()
        
        # محاسبه قدرت نظامی ساده
        my_power = (user["soldiers"] * 1) + (user["tanks"] * 5) + (user["jets"] * 15) * user["army_level"]
        target_power = (target["soldiers"] * 1) + (target["tanks"] * 5) + (target["jets"] * 15) * target["army_level"]
        
        if my_power > target_power:
            loot = int(target["coins"] * 0.2)
            cursor.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (loot, user_id))
            cursor.execute("UPDATE users SET coins = coins - ? WHERE user_id = ?", (loot, target_id))
            send_message(chat_id, f"🔥 **پیروزی در جنگ!**\n\nارتش شما به کشور {target['country']} غلبه کرد و موفق شد **{loot} سکه** غارت کند!")
        else:
            loss_soldiers = int(user["soldiers"] * 0.3)
            cursor.execute("UPDATE users SET soldiers = soldiers - WHERE user_id = ?", (loss_soldiers, user_id))
            send_message(chat_id, f"😭 **شکست در جنگ!**\n\nنیروهای شما در مقابل دفاع سنگین {target['country']} شکست خوردند و {loss_soldiers} سرباز را از دست دادید.")
        conn.commit()

    conn.close()

# مدیریت سیستم پرداخت‌ها
def pre_checkout_query(query):
    url = BASE_URL + "answerPreCheckoutQuery"
    payload = {"pre_checkout_query_id": query["id"], "ok": True}
    requests.post(url, json=payload)

def successful_payment(chat_id, user_id, payload, amount, currency):
    conn = get_db()
    cursor = conn.cursor()
    if payload == "pack_100":
        cursor.execute("UPDATE users SET diamonds = diamonds + 100 WHERE user_id = ?", (user_id,))
        send_message(chat_id, "💎 تراکنش موفقیت‌آمیز بود! ۱۰۰ الماس به اکانت شما اضافه شد.")
    elif payload == "pack_500":
        cursor.execute("UPDATE users SET diamonds = diamonds + 500 WHERE user_id = ?", (user_id,))
        send_message(chat_id, "💎 تراکنش موفقیت‌آمیز بود! ۵۰۰ الماس به اکانت شما اضافه شد.")
    elif payload == "pack_vip":
        vip_date = (datetime.now() + timedelta(days=30)).isoformat()
        cursor.execute("UPDATE users SET vip_until = ? WHERE user_id = ?", (vip_date, user_id))
        send_message(chat_id, "👑 تبریک! شما به مدت ۳۰ روز عضو کاربر ویژه VIP شدید.")
    conn.commit()
    conn.close()

# چرخه خودکار کارخانه‌ها در پس‌زمینه
def factory_auto_production():
    while True:
        try:
            time.sleep(3600) # هر یک ساعت یک بار
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM factories")
            all_f = cursor.fetchall()
            for f in all_f:
                cursor.execute("""
                    UPDATE users 
                    SET wood = wood + ?, iron = iron + ?, oil = oil + ? 
                    WHERE user_id = ?
                """, (f["wood_mill"]*10, f["iron_mine"]*5, f["oil_rig"]*2, f["user_id"]))
            conn.commit()
            conn.close()
        except: pass

# موتور محرک ربات (Long Polling)
def main():
    init_db()
    print("✅ دیتابیس آماده است")
    
    # استارت ترد کارخانه‌ها
    t = threading.Thread(target=factory_auto_production, daemon=True)
    t.start()
    
    offset = 0
    print("📡 در حال دریافت پیام‌ها...")
    
    while True:
        try:
            url = BASE_URL + f"getUpdates?offset={offset}&timeout=20"
            res = requests.get(url, timeout=25).json()
            
            if "result" in res:
                for update in res["result"]:
                    offset = update["update_id"] + 1
                    
                    # پیام‌های متنی
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        text = msg["text"]
                        
                        # چنل چک امنیتی ادمین
                        if user_id == MAIN_ADMIN_ID and text == "/panel":
                            send_message(chat_id, "⚙️ منوی ادمین اصلی باز شد.")
                        else:
                            if not handle_text_message(chat_id, user_id, text):
                                send_message(chat_id, "❌ دستور نامعتبر. از منوی زیر استفاده کنید.")
                                
                    # دکمه‌های اینلاین
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        chat_id = callback["message"]["chat"]["id"]
                        user_id = callback["from"]["id"]
                        data = callback["data"]
                        
                        handle_callback(chat_id, user_id, data)
                        answer_callback(callback["id"])
                    
                    # استعلام قبل از پرداخت
                    elif "pre_checkout_query" in update:
                        pre_checkout_query(update["pre_checkout_query"])
                    
                    # تایید پرداخت موفقیت‌آمیز
                    elif "message" in update and "successful_payment" in update["message"]:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        payment = msg["successful_payment"]
                        successful_payment(chat_id, user_id, payment["invoice_payload"], 
                                           payment["total_amount"], payment["currency"])
            
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            print("\n🛑 ربات متوقف شد.")
            break
        except Exception as e:
            print(f"❌ خطا: {e}")
            time.sleep(3)

if __name__ == "__main__":
    main()
