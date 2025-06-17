from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os

TOKEN = "7820235468:AAFLoJXoVYGrcpw7B_dx4BlTXKFfEkpexjc"
ADMIN_IDS = [829510841]
channel_id = -1002698646841  # ← حط هنا الشات ID الخاص بقناتك

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
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_series")])
    return buttons

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_user_subscribed(user_id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="recheck_sub")]
        ])
        await update.message.reply_text(
            "⚠️ لازم تشترك في القناة الأول.\n📢 https://t.me/اسم_القناة_بتاعتك",
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

# باقي أوامر /add و /list و /delete و /admin تفضل كما هي، بدون تغيير
# تقدر تضيفهم تحت بنفس الشكل اللي عملناه قبل كده

# نهاية الملف:
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
