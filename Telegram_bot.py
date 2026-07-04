from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os, json, random
from datetime import datetime, timedelta

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "arcade_v3.json"

# ---------------- LOAD ----------------
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

users = load()

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

# ---------------- USER ----------------
def get(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "coins": 1000,
            "xp": 0,
            "level": 1,
            "rank": "Bronze",
            "streak": 0,
            "last_daily": None,
            "boost": 1.0,
            "stats": {
                "played": 0,
                "won": 0,
                "lost": 0,
                "biggest_win": 0
            }
        }
        save()

    return users[uid]

# ---------------- PROGRESSION ----------------
def update(u):
    u["level"] = (u["xp"] // 300) + 1

    ranks = [
        (1, "Bronze"),
        (5, "Silver"),
        (10, "Gold"),
        (20, "Diamond"),
        (35, "Master"),
        (60, "Legend")
    ]

    u["rank"] = "Bronze"
    for r in ranks:
        if u["level"] >= r[0]:
            u["rank"] = r[1]

# ---------------- UI ----------------
def home():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Games", callback_data="games")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance"),
         InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")],
        [InlineKeyboardButton("🛒 Shop", callback_data="shop")]
    ])

def games():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💣 Mines", callback_data="mines"),
         InlineKeyboardButton("🎰 Slots", callback_data="slots")],
        [InlineKeyboardButton("🎲 Dice", callback_data="dice"),
         InlineKeyboardButton("📈 Crash", callback_data="crash")],
        [InlineKeyboardButton("🎁 Daily", callback_data="daily")],
        [InlineKeyboardButton("⬅ Back", callback_data="home")]
    ])

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get(update.effective_user.id)

    await update.message.reply_text(
        f"🎰 *TOKEN ARCADE v3*\n\n"
        f"Coins: `{u['coins']}`\n"
        f"Level: `{u['level']}` | Rank: `{u['rank']}`\n"
        f"Streak: `{u['streak']}` 🔥",
        reply_markup=home(),
        parse_mode="Markdown"
    )

# ---------------- BALANCE ----------------
async def balance(update, context):
    u = get(update.effective_user.id)

    await update.message.reply_text(
        f"💰 Coins: `{u['coins']}`\n"
        f"⚡ Boost: `{u['boost']}x`",
        reply_markup=home(),
        parse_mode="Markdown"
    )

# ---------------- PROFILE ----------------
async def profile(update, context):
    u = get(update.effective_user.id)

    await update.message.reply_text(
        f"👤 Profile\n\n"
        f"Level: `{u['level']}`\n"
        f"Rank: `{u['rank']}`\n"
        f"Games: `{u['stats']['played']}`\n"
        f"Wins: `{u['stats']['won']}` | Losses: `{u['stats']['lost']}`\n"
        f"Biggest Win: `{u['stats']['biggest_win']}`",
        reply_markup=home(),
        parse_mode="Markdown"
    )

# ---------------- DAILY ----------------
async def daily(update, context):
    u = get(update.effective_user.id)
    today = datetime.now().date().isoformat()

    if u["last_daily"] == today:
        return await update.message.reply_text("❌ Already claimed")

    reward = int(200 * u["boost"])
    u["coins"] += reward
    u["last_daily"] = today
    u["streak"] += 1

    if u["streak"] % 7 == 0:
        u["coins"] += 500

    save()

    await update.message.reply_text(f"🎁 +{reward} coins")

# ---------------- GAMES ----------------
def bet_ok(u, bet):
    return bet <= u["coins"] and bet > 0

# ---------------- MINES ----------------
async def mines(update, context):
    u = get(update.effective_user.id)
    bet = 50

    if not bet_ok(u, bet):
        return await update.message.reply_text("❌ Not enough coins")

    u["coins"] -= bet

    safe = random.randint(1, 4)
    win = bet * (1 + safe) * u["boost"]

    if random.random() < 0.35:
        result = f"💥 BOOM -{bet}"
        u["stats"]["lost"] += 1
    else:
        u["coins"] += int(win)
        result = f"✅ +{int(win)}"
        u["stats"]["won"] += 1

    u["stats"]["played"] += 1
    u["xp"] += 20
    update(u)
    save()

    await update.message.reply_text(result, reply_markup=games())

