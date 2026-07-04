import os
import json
import random
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "arcade_final.json"

# ---------------- DATA ----------------
users = {}
active_games = {}

def load():
    global users
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            users = json.load(f)

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "coins": 1000,
            "xp": 0,
            "level": 1,
            "rank": "Bronze",
            "boost": 1.0,
            "streak": 0,
            "last_daily": None,
            "last_play": None,
            "admin": False,
            "stats": {"played": 0, "wins": 0, "losses": 0}
        }
        save()

    return users[uid]

def update(u):
    u["level"] = (u["xp"] // 300) + 1
    ranks = [(1,"Bronze"),(5,"Silver"),(10,"Gold"),(20,"Diamond"),(40,"Master")]
    u["rank"] = "Bronze"
    for r in ranks:
        if u["level"] >= r[0]:
            u["rank"] = r[1]

# ---------------- UI ----------------
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Games", callback_data="games")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance"),
         InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("🛒 Shop", callback_data="shop")]
    ])

def games_menu():
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
        f"🎰 TOKEN ARCADE\n\n"
        f"Coins: {u['coins']}\n"
        f"Level: {u['level']} | {u['rank']}",
        reply_markup=main_menu()
    )

# ---------------- DAILY ----------------
async def daily(update, context):
    u = get(update.effective_user.id)
    today = datetime.now().date().isoformat()

    if u["last_daily"] == today:
        return await update.message.reply_text("❌ Already claimed")

    reward = int(200 * u["boost"] + u["streak"] * 20)
    u["coins"] += reward
    u["last_daily"] = today
    u["streak"] += 1

    save()
    await update.message.reply_text(f"🎁 +{reward} coins (streak {u['streak']})")

# ---------------- MINES ----------------
def make_mines():
    return set(random.sample(range(25), 5))

def render_board(mines, revealed, dead=False):
    text = "💣 MINES\n"
    for i in range(25):
        if i % 5 == 0:
            text += "\n"
        if i in revealed:
            text += "💎 "
        else:
            text += "⬜ "
    return text

def mines_keyboard():
    buttons = []
    for i in range(25):
        buttons.append(InlineKeyboardButton("⬜", callback_data=f"m_{i}"))
    rows = [buttons[i:i+5] for i in range(0, 25, 5)]
    rows.append([InlineKeyboardButton("💸 Cashout", callback_data="m_cash")])
    return InlineKeyboardMarkup(rows)

def start_mines(uid, bet):
    active_games[uid] = {
        "bet": bet,
        "mines": make_mines(),
        "revealed": set()
    }

async def mines_start(update, context):
    u = get(update.effective_user.id)

    bet = 50
    if u["coins"] < bet:
        return await update.message.reply_text("❌ Not enough coins")

    u["coins"] -= bet
    save()

    start_mines(str(update.effective_user.id), bet)

    await update.message.reply_text("💣 Pick a tile:", reply_markup=mines_keyboard())

async def mines_click(update, context):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    u = get(uid)
    g = active_games.get(uid)

    if not g:
        return await q.edit_message_text("No game", reply_markup=games_menu())

    if q.data == "m_cash":
        win = len(g["revealed"]) * g["bet"]
        u["coins"] += win
        active_games.pop(uid, None)
        save()
        return await q.edit_message_text(f"💸 +{win}", reply_markup=games_menu())

    index = int(q.data.split("_")[1])

    if index in g["mines"]:
        active_games.pop(uid, None)
        save()
        return await q.edit_message_text("💥 BOOM!", reply_markup=games_menu())

    g["revealed"].add(index)

    await q.edit_message_text(render_board(g["mines"], g["revealed"]), reply_markup=mines_keyboard())

# ---------------- SLOTS ----------------
async def slots(update, context):
    u = get(update.effective_user.id)

    bet = 50
    if u["coins"] < bet:
        return await update.message.reply_text("❌ Not enough coins")

    u["coins"] -= bet

    symbols = ["🍒","🍋","🍊","💎","7️⃣"]
    msg = await update.message.reply_text("🎰 Spinning...")

    for _ in range(6):
        r = [random.choice(symbols) for _ in range(3)]
        await asyncio.sleep(0.2)
        await msg.edit_text("🎰 " + "".join(r))

    r = [random.choice(symbols) for _ in range(3)]

    mult = 0
    if r[0] == r[1] == r[2]:
        mult = 20
    elif r[0] == r[1] or r[1] == r[2]:
        mult = 3

    win = bet * mult
    u["coins"] += win

    save()
    await msg.edit_text(f"🎰 {''.join(r)}\n+{win}")

# ---------------- DICE (FIXED REAL TELEGRAM ANIMATION) ----------------
async def dice(update, context):
    msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎲")
    value = msg.dice.value

    u = get(update.effective_user.id)

    win = value >= 4
    payout = 100 if win else 0

    u["coins"] += payout
    save()

    await update.message.reply_text(f"{'WIN' if win else 'LOSE'} +{payout}")

# ---------------- CRASH ----------------
async def crash(update, context):
    u = get(update.effective_user.id)

    bet = 50
    if u["coins"] < bet:
        return await update.message.reply_text("❌ Not enough coins")

    u["coins"] -= bet

    msg = await update.message.reply_text("📈 Launching...")

    mult = 1.0
    for _ in range(6):
        mult += random.uniform(0.3, 1.5)
        await asyncio.sleep(0.25)
        await msg.edit_text(f"📈 x{mult:.2f}")

    if random.choice([True, False]):
        win = int(bet * mult)
        u["coins"] += win
        result = f"📈 +{win}"
    else:
        result = "💥 CRASH"

    save()
    await msg.edit_text(result)

# ---------------- CALLBACK ROUTER ----------------
async def cb(update, context):
    q = update.callback_query
    await q.answer()

    u = get(str(q.from_user.id))

    if q.data == "home":
        await q.edit_message_text("🏠 Home", reply_markup=main_menu())

    elif q.data == "games":
        await q.edit_message_text("🎮 Games", reply_markup=games_menu())

    elif q.data == "balance":
        await q.edit_message_text(f"💰 {u['coins']}", reply_markup=main_menu())

    elif q.data == "profile":
        await q.edit_message_text(f"👤 Level {u['level']} | {u['rank']}", reply_markup=main_menu())

    elif q.data == "leaderboard":
        top = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)[:5]
        text = "🏆 Top\n\n"
        for i,(id,u2) in enumerate(top,1):
            text += f"{i}. {id[:4]} - {u2['coins']}\n"
        await q.edit_message_text(text, reply_markup=main_menu())

    elif q.data == "shop":
        await q.edit_message_text("🛒 Shop coming soon", reply_markup=main_menu())

    elif q.data == "mines":
        await mines_start(update, context)

    elif q.data == "slots":
        await slots(update, context)

    elif q.data == "dice":
        await dice(update, context)

    elif q.data == "crash":
        await crash(update, context)

    elif q.data.startswith("m_"):
        await mines_click(update, context)

    elif q.data == "daily":
        await daily(update, context)

# ---------------- MAIN ----------------
def main():
    load()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))

    print("🚀 TOKEN ARCADE FINAL v6 RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
