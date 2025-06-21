# ✅ Telegram Bot - تعديل لعرض المسلسل ← المواسم ← الحلقات

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import json, os
from datetime import datetime

TOKEN = "7912558360:AAFkL8lE2GKFM6Nhu6Ze2XhrP2q5lpJLtMI"
ADMIN_IDS = [829510841]
channel_id = -1002698646841
DATA_FILE = "series_data_nested.json"
USAGE_LOG_FILE = "usage_log.json"
PENDING_ADDS = {}
EPISODES_PER_PAGE = 20

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

# ========== توليد أزرار المواسم والحلقات ==========
def generate_season_buttons(series_data, series_name):
    return [[InlineKeyboardButton(season_name, callback_data=f"season|{series_name}|{season_name}")]
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
            InlineKeyboardButton(f"حلقة {int(ep)}", callback_data=f"episode|{series_name}|{season_name}|{ep}")
            for ep in paginated[i:i + per_row]
        ]
        buttons.append(row)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"season|{series_name}|{season_name}|{page-1}"))
    if end < total:
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"season|{series_name}|{season_name}|{page+1}"))
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"back_to_seasons|{series_name}")])
    return buttons

# ========== /start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not await is_user_subscribed(user.id, context):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢إشترك في القناة من هنا", url="https://t.me/AlboraninTV")],
            [InlineKeyboardButton("👥 إشترك في الجروب", url="https://t.me/+sRMVn6ImJoRhMTU0")]
        ])
        await update.message.reply_text("⚠️ لازم تشترك في القناة عشان تقدر تستخدم البوت.", reply_markup=keyboard)
        return
    log_usage(user, "start")
    series_data = load_series_data()
    if not series_data:
        await update.message.reply_text("📂 مفيش مسلسلات مضافة حتى الآن.")
        return
    buttons = [[InlineKeyboardButton(series_name, callback_data=f"series|{series_name}")]
               for series_name in series_data]
    await update.message.reply_text("📺 اختار المسلسل اللي عايز تشوفه:", reply_markup=InlineKeyboardMarkup(buttons))

# ========== الضغطات ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    series_data = load_series_data()

    if data == "back_to_series":
        buttons = [[InlineKeyboardButton(series_name, callback_data=f"series|{series_name}")]
                   for series_name in series_data]
        await query.message.edit_text("📺 اختار المسلسل اللي عايز تشوفه:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("back_to_seasons|"):
        _, series_name = data.split("|")
        buttons = generate_season_buttons(series_data, series_name)
        await query.message.edit_text(f"📂 اختار الموسم من {series_name}:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("series|"):
        _, series_name = data.split("|")
        buttons = generate_season_buttons(series_data, series_name)
        await query.message.edit_text(f"📂 اختار الموسم من {series_name}:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("season|"):
        parts = data.split("|")
        series_name = parts[1]
        season_name = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0
        episodes = series_data[series_name][season_name]
        buttons = generate_episode_buttons(episodes, series_name, season_name, page)
        await query.message.edit_text(f"🎬 اختار الحلقة من {series_name} - {season_name}:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("episode|"):
        _, series_name, season_name, ep_number = data.split("|")
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
