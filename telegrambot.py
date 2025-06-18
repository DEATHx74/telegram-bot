from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json, os
from datetime import datetime

TOKEN = "7820235468:AAFLoJXoVYGrcpw7B_dx4BlTXKFfEkpexjc"
ADMIN_IDS = [829510841]
channel_id = -1002698646841

DATA_FILE = "series_data.json"
USAGE_LOG_FILE = "usage_log.json"
PENDING_ADDS = {}

def load_series_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_series_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log_usage(user, action, extra=""):
    log = {
        "user_id": user.id,
        "username": user.username or "",
        "name": f"{user.first_name} {user.last_name or ''}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "extra": extra
    }
    data = []
    if os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except:
                data = []
    data.append(log)
    with open(USAGE_LOG_FILE, "w", encoding="utf-8") as f:
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

# ====== الأوامر ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ إبدأ الآن", callback_data="recheck_sub")]
        ])
        await update.message.reply_text(
            "⚠️ لازم تشترك في القناة الأول وبعدها اضغط على زر 'إبدأ الآن'.\n📢 https://t.me/AlboraninTV",
            reply_markup=keyboard
        )
        return

    log_usage(user, "start")

    series_data = load_series_data()
    if not series_data:
        await update.message.reply_text("📂 مفيش مسلسلات مضافة حتى الآن.")
        return

    buttons = [
        [InlineKeyboardButton(series, callback_data=f"series|{series}")]
        for series in series_data
    ]
    await update.message.reply_text("📺 اختر المسلسل اللي عايز تشوفه:", reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data
    series_data = load_series_data()

    if data == "recheck_sub":
        if not await is_user_subscribed(user.id, context):
            await query.message.reply_text("⚠️ لسه مش مشترك، جرب بعد شوية.")
            return
        await start(update, context)
        return

    if data == "back_to_series":
        buttons = [[InlineKeyboardButton(series, callback_data=f"series|{series}")] for series in series_data]
        await query.message.edit_text("📺 اختر المسلسل اللي عايز تشوفه:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("series|"):
        series_name = data.split("|")[1]
        episodes = series_data.get(series_name, {})
        buttons = generate_episode_buttons(episodes, series_name)
        await query.message.edit_text(f"🎬 اختر الحلقة من {series_name}:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("episode|"):
        _, series_name, ep = data.split("|")
        episode = series_data.get(series_name, {}).get(ep)
        if not episode:
            await query.message.reply_text("⚠️ الحلقة غير موجودة.")
            return
        log_usage(user, "watch_episode", f"{series_name} - حلقة {ep}")
        await context.bot.forward_message(chat_id=query.message.chat_id, from_chat_id=episode["chat_id"], message_id=episode["message_id"])
        await query.message.reply_text("⬅️ رجوع للقائمة:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 رجوع للقائمة", callback_data="back_to_series")]]))

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        await update.message.reply_text("⚠️ لازم تشترك في القناة.")
        return
    if not is_admin(user.id):
        await update.message.reply_text("❌ مش مسموحلك.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدم كده:\n`/add اسم_المسلسل رقم_الحلقة`", parse_mode="Markdown")
        return
    series, ep = context.args[0], context.args[1]
    PENDING_ADDS[user.id] = (series, ep)
    log_usage(user, "add_episode", f"{series} - {ep}")
    await update.message.reply_text(f"✅ تمام، ابعتلي الحلقة كـ Forward عشان أسجلها: {series} - حلقة {ep}")

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in PENDING_ADDS:
        return
    if not update.message.forward_from_chat:
        await update.message.reply_text("⚠️ لازم تبعت الحلقة كـ Forward من الجروب.")
        return

    series, ep = PENDING_ADDS.pop(user.id)
    data = load_series_data()
    if series not in data:
        data[series] = {}
    data[series][ep] = {
        "chat_id": update.message.forward_from_chat.id,
        "message_id": update.message.forward_from_message_id
    }
    save_series_data(data)
    log_usage(user, "saved_episode", f"{series} - {ep}")
    await update.message.reply_text(f"✅ تم حفظ الحلقة {ep} لمسلسل {series}")

async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        await update.message.reply_text("⚠️ لازم تشترك في القناة.")
        return
    log_usage(user, "list_series")

    data = load_series_data()
    if not data:
        await update.message.reply_text("❌ مفيش بيانات.")
        return

    text = "📚 قائمة المسلسلات والحلقات:\n\n"
    for series, episodes in data.items():
        ep_list = ", ".join(sorted(episodes.keys(), key=lambda x: int(x)))
        text += f"• {series} ({len(episodes)} حلقات): {ep_list}\n"
    await update.message.reply_text(text)

async def delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("❌ مش مسموحلك.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدم كده:\n`/delete اسم_المسلسل رقم_الحلقة`", parse_mode="Markdown")
        return

    series, ep = context.args[0], context.args[1]
    data = load_series_data()
    if series in data and ep in data[series]:
        del data[series][ep]
        if not data[series]:
            del data[series]
        save_series_data(data)
        log_usage(user, "delete_episode", f"{series} - {ep}")
        await update.message.reply_text(f"🗑️ تم حذف الحلقة {ep} من {series}")
    else:
        await update.message.reply_text("❌ الحلقة أو المسلسل غير موجود.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return await update.message.reply_text("❌ مش مسموحلك.")

    data = load_series_data()
    users = set()
    logs = []
    if os.path.exists(USAGE_LOG_FILE):
        with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
            users = {entry["user_id"] for entry in logs}

    await update.message.reply_text(f"""📊 لوحة التحكم:

• عدد المسلسلات: {len(data)}
• عدد الحلقات: {sum(len(e) for e in data.values())}
• عدد المستخدمين: {len(users)}

🧾 /logs - سجل الاستخدام الكامل
""")

async def logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        return
    if not os.path.exists(USAGE_LOG_FILE):
        return await update.message.reply_text("📄 مفيش سجل حتى الآن.")

    with open(USAGE_LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)

    if not logs:
        return await update.message.reply_text("📄 السجل فاضي.")

    logs_text = ""
    for entry in logs:
        logs_text += f"{entry['timestamp']} - {entry['name']} @{entry['username']}: {entry['action']} {entry['extra']}\n"

    await update.message.reply_text(f"📋 سجل المستخدمين:\n\n{logs_text[:4000]}")

# ========== تشغيل البوت ==========
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_series))
app.add_handler(CommandHandler("delete", delete_episode))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CommandHandler("logs", logs_command))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.FORWARDED, handle_forward))

print("✅ البوت شغّال...")
app.run_polling()
