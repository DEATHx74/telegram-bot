
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import json

TOKEN = "7820235468:AAFLoJXoVYGrcpw7B_dx4BlTXKFfEkpexjc"

def load_series_data():
    with open("series_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    series_data = load_series_data()
    buttons = [
        [InlineKeyboardButton(series_name, callback_data=f"series|{series_name}")]
        for series_name in series_data
    ]
    await update.message.reply_text(
        "📺 اختر المسلسل اللي عايز تشوفه:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# زر المسلسل أو رقم الحلقة
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("series|"):
        series_name = data.split("|")[1]
        series_data = load_series_data()
        if series_name not in series_data:
            await query.message.reply_text("❌ المسلسل غير موجود.")
            return

        episode_buttons = [
            [InlineKeyboardButton(f"حلقة {ep}", callback_data=f"episode|{series_name}|{ep}")]
            for ep in series_data[series_name]
        ]

        await query.message.reply_text(
            f"🎬 اختر الحلقة من {series_name}:",
            reply_markup=InlineKeyboardMarkup(episode_buttons)
        )

    elif data.startswith("episode|"):
        _, series_name, ep_number = data.split("|")
        series_data = load_series_data()
        episode = series_data.get(series_name, {}).get(ep_number)

        if not episode:
            await query.message.reply_text("⚠️ الحلقة غير موجودة.")
            return

        await context.bot.forward_message(
            chat_id=query.message.chat_id,
            from_chat_id=episode["chat_id"],
            message_id=episode["message_id"]
        )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))

print("✅ البوت النظيف شغال...")
app.run_polling()
