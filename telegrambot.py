from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from database import init_db, add_user, get_all_user_ids
import json
import os
import re
from datetime import datetime

TOKEN = "8118153328:AAFgcRg4W0QwHUh69N4kmf2dAj2IhVOThMw"
ADMIN_IDS = [829510841]
channel_id = -1002894773514
DATA_FILE = "series_data.json"
USAGE_LOG_FILE = "usage_log.json"
PENDING_ADDS = {}
EPISODES_PER_PAGE = 20

# ========== إعدادات ==========
SERIES_PER_ROW = 3  # عدد المسلسلات في كل صف

# ========== أدوات التحميل والحفظ ==========
def load_series_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_series_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_usage(user, action, extra=""):
    entry = {
        "user_id": user.id,
        "username": user.username or "",
        "name": f"{user.first_name} {user.last_name or ''}".strip(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "extra": extra
    }
    print("✅ log_usage entry:", entry)
    logs = []
    if os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    logs.append(entry)
    with open(USAGE_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def sanitize_callback(text):
    return re.sub(r"[^\w\d]", "", text).strip()[:20]


# ========== توليد أزرار المواسم والحلقات ==========
# ✅ تنظيف النص من الرموز لتفادي أخطاء callback_data

def sanitize_callback(text):
    return re.sub(r"[^\w\d]", "", text).strip()[:20]  # إزالة الرموز وقصر النص

# ========== توليد أزرار المواسم والحلقات ==========
def generate_season_buttons(series_data, series_name):
    return [[InlineKeyboardButton(season_name, callback_data=f"season|{sanitize_callback(series_name)}|{sanitize_callback(season_name)}")]
            for season_name in series_data[series_name].keys()] + [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_series")]]

def generate_episode_buttons(episodes: dict, series_name: str, season_name: str, page: int = 0, per_row: int = 4):
    keys_sorted = sorted([k.strip() for k in episodes.keys() if k.strip().isdigit()], key=lambda x: int(x))
    total = len(keys_sorted)
    start = page * EPISODES_PER_PAGE
    end = start + EPISODES_PER_PAGE
    paginated = keys_sorted[start:end]
    buttons = []
    for i in range(0, len(paginated), per_row):
        row = [
            InlineKeyboardButton(
                f"حلقة {int(ep)}",
                callback_data=f"episode|{sanitize_callback(series_name)}|{sanitize_callback(season_name)}|{ep}"
            )
            for ep in paginated[i:i + per_row]
        ]
        buttons.append(row)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ السابق",
            callback_data=f"season|{sanitize_callback(series_name)}|{sanitize_callback(season_name)}|{page-1}"
        ))
    if end < total:
        nav_buttons.append(InlineKeyboardButton(
            "التالي ➡️",
            callback_data=f"season|{sanitize_callback(series_name)}|{sanitize_callback(season_name)}|{page+1}"
        ))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"back_to_seasons|{sanitize_callback(series_name)}")])
    return buttons

# ========== تسجيل الاستخدام ==========

def log_usage(user, action, extra="-"):
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": user.first_name,
        "username": user.username or "-",
        "action": action,
        "extra": extra
    }

    try:
        with open("usage_log.json", "r", encoding="utf-8") as f:
            logs = json.load(f)
    except FileNotFoundError:
        logs = []

    logs.append(log_entry)

    with open("usage_log.json", "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

# ========== broadcast ==========
BATCH_SIZE = 30
DELAY_BETWEEN_BATCHES = 1  # ثواني

async def try_send(bot, user_id, message):
    try:
        await bot.send_message(chat_id=user_id, text=message)
        return "success"
    except Exception as e:
        print(f"❌ فشل مع {user_id}: {e}")
        return "fail"

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE, message: str):
    users = get_all_user_ids()
    success, failed = 0, 0

    for i in range(0, len(users), BATCH_SIZE):
        batch = users[i:i+BATCH_SIZE]

        # ✅ هنا مكان طباعة رقم الدفعة
        print(f"📦 Batch {(i // BATCH_SIZE) + 1} - جاري الإرسال لـ {len(batch)} مستخدم")

        results = await asyncio.gather(*[
            try_send(context.bot, user_id, message)
            for user_id in batch
        ])
        success += results.count("success")
        failed += results.count("fail")
        await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    # ✅ ترجع النتائج لدالة broadcast_command
    return success, failed

# ========== /ارسال اعلان ==========
async def handle_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        return

    if context.user_data.get("awaiting_broadcast"):
        context.user_data["awaiting_broadcast"] = False
        context.user_data["pending_broadcast_message"] = update.message.text

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin")]
        ])

        await update.message.reply_text(
            f"📢 الرسالة المراد إرسالها:\n\n{update.message.text}",
            reply_markup=keyboard
        )