# ---------------- SLOTS ----------------
async def slots(update, context):
    u = get(update.effective_user.id)
    bet = 50

    if not bet_ok(u, bet):
        return await update.message.reply_text("❌ Not enough coins")

    u["coins"] -= bet

    s = ["🍒","🍋","🍊","💎","7️⃣"]
    r = [random.choice(s) for _ in range(3)]

    mult = 0
    if r[0] == r[1] == r[2]:
        mult = 25
    elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
        mult = 2

    win = int(bet * mult * u["boost"])

    u["coins"] += win

    u["xp"] += 15
    update(u)
    save()

    await update.message.reply_text(f"🎰 {''.join(r)}\n+{win}", reply_markup=games())

# ---------------- DICE ----------------
async def dice(update, context):
    u = get(update.effective_user.id)
    bet = 50

    if not bet_ok(u, bet):
        return await update.message.reply_text("❌ Not enough coins")

    u["coins"] -= bet

    a, b = random.randint(1,6), random.randint(1,6)
    total = a + b

    win = total >= 7

    payout = int(bet * 2 * u["boost"]) if win else 0
    u["coins"] += payout

    u["xp"] += 10
    update(u)
    save()

    await update.message.reply_text(f"🎲 {a}+{b}={total}\n{'WIN' if win else 'LOSE'}")

# ---------------- CRASH ----------------
async def crash(update, context):
    u = get(update.effective_user.id)
    bet = 50

    if not bet_ok(u, bet):
        return await update.message.reply_text("❌ Not enough coins")

    u["coins"] -= bet

    mult = round(random.uniform(1, 6), 2)
    cash = random.choice([True, False])

    if cash:
        win = int(bet * mult * u["boost"])
        u["coins"] += win
        msg = f"📈 x{mult} → +{win}"
    else:
        u["stats"]["lost"] += 1
        msg = f"💥 CRASH x{mult}"

    u["xp"] += 25
    update(u)
    save()

    await update.message.reply_text(msg, reply_markup=games())

# ---------------- CALLBACKS ----------------
async def cb(update, context):
    q = update.callback_query
    await q.answer()

    u = get(q.from_user.id)

    if q.data == "home":
        await q.edit_message_text("🏠 Home", reply_markup=home())

    elif q.data == "games":
        await q.edit_message_text("🎮 Games", reply_markup=games())

    elif q.data == "balance":
        await q.edit_message_text(f"💰 {u['coins']}", reply_markup=home())

    elif q.data == "profile":
        await q.edit_message_text(
            f"👤 Level {u['level']} | {u['rank']}",
            reply_markup=home()
        )

    elif q.data == "leaderboard":
        top = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)[:5]
        text = "🏆 Top\n\n"
        for i,(id,u2) in enumerate(top,1):
            text += f"{i}. {id[:4]} - {u2['coins']}\n"
        await q.edit_message_text(text, reply_markup=home())

    elif q.data == "shop":
        await q.edit_message_text(
            "🛒 Shop\n\nBoost 2x = 2000 coins\n(Not implemented fully yet)",
            reply_markup=home()
        )

    elif q.data == "mines":
        await mines(update, context)

    elif q.data == "slots":
        await slots(update, context)

    elif q.data == "dice":
        await dice(update, context)

    elif q.data == "crash":
        await crash(update, context)

    elif q.data == "daily":
        await daily(update, context)

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("daily", daily))

    app.add_handler(CallbackQueryHandler(cb))

    print("🚀 TOKEN ARCADE v3 LIVE")
    app.run_polling()

if __name__ == "__main__":
    main()
