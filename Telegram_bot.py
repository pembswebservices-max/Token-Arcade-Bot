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
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

users = load()

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
            "stats": {"played": 0, "wins": 0, "losses": 0},
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

# ---------------- MINES ----------------
def make_board():
    mines = set(random.sample(range(25), 5))
    return mines

def render(mines, revealed=set(), dead=False):
    text = ""
    for i in range(25):
        if i % 5 == 0:
            text += "\n"
        if i in revealed:
            text += "💎 "
        elif dead and i in mines:
            text += "💣 "
        else:
            text += "⬜ "
    return text

async def mines_game(q, u):
    bet = 50
    if u["coins"] < bet:
        return await q.edit_message_text("❌ Not enough coins", reply_markup=games_menu())

    u["coins"] -= bet
    mines = make_board()
    revealed = set()

    msg = await q.edit_message_text("💣 Loading board...")

    for i in range(3):
        await asyncio.sleep(0.3)
        await msg.edit_text("💣 Revealing" + "." * (i+1))

    safe = random.sample(range(25), 8)
    dead = False

    for s in safe:
        await asyncio.sleep(0.2)
        if s in mines:
            revealed.add(s)
            dead = True
            break
        revealed.add(s)
        await msg.edit_text(render(mines, revealed))

    if dead:
        result = f"\n\n💥 LOST -{bet}"
        u["stats"]["losses"] += 1
    else:
        win = bet * 4
        u["coins"] += win
        result = f"\n\n✅ WIN +{win}"
        u["stats"]["wins"] += 1

    u["stats"]["played"] += 1
    u["xp"] += 20
    update(u)
    save()

    await msg.edit_text(render(mines, revealed, dead) + result, reply_markup=games_menu())

# ---------------- SLOTS ----------------
async def slots_game(q, u):
    bet = 50
    if u["coins"] < bet:
        return await q.edit_message_text("❌ Not enough coins", reply_markup=games_menu())

    u["coins"] -= bet

    symbols = ["🍒","🍋","🍊","💎","7️⃣"]
    msg = await q.edit_message_text("🎰 Spinning...")

    reels = ["❓","❓","❓"]

    for _ in range(6):
        reels = [random.choice(symbols) for _ in range(3)]
        await asyncio.sleep(0.15)
        await msg.edit_text("🎰 " + "".join(reels))

    reels = [random.choice(symbols) for _ in range(3)]

    mult = 0
    if reels[0] == reels[1] == reels[2]:
        mult = 20
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        mult = 3

    win = bet * mult
    u["coins"] += win

    u["xp"] += 15
    update(u)
    save()

    await msg.edit_text("🎰 " + "".join(reels) + f"\n\n+{win}", reply_markup=games_menu())

# ---------------- DICE ----------------
async def dice_game(q, u):
    bet = 50
    if u["coins"] < bet:
        return await q.edit_message_text("❌ Not enough coins", reply_markup=games_menu())

    u["coins"] -= bet

    msg = await q.edit_message_text("🎲 Rolling...")

    for _ in range(4):
        a, b = random.randint(1,6), random.randint(1,6)
        await asyncio.sleep(0.2)
        await msg.edit_text(f"🎲 {a}+{b}")

    a, b = random.randint(1,6), random.randint(1,6)
    total = a + b

    win = total >= 7
    payout = bet * 2 if win else 0

    u["coins"] += payout
    u["xp"] += 10
    update(u)
    save()

    await msg.edit_text(f"🎲 {a}+{b}={total}\n{'WIN' if win else 'LOSE'}", reply_markup=games_menu())

# ---------------- CRASH ----------------
async def crash_game(q, u):
    bet = 50
    if u["coins"] < bet:
        return await q.edit_message_text("❌ Not enough coins", reply_markup=games_menu())

    u["coins"] -= bet

    msg = await q.edit_message_text("📈 Launching...")

    mult = 1.0
    for _ in range(6):
        mult += random.uniform(0.3, 1.5)
        await asyncio.sleep(0.25)
        await msg.edit_text(f"📈 x{mult:.2f}")

    crashed = random.choice([True, False])

    if crashed:
        result = f"💥 CRASHED x{mult:.2f}"
        u["stats"]["losses"] += 1
    else:
        win = int(bet * mult)
        u["coins"] += win
        result = f"📈 CASHED x{mult:.2f} → +{win}"
        u["stats"]["wins"] += 1

    u["xp"] += 25
    update(u)
    save()

    await msg.edit_text(result, reply_markup=games_menu())

# ---------------- CALLBACKS ----------------
async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    u = get(q.from_user.id)

    if q.data == "home":
        await q.edit_message_text("🏠 Main Menu", reply_markup=main_menu())

    elif q.data == "games":
        await q.edit_message_text("🎮 Games", reply_markup=games_menu())

    elif q.data == "balance":
        await q.edit_message_text(f"💰 Coins: {u['coins']}", reply_markup=main_menu())

    elif q.data == "profile":
        await q.edit_message_text(
            f"👤 Level {u['level']} | {u['rank']}\nCoins {u['coins']}",
            reply_markup=main_menu()
        )

    elif q.data == "leaderboard":
        top = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)[:5]
        text = "🏆 Top\n\n"
        for i,(uid,x) in enumerate(top,1):
            text += f"{i}. {uid[:4]} - {x['coins']}\n"
        await q.edit_message_text(text, reply_markup=main_menu())

    elif q.data == "shop":
        await q.edit_message_text("🛒 Shop coming soon", reply_markup=main_menu())

    elif q.data == "mines":
        await mines_game(q, u)

    elif q.data == "slots":
        await slots_game(q, u)

    elif q.data == "dice":
        await dice_game(q, u)

    elif q.data == "crash":
        await crash_game(q, u)

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(cb))

    print("🚀 TOKEN ARCADE FINAL RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
