from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
import os

TOKEN = '7820235468:AAFLoJXoVYGrcpw7B_dx4BlTXKFfEkpexjc'
BOT_USERNAME = 'DeAlbora_Bot'

# الكلمات المستهدفة + الرد + الرابط
KEYWORD_RESPONSE_MAP = {
    ('رابط المدينة', 'جروب المدينة', 'رابط المدينه' , 'جروب المدينه'): ('🪁 جروب حلقات المدينة البعيدة', 'https://t.me/+qxxf6IA2SpwzMmE0'),
    ('المدينة منخفضة', 'المدينه منخفضه'): ('🔻جروب حلقات المدينة جودة منخفضة! ', 'https://t.me/+w5efATshnAphMGQ0'),
    ('جروب قطاع', 'رابط قطاع'): ('🥷🏻 جروب حلقات قطاع الطرق', 'https://t.me/+uSYEbwXR-QUyNmQ0'),
    ('جروب القضاء', 'رابط القضاء', 'رابط القضاء'): ('⚖️ جروب حلقات القضاء', 'https://t.me/+E2HH96rg-bFlMTdk'),
    ('رابط طبيب', 'جروب طبيب', 'رابط طبيب القريه'): ('🩺 جروب حلقات طبيب القرية', 'https://t.me/+pjF4F_3WhlxlNTZk'),
    ('جروب حلم', 'رابط حلم اشرف'): ('🌙 جروب حلقات حلم اشرف', 'https://t.me/+QI4yXLDVSHAzZDA8'),
    ('حلم منخفضة', 'حلم منخفضه'): ('🌙 جروب حلقات حلم اشرف جودة منخفضة', 'https://t.me/+0Hr7MH_zLA9lNmZk'),
    ('جروب ليلى', 'رابط ليلي' , 'رابط ليلي'): ('👧 جروب حلقات ليلى', 'https://t.me/+5gIkrQXXQU5jZjhk'),
    ('رابط الغرفة', 'جروب الغرفه', 'جروب الغرفة', 'رابط الغرفه', 'جروب غرفة', 'رابط غرفه'): ('👫 جروب حلقات الغرفة المزدوجة', 'https://t.me/+ZVUyO73yR7pmMmE0'),
    ('رابط العبقري', 'جروب العبقري' , 'جروب العبقرى' , 'رابط العبقرى'): ('🧠 جروب حلقات العبقري', 'https://t.me/+4pbDVBfQMB4zNzA0'),
    ('رابط القبعة', 'رابط القبعه', 'جروب القبعة', 'جروب القبعه'): ('🎩 جروب حلقات القبعة السوداء', 'https://t.me/+d7V-lHuQhThjN2U0'),
    ('رابط حكاية', 'جروب حكايه', 'حلقات حكايه', 'حلقات حكاية'): ('👩‍❤️‍👨 جروب حلقات حكاية ليلة', 'https://t.me/+5ZaDx8rIzPEzN2I0'),
    ('رابط المشردون', 'رابط المتشردون', 'جروب المتشردون', 'جروب المشردون', 'رابط المتشردين', 'جروب المتشردين'): ('🫂 جروب حلقات المشردون', 'https://t.me/+pSbam4z-FFlhMjA0'),

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
        "لو لسه مش بدأ محادثة خاصة معايا، دوس هنا: https://t.me/AlboranBot"
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
                    f"⚠️ لازم تبدأ محادثة خاصة مع البوت الأول اضغط على الرابط ثم (اضغط Start او بدء) بعدها ارجع الجروب هنا واكتب نفس الامر تاني: https://t.me/{BOT_USERNAME}"
                )
                print("❗ المستخدم لم يبدأ محادثة مع البوت")
                return

# تشغيل البوت
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("help", help_command))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ البوت شغّال... مستني رسائل...")
app.run_polling()
