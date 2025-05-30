from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TOKEN = '7626736625:AAE5tyStesP1LWu9rYsdCy03HLI6kcywF24'
BOT_USERNAME = 'AlboraninBot'

KEYWORD_LINK_MAP = {
    ('جروب حلقات المدينة البعيدة', 'حلقات المدينة', 'جروب المدينة'): 'https://t.me/+evUItbGXkRU3YTE0',
    ('جروب المدينة منخفضة', 'المدينة البعيدة جودة', 'المدينة البعيدة منخفضة'): 'https://t.me/+w5efATshnAphMGQ0',
    ('جروب قطاع الطرق', 'جروب قطاع'): 'https://t.me/+5W6dd6X45N0zOTVk',
    ('جروب القضاء', 'القضاء'): 'https://t.me/+B0OVr5ulErxjMjU0',
    ('طبيب القرية', 'طبيب البلدة', 'جروب طبيب'): 'https://t.me/+lm_X8yn8eVw2OTE8',
    ('جروب حلم اشرف', 'رابط حلم', 'جروب رؤية'): 'https://t.me/+-sOunO8YnMdiOTE0',
    ('جروب ليلى', 'رابط ليلى', 'مسلسل ليلى'): 'https://t.me/+1IYRMalAuTw4YTA0',
    ('جروب العبقري', 'رابط العبقري', 'مسلسل العبقري'): 'https://t.me/+k9XFpNcsreZlNWE8',
    ('جروب القبعة', 'حلقات القبعة', 'مسلسل القبعة السوداء'): 'https://t.me/+RnOqk1eJnR0yMDRk',
  }

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    print(f"📥 رسالة وصلت: {text}")

    for keywords, link in KEYWORD_LINK_MAP.items():
        if any(keyword.lower() in text for keyword in keywords):
            try:
                await context.bot.send_message(
                    chat_id=update.message.from_user.id,
                    text=f"أهلاً! تقدر تنضم من هنا: {link}",
                    disable_web_page_preview=True
                )
                print(f"📩 تم إرسال رابط ({link}) لـ {update.message.from_user.username or update.message.from_user.first_name}")
                return  # وقف عند أول مجموعة كلمات متطابقة

            except:
                await update.message.reply_text(
                    f"⚠️ لازم تبدأ محادثة خاصة مع البوت الأول (اضغط Start): https://t.me/{BOT_USERNAME}"
                )
                print("❗ المستخدم لم يبدأ محادثة مع البوت")
                return

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("✅ البوت شغال... مستني رسائل...")
app.run_polling()