# ========== /البحث عن المسلسلات ==========
async def handle_series_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not context.user_data.get("awaiting_series_search"):
        return

    context.user_data["awaiting_series_search"] = False
    query = update.message.text.lower()
    series_data = load_series_data()

    results = []

    for series_name, series_info in series_data.items():
        # بحث في اسم المسلسل نفسه
        if query in series_name.lower():
            results.append(("series", series_name))

        # بحث داخل المواسم
        for season_name, episodes in series_info.items():
            if not isinstance(episodes, dict):
                continue

            if query in season_name.lower():
                results.append(("season", series_name, season_name))

            # بحث داخل الحلقات داخل كل موسم
            for ep_num, ep_info in episodes.items():
                if query in ep_num or query in f"{series_name.lower()} {season_name.lower()}":
                    results.append(("episode", series_name, ep_num, season_name))

    if not results:
        await update.message.reply_text("❌ مفيش نتائج.")
        return

    keyboard = []
    for item in results:
        if item[0] == "series":
            _, name = item
            keyboard.append([InlineKeyboardButton(f"📺 {name}", callback_data=f"series|{name}")])
        elif item[0] == "season":
            _, series_name, season_name = item
            keyboard.append([InlineKeyboardButton(f"📂 {series_name} - {season_name}", callback_data=f"season|{series_name}|{season_name}")])
        elif item[0] == "episode":
            _, series_name, ep_num, season_name = item
            keyboard.append([InlineKeyboardButton(f"🎞 {series_name} - {season_name} - حلقة {ep_num}", callback_data=f"episode|{series_name}|{ep_num}")])

    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_series")])


    await update.message.reply_text("🔎 نتائج البحث:", reply_markup=InlineKeyboardMarkup(keyboard))


# ========== /start ==========
# دالة لحفظ user_id في ملف users.json
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # تحقق من الاشتراك
    if not await is_user_subscribed(user.id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 إشترك في القناة من هنا", url="https://t.me/+TjSNl-DGAYgyYjc0")],
            [InlineKeyboardButton("📢 إشترك في القناة  الاحتياطية من هنا", url="https://t.me/+kmoZ3ILV8O9hM2Zk")],
            [InlineKeyboardButton("👥 إشترك في الجروب", url="https://t.me/+Dv65alI3QCgzMzM0")]
        ])
        await update.message.reply_text("⚠️ لازم تشترك في القناة عشان تقدر تستخدم البوت.", reply_markup=keyboard)
        return

    # تسجل المستخدم الجديد
    add_user(user)

    # تسجيل الاستخدام
    log_usage(user, "start")

    # تحميل البيانات
    series_data = load_series_data()
    if not series_data:
        await update.message.reply_text("📂 مفيش مسلسلات مضافة حتى الآن.")
        return

    # توليد أزرار المسلسلات
    buttons = [[InlineKeyboardButton(series_name, callback_data=f"series|{sanitize_callback(series_name)}")]
               for series_name in series_data]

# ✅ نضيف زر البحث في الآخر
    buttons.append([InlineKeyboardButton("🔍 بحث عن مسلسل", callback_data="search_series")])


    await update.message.reply_text("📺 اختار المسلسل اللي عايز تشوفه:", reply_markup=InlineKeyboardMarkup(buttons))

