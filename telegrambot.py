from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os
from datetime import datetime

TOKEN = "7820235468:AAFLoJXoVYGrcpw7B_dx4BlTXKFfEkpexjc"
ADMIN_IDS = [829510841]  # حط ID الأدمن هنا
channel_id = -1002698646841  # ID القناة (تأكد إنه صح)

DATA_FILE = "series_data.json"
USAGE_LOG_FILE = "usage_log.json"
PENDING_ADDS = {}

# ========== أدوات التعامل مع الملفات ==========
def load_series_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_series_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_usage(user, action, extra=""):
    log_entry = {
        "user_id": user.id,
        "username": user.username or "",
        "name": f"{user.first_name} {user.last_name or ''}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "extra": extra
    }
    if not os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([log_entry], f, ensure_ascii=False, indent=2)
    else:
        with open(USAGE_LOG_FILE, "r+", encoding="utf-8") as f:
            data = json.load(f)
            data.append(log_entry)
            f.seek(0)
            json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def generate_episode_buttons(episodes: dict, series_name: str, per_row: int = 4):
    try:
        keys_sorted = sorted(episodes.keys(), key=lambda x: int(x))
    except:
        keys_sorted = sorted(episodes.keys())

    buttons = []
    for i in range(0, len(keys_sorted), per_row):
        row = [
            InlineKeyboardButton(f"حلقة {ep}", callback_data=f"episode|{series_name}|{ep}")
            for ep in keys_sorted[i:i+per_row]
        ]
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_series")])
    return buttons

# ========== الأوامر ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="recheck_sub")]
        ])
        await update.message.reply_text(
            "⚠️ لازم تشترك في القناة الأول.\n📢 https://t.me/AlboraninTV",
            reply_markup=keyboard
        )
        return

    log_usage(user, "start")

    series_data = load_series_data()
    if not series_data:
        await update.message.reply_text("📂 مفيش مسلسلات مضافة حتى الآن.")
        return

    buttons = [
        [InlineKeyboardButton(series_name, callback_data=f"series|{series_name}")]
        for series_name in series_data
    ]
    await update.message.reply_text(
        "📺 اختر المسلسل اللي عايز تشوفه:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    series_data = load_series_data()

    if data == "recheck_sub":
        if not await is_user_subscribed(user.id, context):
            await query.message.reply_text("⚠️ لسه مش مشترك أو التحقق اتأخر شوية. حاول تاني بعد 10 ثواني.")
            return
        await start(update, context)
        return

    if data == "back_to_series":
        buttons = [
            [InlineKeyboardButton(series_name, callback_data=f"series|{series_name}")]
            for series_name in series_data
        ]
        await query.message.edit_text(
            "📺 اختر المسلسل اللي عايز تشوفه:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if data.startswith("series|"):
        series_name = data.split("|")[1]
        episodes = series_data.get(series_name, {})
        buttons = generate_episode_buttons(episodes, series_name)
        await query.message.edit_text(
            f"🎬 اختر الحلقة من {series_name}:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif data.startswith("episode|"):
        _, series_name, ep_number = data.split("|")
        episode = series_data.get(series_name, {}).get(ep_number)
        if not episode:
            await query.message.reply_text("⚠️ الحلقة غير موجودة.")
            return

        log_usage(user, "watch_episode", f"{series_name} - حلقة {ep_number}")

        await context.bot.forward_message(
            chat_id=query.message.chat_id,
            from_chat_id=episode["chat_id"],
            message_id=episode["message_id"]
        )
        await query.message.reply_text(
            "⬅️ رجوع للقائمة:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 رجوع للقائمة", callback_data="back_to_series")]
            ])
        )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        await update.message.reply_text("⚠️ لازم تشترك في القناة.")
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

    series_data[series_name][episode_number] = {
        "chat_id": update.message.forward_from_chat.id,
        "message_id": update.message.forward_from_message_id
    }

    save_series_data(series_data)
    log_usage(user, "saved_episode", f"{series_name} - {episode_number}")
    await update.message.reply_text(f"✅ تم حفظ الحلقة {episode_number} لمسلسل {series_name}")

async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        await update.message.reply_text("⚠️ لازم تشترك في القناة.")
        return

    series_data = load_series_data()
    if not series_data:
        await update.message.reply_text("❌ مفيش بيانات حالياً.")
        return

    log_usage(user, "list_series")

    text = "📚 قائمة المسلسلات والحلقات:\n\n"
    for series, episodes in series_data.items():
        ep_list = ", ".join(sorted(episodes.keys(), key=lambda x: int(x) if x.isdigit() else x))
        text += f"• {series} ({len(episodes)} حلقات): {ep_list}\n"
    await update.message.reply_text(text)

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

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ مش مسموحلك.")
        return

    data = load_series_data()
    total_series = len(data)
    total_episodes = sum(len(episodes) for episodes in data.values())

    users = set()
    if os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
            users = {entry["user_id"] for entry in logs}

    text = f"""📊 لوحة تحكم البوت:

• عدد المسلسلات: {total_series}
• عدد الحلقات: {total_episodes}
• عدد المستخدمين: {len(users)}

🕹️ التحكم:
- /list : عرض الحلقات
- /add : إضافة
- /delete : حذف
"""
    await update.message.reply_text(text)

# ========== تشغيل البوت ==========
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_series))
app.add_handler(CommandHandler("delete", delete_episode))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.FORWARDED & filters.TEXT, handle_forward))
app.add_handler(MessageHandler(filters.FORWARDED & filters.VIDEO, handle_forward))
app.add_handler(MessageHandler(filters.FORWARDED & filters.PHOTO, handle_forward))

print("✅ البوت شغّال...")
app.run_polling()
