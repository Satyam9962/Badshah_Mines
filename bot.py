import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from utils import generate_prediction_image, get_safe_tiles
from datetime import datetime, timedelta
import os, json, io

# --- Configuration ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PASSKEY_BASIC = os.environ.get("PASSKEY_BASIC")
PASSKEY_KING = os.environ.get("PASSKEY_KING")
DATA_FILE = "data.json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- States ---
CHOOSE_PLAN, ENTER_PASSKEY, ENTER_SEED = range(3)

# --- Helpers ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_limits(plan):
    return {"basic": (15, 20), "king": (31, 45)}[plan]

def is_plan_active(user, data):
    info = data.get(str(user.id))
    if not info:
        return False
    if datetime.utcnow() > datetime.fromisoformat(info["expiry"]):
        return False
    if datetime.utcnow().date() > datetime.fromisoformat(info["last_used"]).date():
        info["daily_used"] = 0
    return True

def update_usage(user, data):
    data[str(user.id)]["daily_used"] += 1
    data[str(user.id)]["last_used"] = datetime.utcnow().isoformat()

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Mines Basic", callback_data="basic")],
        [InlineKeyboardButton("Mines King 👑", callback_data="king")]
    ]
    await update.message.reply_text(
    "Welcome to Stake Mines Predictor Bot!\nChoose your plan:",
    reply_markup=InlineKeyboardMarkup(keyboard)
)
return CHOOSE_PLAN

async def choose_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan = update.callback_query.data
    context.user_data["plan"] = plan
    await update.callback_query.message.reply_text("Please enter your passkey:")
    return ENTER_PASSKEY

async def enter_passkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_passkey = update.message.text.strip()
    plan = context.user_data["plan"]
    expected = PASSKEY_BASIC if plan == "basic" else PASSKEY_KING
    if user_passkey != expected:
        await update.message.reply_text("❌ Invalid passkey. Try again.")
        return ENTER_PASSKEY
    days, _ = get_limits(plan)
    expiry = datetime.utcnow() + timedelta(days=days)
    user_id = str(update.effective_user.id)
    data = load_data()
    data[user_id] = {"plan": plan, "expiry": expiry.isoformat(), "daily_used": 0, "last_used": datetime.utcnow().isoformat()}
    save_data(data)
    await update.message.reply_text(f"✅ Access granted for {plan.title()} plan until {expiry.date()}.
Now send your client seed:")
    return ENTER_SEED

async def enter_seed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if not is_plan_active(update.effective_user, data):
        await update.message.reply_text("❌ Your plan has expired or not active. Please restart with /start.")
        return ConversationHandler.END
    plan = data[user_id]["plan"]
    _, max_per_day = get_limits(plan)
    if data[user_id]["daily_used"] >= max_per_day:
        await update.message.reply_text("⛔ You’ve reached your daily limit. Try again tomorrow.")
        return ConversationHandler.END
    seed = update.message.text.strip()
    safe_tiles = get_safe_tiles(seed)
    img = generate_prediction_image(safe_tiles)
    bio = io.BytesIO()
    img.save(bio, format='PNG')
    bio.seek(0)
    update_usage(update.effective_user, data)
    save_data(data)
    await update.message.reply_photo(photo=bio, caption=f"✅ Safe tiles based on your seed.
💎 Safe Tiles: {sorted(safe_tiles)}")
    await update.message.reply_text("🔁 Send another client seed or type /start to restart.")
    return ENTER_SEED

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        await update.message.reply_text("❌ You don’t have an active plan.")
        return
    info = data[user_id]
    expiry = datetime.fromisoformat(info["expiry"]).date()
    used = info["daily_used"]
    _, max_per_day = get_limits(info["plan"])
    await update.message.reply_text(f"📊 Plan: {info['plan'].title()}
📅 Expiry: {expiry}
🔢 Signals Used Today: {used}/{max_per_day}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# --- Main ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_PLAN: [CallbackQueryHandler(choose_plan)],
            ENTER_PASSKEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_passkey)],
            ENTER_SEED: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_seed)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("status", status))

    app.run_polling()

if __name__ == "__main__":
    main()