# ========== الضغطات ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    series_data = load_series_data()

    if data == "admin_list":
        await list_series(update, context)
        return

    if data == "admin_logs":
        await show_logs(update, context)
        return

    if data == "admin_add":
        await query.message.reply_text("استخدم الأمر `/add اسم_المسلسل رقم_الحلقة` لإضافة حلقة جديدة.", parse_mode="Markdown")
        return

    if data == "admin_delete":
        await query.message.reply_text("استخدم الأمر `/delete اسم_المسلسل رقم_الحلقة` لحذف حلقة.", parse_mode="Markdown")
        return


    # استرجاع الاسم الحقيقي من البيانات (من أول تطابق موجود)
    def find_series_name(short_name):
        for name in series_data:
            if sanitize_callback(name) == short_name:
                return name
        return None

    if data == "back_to_series":
        series_names = list(series_data.keys())
        buttons = []

        for i in range(0, len(series_names), SERIES_PER_ROW):
            row = [
                InlineKeyboardButton(series_name, callback_data=f"series|{sanitize_callback(series_name)}")
                for series_name in series_names[i:i + SERIES_PER_ROW]
            ]
            buttons.append(row)

        await query.message.edit_text("📺 اختار المسلسل اللي عايز تشوفه:", reply_markup=InlineKeyboardMarkup(buttons))
        return


    if data.startswith("back_to_seasons|"):
        _, short_series = data.split("|")
        series_name = find_series_name(short_series)
        if not series_name:
            await query.message.edit_text("❌ تعذر عرض المواسم.")
            return
        buttons = generate_season_buttons(series_data, series_name)
        await query.message.edit_text(f"📂 اختار الموسم من {series_name}:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("series|"):
        _, short_series = data.split("|")
        series_name = find_series_name(short_series)
        if not series_name:
            await query.message.edit_text("❌ تعذر عرض المسلسل.")
            return
        buttons = generate_season_buttons(series_data, series_name)
        await query.message.edit_text(f"📂 اختار الموسم من {series_name}:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("season|"):
        parts = data.split("|")
        short_series = parts[1]
        short_season = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0
        series_name = find_series_name(short_series)
        if not series_name:
            await query.message.edit_text("❌ تعذر عرض الحلقات.")
            return
        season_name = None
        for s in series_data[series_name]:
            if sanitize_callback(s) == short_season:
                season_name = s
                break
        if not season_name:
            await query.message.edit_text("❌ الموسم غير موجود.")
            return
        episodes = series_data[series_name][season_name]
        buttons = generate_episode_buttons(episodes, series_name, season_name, page)
        await query.message.edit_text(f"🎬 اختار الحلقة من {series_name} - {season_name}:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("episode|"):
        _, short_series, short_season, ep_number = data.split("|")
        series_name = find_series_name(short_series)
        if not series_name:
            await query.message.reply_text("❌ المسلسل غير موجود.")
            return
        season_name = None
        for s in series_data[series_name]:
            if sanitize_callback(s) == short_season:
                season_name = s
                break
        if not season_name:
            await query.message.reply_text("❌ الموسم غير موجود.")
            return
        episode = series_data.get(series_name, {}).get(season_name, {}).get(ep_number.strip())
        if not episode:
            await query.message.reply_text("⚠️ الحلقة غير موجودة.")
            return
        log_usage(user, "watch_episode", f"{series_name} - {season_name} - حلقة {ep_number}")
        await context.bot.forward_message(
            chat_id=query.message.chat_id,
            from_chat_id=episode["chat_id"],
            message_id=episode["message_id"]
        )
        await query.message.reply_text("🎬 تم عرض الحلقة.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 رجوع للقائمة", callback_data="back_to_series")]
        ]))

