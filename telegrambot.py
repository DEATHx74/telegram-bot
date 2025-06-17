from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os

TOKEN = "7820235468:AAFLoJXoVYGrcpw7B_dx4BlTXKFfEkpexjc"
ADMIN_IDS = [829510841]
channel_id = -1002698646841  # ← الشات ID بتاع القناة

DATA_FILE = "series_data.json"
PENDING_ADDS = {}

def load_series_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_series_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def is_admin(user_id):
    return user_id in ADMIN_IDS

def generate_episode_buttons(episodes: dict, series_name: str, per_row: int = 4):
    keys_sorted = sorted(episodes.keys(), key=lambda x: int(x) if x.isdigit() else x)
    buttons = []
    for i in range(0, len(keys_sorted), per_row):
        row = [
            InlineKeyboardButton(f"{ep}", callback_data=f"episode|{series_name}|{ep}")
            for ep in keys_sorted[i:i+per_row]
        ]
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_series"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")
    ])
    return buttons

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(user_id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="recheck_sub")]
        ])
        await update.message.reply_text(
            "⚠️ لازم تشترك في القناة الأول.\n📢 https://t.me/AlboraninTV",
            reply_markup=keyboard
        )
        return

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
    series_data = load_series_data()

    if data == "recheck_sub":
        user_id = query.from_user.id
        if not await is_user_subscribed(user_id, context):
            await query.message.reply_text("⚠️ لسه مش مشترك أو التحقق اتأخر شوية. حاول تاني بعد شوية.")
            return
        await start(update, context)
        return

    if data in ["back_to_series", "back_to_main"]:
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

        await context.bot.forward_message(
            chat_id=query.message.chat_id,
            from_chat_id=episode["chat_id"],
            message_id=episode["message_id"]
        )

        # عرض قائمة الحلقات مرة تانية بعد المشاهدة
        episodes = series_data.get(series_name, {})
        buttons = generate_episode_buttons(episodes, series_name)
        await query.message.reply_text(
            f"🎬 اختر حلقة تانية من {series_name}:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(user_id, context):
        await update.message.reply_text("⚠️ لازم تشترك في القناة.\n📢 https://t.me/AlboraninTV")
        return
    if not is_admin(user_id):
        await update.message.reply_text("❌ مش مسموحلك تستخدم الأمر ده.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("❗ استخدم الأمر كده:\n`/add اسم_المسلسل رقم_الحلقة`", parse_mode="Markdown")
        return

    series_name = context.args[0]
    episode_number = context.args[1]
    PENDING_ADDS[user_id] = (series_name, episode_number)
    await update.message.reply_text(f"✅ تمام، ابعتلي الحلقة (فورورد من الجروب) كحلقة {episode_number} لمسلسل {series_name}")

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in PENDING_ADDS:
        return

    if not update.message.forward_from_chat:
        await update.message.reply_text("⚠️ لازم تبعتلي الرسالة كـ *Forward* من الجروب.", parse_mode="Markdown")
        return

    series_name, episode_number = PENDING_ADDS.pop(user_id)
    series_data = load_series_data()

    if series_name not in series_data:
        series_data[series_name] = {}

    series_data[series_name][episode_number] = {
        "chat_id": update.message.forward_from_chat.id,
        "message_id": update.message.forward_from_message_id
    }

    save_series_data(series_data)
    await update.message.reply_text(f"✅ تم حفظ الحلقة {episode_number} لمسلسل {series_name}")

async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(user_id, context):
        await update.message.reply_text("⚠️ لازم تشترك في القناة.\n📢 https://t.me/AlboraninTV")
        return

    series_data = load_series_data()
    if not series_data:
        await update.message.reply_text("❌ مفيش بيانات حالياً.")
        return

    text = "📚 قائمة المسلسلات والحلقات:\n\n"
    for series, episodes in series_data.items():
        ep_list = ", ".join(sorted(episodes.keys(), key=lambda x: int(x) if x.isdigit() else x))
        text += f"• {series} ({len(episodes)} حلقات): {ep_list}\n"
    await update.message.reply_text(text)

async def delete_episode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
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
        await update.message.reply_text(f"🗑️ تم حذف الحلقة {episode_number} من {series_name}.")
    else:
        await update.message.reply_text("❌ الحلقة أو المسلسل غير موجود.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ مش مسموحلك.")
        return

    data = load_series_data()
    total_series = len(data)
    total_episodes = sum(len(episodes) for episodes in data.values())

    text = f"""📊 لوحة تحكم البوت:

• عدد المسلسلات: {total_series}
• عدد الحلقات: {total_episodes}

🕹️ التحكم:
- /list : عرض الحلقات
- /add : إضافة
- /delete : حذف
"""
    await update.message.reply_text(text)

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
