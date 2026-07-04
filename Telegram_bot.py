from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json
import os
import random
from datetime import datetime
import logging

# ---------------- CONFIG ----------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "arcade_users_tg.json"

# ---------------- LOGGING ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ---------------- DATA ----------------
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

users = load_users()

def save_users():
    global users
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_user(user_id):
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "coins": 500,
            "xp": 0,
            "ref_code": f"TG{user_id % 10000:04d}",
            "referrals": [],
            "stats": {
                "games_played": 0,
                "total_wagered": 0,
                "biggest_win": 0,
                "last_daily": None
            }
        }
        save_users()

    return users[uid]

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)

    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🎲 Dice", callback_data="dice_demo")],
        [InlineKeyboardButton("🎰 Slots", callback_data="slots_demo")],
        [InlineKeyboardButton("💣 Mines Info", callback_data="mines_info")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")]
    ]

    await update.message.reply_text(
        f"🎰 *TokenArcade Bot*\n\n"
        f"Hi {update.effective_user.first_name}!\n\n"
        f"💰 Coins: `{user['coins']}`\n"
        f"🎮 Games: `{user['stats']['games_played']}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ---------------- HELP ----------------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """
🎮 Commands:

/start - Menu
/balance - Coins
/daily - Free coins
/mines 50 5
/slots 50
/keno 50
/dice 50 high
        """,
        parse_mode="Markdown"
    )

# ---------------- BALANCE ----------------
async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    level = (user["xp"] // 500) + 1

    await update.message.reply_text(
        f"💰 Balance: `{user['coins']}`\n"
        f"📊 Level: `{level}`\n"
        f"🎮 Games: `{user['stats']['games_played']}`",
        parse_mode="Markdown"
    )

# ---------------- DAILY ----------------
async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    today = datetime.now().date().isoformat()

    if user["stats"]["last_daily"] == today:
        await update.message.reply_text("❌ Already claimed today.")
        return

    user["coins"] += 50
    user["stats"]["last_daily"] = today
    save_users()

    await update.message.reply_text("✅ +50 coins claimed!")

# ---------------- MINES ----------------
async def mines_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /mines 50 5")
        return

    bet = int(context.args[0])
    bombs = int(context.args[1])

    user = get_user(update.effective_user.id)

    if bet > user["coins"]:
        await update.message.reply_text("❌ Not enough coins")
        return

    user["coins"] -= bet

    safe = random.randint(1, 5)
    hit = random.random() < 0.4

    if hit:
        result = f"💥 BOOM! Lost {bet}"
    else:
        win = bet * random.randint(2, 5)
        user["coins"] += win
        result = f"✅ Won {win}"

    user["stats"]["games_played"] += 1
    save_users()

    await update.message.reply_text(result)

# ---------------- SLOTS ----------------
async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /slots 50")
        return

    bet = int(context.args[0])
    user = get_user(update.effective_user.id)

    if bet > user["coins"]:
        await update.message.reply_text("❌ Not enough coins")
        return

    user["coins"] -= bet

    symbols = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
    r = [random.choice(symbols) for _ in range(3)]

    mult = 0
    if r[0] == r[1] == r[2]:
        mult = 10
    elif r[0] == r[1] or r[1] == r[2]:
        mult = 2

    win = bet * mult
    user["coins"] += win

    save_users()

    await update.message.reply_text(
        f"🎰 {''.join(r)}\n"
        f"Won: {win}"
    )

# ---------------- DICE ----------------
async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /dice 50 high")
        return

    bet = int(context.args[0])
    guess = context.args[1]

    user = get_user(update.effective_user.id)

    if bet > user["coins"]:
        await update.message.reply_text("❌ Not enough coins")
        return

    user["coins"] -= bet

    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2

    high = total >= 7
    win = (high and guess == "high") or (not high and guess == "low")

    payout = bet * 2 if win else 0
    user["coins"] += payout

    save_users()

    await update.message.reply_text(
        f"🎲 {d1}+{d2}={total}\n"
        f"{'WIN' if win else 'LOSE'}"
    )

# ---------------- CALLBACKS ----------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = get_user(q.from_user.id)

    if q.data == "balance":
        await q.edit_message_text(f"💰 Coins: {user['coins']}")

    elif q.data == "profile":
        await q.edit_message_text(
            f"👤 Profile\nCoins: {user['coins']}\nGames: {user['stats']['games_played']}"
        )

    elif q.data == "dice_demo":
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        await q.edit_message_text(f"🎲 {d1}+{d2}")

    elif q.data == "slots_demo":
        symbols = ["🍒", "🍋", "🍊", "💎", "7️⃣"]
        r = [random.choice(symbols) for _ in range(3)]
        await q.edit_message_text("🎰 " + "".join(r))

    elif q.data == "mines_info":
        await q.edit_message_text("💣 /mines 50 5")

    elif q.data == "leaderboard":
        top = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)[:5]
        text = "🏆 Top Players\n\n"
        for i, (uid, u) in enumerate(top, 1):
            text += f"{i}. {uid[:4]} - {u['coins']}\n"

        await q.edit_message_text(text)

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("mines", mines_cmd))
    app.add_handler(CommandHandler("slots", slots_cmd))
    app.add_handler(CommandHandler("dice", dice_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 Bot running...")

    # ✅ FIXED: correct polling method
    app.run_polling()

if __name__ == "__main__":
    main()