# ========== /add ==========
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        await update.message.reply_text("⚠️ لازم تشترك في القناة عشان تقدر تستخدم البوت، وبعدها ارجع هنا واضغط على ⬅️ /start.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("❌ مش مسموحلك تستخدم الأمر ده.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدم الأمر كده:\n`/add اسم_المسلسل رقم_الحلقة`", parse_mode="Markdown")
        return

    series_name = context.args[0]
    episode_number = context.args[1]
    PENDING_ADDS[user.id] = (series_name, episode_number)
    log_usage(user, "add_episode", f"{series_name} - {episode_number}")
    await update.message.reply_text(f"✅ تمام، ابعتلي الحلقة (فورورد من الجروب) كحلقة {episode_number} لمسلسل {series_name}")

# ========== التقاط الرسالة الموجهة ==========
async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in PENDING_ADDS:
        return

    if not update.message.forward_from_chat:
        await update.message.reply_text("⚠️ لازم تبعتلي الرسالة كـ *Forward* من الجروب.", parse_mode="Markdown")
        return

    series_name, episode_number = PENDING_ADDS.pop(user.id)
    series_data = load_series_data()

    if series_name not in series_data:
        series_data[series_name] = {}

    series_data[series_name][episode_number.strip()] = {
    "chat_id": update.message.forward_from_chat.id,
    "message_id": update.message.forward_from_message_id
    }

    save_series_data(series_data)
    log_usage(user, "saved_episode", f"{series_name} - {episode_number}")
    await update.message.reply_text(f"✅ تم حفظ الحلقة {episode_number} لمسلسل {series_name}")

# ========== /list ==========
async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        await (update.message or update.callback_query.message).reply_text("⚠️ لازم تشترك في القناة.")
        return

    series_data = load_series_data()
    if not series_data:
        await (update.message or update.callback_query.message).reply_text("❌ مفيش بيانات حالياً.")
        return

    log_usage(user, "list_series")

    series_names = list(series_data.keys())
    buttons = []

    for i in range(0, len(series_names), SERIES_PER_ROW):
        row = [
            InlineKeyboardButton(series_name, callback_data=f"series|{sanitize_callback(series_name)}")
            for series_name in series_names[i:i + SERIES_PER_ROW]
        ]
        buttons.append(row)

    await (update.message or update.callback_query.message).reply_text(
        "📚 قائمة المسلسلات:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========== /delete ==========
async def delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ مش مسموحلك بالأمر ده.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدم كده:\n`/delete اسم_المسلسل رقم_الحلقة`", parse_mode="Markdown")
        return

    series_name = context.args[0]
    episode_number = context.args[1]
    series_data = load_series_data()

    if series_name in series_data and episode_number in series_data[series_name]:
        del series_data[series_name][episode_number]
        if not series_data[series_name]:
            del series_data[series_name]
        save_series_data(series_data)
        log_usage(user, "delete_episode", f"{series_name} - {episode_number}")
        await update.message.reply_text(f"🗑️ تم حذف الحلقة {episode_number} من {series_name}.")
    else:
        await update.message.reply_text("❌ الحلقة أو المسلسل غير موجود.")

# ========== /admin ==========
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ مش مسموحلك.")
        return

    data = load_series_data()
    total_series = len(data)
    total_seasons = sum(len(series) for series in data.values())
    total_episodes = sum(len(season) for series in data.values() for season in series.values())

    user_ids = set()
    logs = []
    if os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
            try:
                logs = json.load(f)
                for entry in logs:
                    user_ids.add(entry.get("user_id"))
            except:
                logs = []

    text = f"""📊 لوحة تحكم البوت:

• عدد المسلسلات: {total_series}
• عدد المواسم: {total_seasons}
• عدد الحلقات: {total_episodes}
• عدد المستخدمين: {len(user_ids)}
• عدد الأوامر المسجلة: {len(logs)}

اختر إجراء:
"""

    buttons = [
        [
            InlineKeyboardButton("📃 عرض المسلسلات", callback_data="admin_list"),
            InlineKeyboardButton("📋 سجل الاستخدام", callback_data="admin_logs")
        ],
        [
            InlineKeyboardButton("📊 عرض الإحصائيات", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("📢 إرسال إعلان", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("➕ إضافة حلقة", callback_data="admin_add"),
            InlineKeyboardButton("🗑 حذف حلقة", callback_data="admin_delete")
        ],
        [
            InlineKeyboardButton("🏠 العودة للبداية", callback_data="back_to_series")
        ]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

# ========== /logs ==========
async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await (update.message or update.callback_query.message).reply_text("❌ غير مصرح لك.")
        return

    if not os.path.exists(USAGE_LOG_FILE):
        await (update.message or update.callback_query.message).reply_text("⚠️ لا يوجد سجل استخدام.")
        return

    with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)

    text = "📝 سجل الاستخدام:\n\n"
    for entry in logs[-50:]:  # آخر 50 استخدام فقط
        line = f"{entry['timestamp']} - {entry['name']} (@{entry['username']}): {entry['action']} {entry['extra']}\n"
        text += line

    if len(text) > 4000:
        text = text[-4000:]

    await (update.message or update.callback_query.message).reply_text(text)

# ========== /broadcast ==========
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not is_admin(user.id):
        await update.message.reply_text("❌ مش مسموحلك تستخدم الأمر ده.")
        return

    if not context.args:
        await update.message.reply_text("❗ اكتب الرسالة بعد الأمر، مثال:\n`/broadcast فيه مسلسل جديد 🔥`", parse_mode="Markdown")
        return

    message = " ".join(context.args)
    await update.message.reply_text("⏳ جاري إرسال الرسالة لكل المستخدمين...")
    success, failed = await broadcast_message(context, message)
    await update.message.reply_text(f"📤 تم الإرسال لـ {success} مستخدم، وفشل مع {failed}.")

# ========== تشغيل البوت ==========

async def set_commands(app):
    await app.bot.set_my_commands([
        BotCommand("start", "بدء البوت"),
        BotCommand("admin", "لوحة التحكم"),
        BotCommand("broadcast", "إرسال رسالة لكل المستخدمين"),
        BotCommand("logs", "سجل الاستخدام"),
        BotCommand("list", "قائمة المسلسلات"),
        BotCommand("add", "إضافة حلقة"),
        BotCommand("delete", "حذف حلقة"),
    ])

app = ApplicationBuilder().token(TOKEN).post_init(set_commands).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("broadcast", broadcast_command))
app.add_handler(CommandHandler("list", list_series))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("delete", delete_episode))
app.add_handler(CommandHandler("logs", show_logs))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_broadcast_input))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_series_search))

app.add_handler(CallbackQueryHandler(button_handler))

app.add_handler(MessageHandler(filters.FORWARDED & filters.TEXT, handle_forward))
app.add_handler(MessageHandler(filters.FORWARDED & filters.VIDEO, handle_forward))
app.add_handler(MessageHandler(filters.FORWARDED & filters.PHOTO, handle_forward))

print("✅ البوت شغّال...")
init_db()
app.run_polling()