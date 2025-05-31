from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import os

TOKEN = '7626736625:AAE5tyStesP1LWu9rYsdCy03HLI6kcywF24'
BOT_USERNAME = 'AlboraninBot'

# الكلمات المستهدفة + الرد + الرابط
KEYWORD_RESPONSE_MAP = {
    ('رابط المدينة', 'رابط المدينه'): ('🎯 رابط المدينة', 'https://t.me/+evUItbGXkRU3YTE0'),
    ('المدينة منخفضة', 'المدينه منخفضه'): ('🔻 المدينة منخفضة! ادخل بسرعة', 'https://t.me/+w5efATshnAphMGQ0'),
    ('رابط قطاع',): ('📦 ده رابط القطاع', 'https://t.me/+5W6dd6X45N0zOTVk'),
    ('رابط القضاء',): ('⚖️ جروب القضاء موجود هنا', 'https://t.me/+B0OVr5ulErxjMjU0'),
    ('رابط طبيب القرية', 'رابط طبيب القريه'): ('🩺 طبيب القرية في انتظارك', 'https://t.me/+lm_X8yn8eVw2OTE8'),
    ('رابط حلم اشرف',): ('🌙 حلم أشرف؟ اتفضل', 'https://t.me/+-sOunO8YnMdiOTE0'),
    ('رابط ليلى', 'رابط ليلي'): ('👧 رابط ليلى هنا', 'https://t.me/+1IYRMalAuTw4YTA0'),
    ('رابط العبقري', 'رابط العبقرى'): ('🧠 العبقري جاهز يستقبلك', 'https://t.me/+k9XFpNcsreZlNWE8'),
    ('رابط القبعة', 'رابط القبعه', 'رابط القبعة السوداء', 'رابط القبعه السوداء'): ('🎩 القبعة السوداء بتاعتك هنا', 'https://t.me/+RnOqk1eJnR0yMDRk'),
}

# تسجيل المستخدمين في ملف بسيط
def log_user(user):
    with open("users_log.txt", "a", encoding="utf-8") as f:
        name = user.username or f"{user.first_name} {user.last_name or ''}"
        f.write(f"{name} - ID: {user.id}\n")

# أمر /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بيك! ابعتلي اسم المجموعة أو الرابط اللي بتدور عليه، وأنا هبعتهولك على الخاص.\n\n"
        "لو لسه مش بدأ محادثة خاصة معايا، دوس هنا: https://t.me/AlboraninBot"
    )

# التعامل مع الرسائل العادية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    user = update.message.from_user
    print(f"📥 رسالة وصلت: {text} من {user.username or user.first_name}")

    for keywords, (reply_text, link) in KEYWORD_RESPONSE_MAP.items():
        if any(keyword.lower() in text for keyword in keywords):
            try:
                keyboard = InlineKeyboardMarkup.from_button(
                    InlineKeyboardButton("📎 انضم للجروب", url=link)
                )
                await context.bot.send_message(
                    chat_id=user.id,
                    text=reply_text,
                    reply_markup=keyboard
                )
                log_user(user)
                print(f"📩 أرسل رابط ({link}) لـ {user.username or user.first_name}")
                return

            except:
                await update.message.reply_text(
                    f"⚠️ لازم تبدأ محادثة خاصة مع البوت الأول (اضغط Start): https://t.me/{BOT_USERNAME}"
                )
                print("❗ المستخدم لم يبدأ محادثة مع البوت")
                return

# تشغيل البوت
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ البوت شغّال... مستني رسائل...")
app.run_polling()
