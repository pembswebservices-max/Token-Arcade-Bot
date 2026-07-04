import os
import json
import random
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "arcade_final.json"

users = {}
sessions = {}

# ---------------- STORAGE ----------------
def load():
    global users
    if os.path.exists(DATA_FILE):
        users = json.load(open(DATA_FILE))

def save():
    json.dump(users, open(DATA_FILE, "w"), indent=2)

# ---------------- USER MODEL ----------------
def get(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "coins": 1000,
            "xp": 0,
            "level": 1,
            "boost": 1.0,
            "weekly": 0,
            "referrals": 0,
            "last_daily": None,
            "admin": False,
            "wagered": 0,
            "withdrawals": [],
            "deposits": []
        }

    return users[uid]

def level(u):
    u["level"] = (u["xp"] // 250) + 1

# ---------------- UI ----------------
def header(u):
    return (
        f"🎰 TOKEN ARCADE\n"
        f"━━━━━━━━━━━━\n"
        f"💰 {u['coins']} coins\n"
        f"⚡ Lv {u['level']}\n"
        f"🔥 x{u['boost']}\n"
        f"━━━━━━━━━━━━\n\n"
    )

def home(u):
    return header(u) + "🏠 Main Hub"

def home_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Games", callback_data="games")],
        [InlineKeyboardButton("💼 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("🏆 Leaderboards", callback_data="lb")]
    ])

def games_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 Dice", callback_data="dice"),
         InlineKeyboardButton("🎯 Darts", callback_data="darts")],
        [InlineKeyboardButton("🏀 Basket", callback_data="basket"),
         InlineKeyboardButton("🎳 Bowling", callback_data="bowling")],
        [InlineKeyboardButton("⚽ Football", callback_data="football"),
         InlineKeyboardButton("💣 Mines", callback_data="mines")],
        [InlineKeyboardButton("🎱 Keno", callback_data="keno")],
        [InlineKeyboardButton("⬅ Back", callback_data="home")]
    ])

def wallet_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇ Deposit", callback_data="deposit"),
         InlineKeyboardButton("⬆ Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("⬅ Back", callback_data="home")]
    ])

# ---------------- BONUSES ----------------
def daily(u):
    today = str(datetime.now().date())
    if u["last_daily"] == today:
        return 0
    u["last_daily"] = today
    u["coins"] += 200
    return 200

# ---------------- LEADERBOARDS ----------------
def lb_all():
    top = sorted(users.items(), key=lambda x: x[1]["coins"], reverse=True)[:5]
    t = "🏆 ALL TIME\n\n"
    for i,(uid,u) in enumerate(top,1):
        t += f"{i}. {uid[:4]} - {u['coins']}\n"
    return t

def lb_week():
    top = sorted(users.items(), key=lambda x: x[1]["weekly"], reverse=True)[:5]
    t = "📅 WEEKLY\n\n"
    for i,(uid,u) in enumerate(top,1):
        t += f"{i}. {uid[:4]} - {u['weekly']}\n"
    return t

# ---------------- MINES ----------------
def mines_new():
    return {
        "mines": set(random.sample(range(25), 5)),
        "revealed": set(),
        "mult": 1.0
    }

def mines_ui(s):
    t = "💣 MINES\n"
    for i in range(25):
        if i % 5 == 0:
            t += "\n"
        t += "💎 " if i in s["revealed"] else "⬜ "
    return t + f"\nx{s['mult']:.2f}"

def mines_kb():
    b = [InlineKeyboardButton("⬜", callback_data=f"m_{i}") for i in range(25)]
    rows = [b[i:i+5] for i in range(0,25,5)]
    rows.append([InlineKeyboardButton("💸 Cashout", callback_data="m_cash")])
    return InlineKeyboardMarkup(rows)

# ---------------- GAMES ----------------
async def dice(update, context):
    u = get(update.effective_user.id)

    msg = await context.bot.send_dice(update.effective_chat.id, "🎲")

    if msg.dice.value >= 4:
        u["coins"] += 100
        u["weekly"] += 100

    save()

async def darts(update, context):
    u = get(update.effective_user.id)
    msg = await context.bot.send_dice(update.effective_chat.id, "🎯")
    if msg.dice.value >= 5:
        u["coins"] += 150
    save()

async def basket(update, context):
    u = get(update.effective_user.id)
    msg = await context.bot.send_dice(update.effective_chat.id, "🏀")
    if msg.dice.value >= 4:
        u["coins"] += 120
    save()

async def bowling(update, context):
    u = get(update.effective_user.id)
    msg = await context.bot.send_dice(update.effective_chat.id, "🎳")
    if msg.dice.value >= 4:
        u["coins"] += 200
    save()

async def football(update, context):
    u = get(update.effective_user.id)
    msg = await context.bot.send_dice(update.effective_chat.id, "⚽")
    if msg.dice.value in [4,5]:
        u["coins"] += 180
    save()

async def keno(update, context):
    u = get(update.effective_user.id)

    u["coins"] -= 50

    drawn = set(random.sample(range(40), 10))
    picks = set(random.sample(range(40), 8))

    matches = len(drawn & picks)
    payout = matches * 50

    u["coins"] += payout
    u["weekly"] += payout

    save()

    await update.message.reply_text(f"🎱 KENO\nMatches: {matches}\n+{payout}")

# ---------------- MINES ENGINE ----------------
async def mines_start(update, context):
    uid = str(update.effective_user.id)
    u = get(uid)

    u["coins"] -= 50
    sessions[uid] = mines_new()

    await update.message.reply_text(mines_ui(sessions[uid]), reply_markup=mines_kb())

async def mines_click(update, context):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    u = get(uid)
    s = sessions.get(uid)

    if not s:
        return

    if q.data == "m_cash":
        payout = int(50 * s["mult"])
        u["coins"] += payout
        sessions.pop(uid, None)
        save()
        return await q.edit_message_text(f"💸 +{payout}", reply_markup=home_kb())

    i = int(q.data.split("_")[1])

    if i in s["mines"]:
        sessions.pop(uid, None)
        return await q.edit_message_text("💥 BOOM", reply_markup=home_kb())

    s["revealed"].add(i)
    s["mult"] += 0.4

    await q.edit_message_text(mines_ui(s), reply_markup=mines_kb())

# ---------------- WALLET (SIMULATED LEDGER) ----------------
async def withdraw(update, context):
    u = get(update.effective_user.id)

    try:
        amt = int(context.args[0])
        method = context.args[1]
        addr = context.args[2]
    except:
        return await update.message.reply_text("Usage: /withdraw 500 BTC ADDRESS")

    if amt > u["coins"]:
        return

    u["coins"] -= amt

    u["withdrawals"].append({
        "amount": amt,
        "method": method,
        "address": addr,
        "status": "pending"
    })

    save()
    await update.message.reply_text("⬆ Withdrawal queued")

# ---------------- CALLBACK ----------------
async def cb(update, context):
    q = update.callback_query
    await q.answer()

    u = get(str(q.from_user.id))

    if q.data == "home":
        await q.edit_message_text(home(u), reply_markup=home_kb())

    elif q.data == "games":
        await q.edit_message_text("🎮 Games", reply_markup=games_kb())

    elif q.data == "wallet":
        await q.edit_message_text(header(u) + "💼 Wallet", reply_markup=wallet_kb())

    elif q.data == "deposit":
        await q.edit_message_text("⬇ Deposit\n\nBTC/ETH/USDT placeholder")

    elif q.data == "withdraw":
        await q.edit_message_text("⬆ Use /withdraw amount method address")

    elif q.data == "lb":
        await q.edit_message_text(lb_all())

    elif q.data == "mines":
        await mines_start(update, context)

    elif q.data.startswith("m_"):
        await mines_click(update, context)

    elif q.data in ["dice","darts","basket","bowling","football"]:
        await globals()[q.data](update, context)

# ---------------- START ----------------
async def start(update, context):
    u = get(update.effective_user.id)
    save()
    await update.message.reply_text(home(u), reply_markup=home_kb())

# ---------------- MAIN ----------------
def main():
    load()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CallbackQueryHandler(cb))

    print("🚀 FINAL TOKEN ARCADE RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
