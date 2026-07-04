import os
import json
import random
import asyncio
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATA_FILE = "arcade_prod.json"

users = {}
sessions = {}
cooldowns = {}

# ---------------- STORAGE ----------------
def load():
    global users
    if os.path.exists(DATA_FILE):
        users = json.load(open(DATA_FILE))

def save():
    json.dump(users, open(DATA_FILE, "w"), indent=2)

# ---------------- USER CORE ----------------
def get(uid):
    uid = str(uid)

    if uid not in users:
        users[uid] = {
            "coins": 1000,
            "xp": 0,
            "level": 1,
            "boost": 1.0,
            "streak": 0,
            "last_daily": None,
            "referrals": 0,
            "wallet": {
                "deposits": [],
                "withdrawals": []
            },
            "admin": False
        }

    return users[uid]

def level(u):
    u["level"] = (u["xp"] // 250) + 1

# ---------------- UI ENGINE ----------------
def header(u):
    return (
        f"🎰 TOKEN ARCADE\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 {u['coins']} coins\n"
        f"⚡ Level {u['level']}\n"
        f"🔥 Boost x{u['boost']}\n"
        f"━━━━━━━━━━━━━━\n\n"
    )

def home(u):
    return header(u) + "🏠 MAIN HUB"

def home_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Games", callback_data="games")],
        [InlineKeyboardButton("💼 Wallet", callback_data="wallet")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="lb")],
    ])

def wallet_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇ Deposit", callback_data="deposit")],
        [InlineKeyboardButton("⬆ Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("⬅ Back", callback_data="home")]
    ])

# ---------------- WALLET (SIMULATED LEDGER) ----------------
def deposit_screen():
    return (
        "⬇ DEPOSIT\n\n"
        "Send crypto to:\n"
        "BTC: bc1q-placeholder\n"
        "ETH: 0x-placeholder\n"
        "USDT: TRC20-placeholder\n\n"
        "⚠ Simulated system (no real funds processed)"
    )

def withdraw_screen(u):
    return (
        header(u) +
        "⬆ WITHDRAW\n\n"
        "Use:\n"
        "/withdraw 500 BTC ADDRESS\n\n"
        "Requests are queued for admin approval"
    )

# ---------------- MINES ----------------
def new_mines():
    return {
        "mines": set(random.sample(range(25), 5)),
        "revealed": set(),
        "mult": 1.0
    }

def mines_ui(s):
    t = "💣 MINES\n\n"
    for i in range(25):
        if i % 5 == 0:
            t += "\n"
        t += "💎 " if i in s["revealed"] else "⬜ "
    return t + f"\n\nx{s['mult']:.2f}"

def mines_kb():
    b = [InlineKeyboardButton("⬜", callback_data=f"m_{i}") for i in range(25)]
    rows = [b[i:i+5] for i in range(0,25,5)]
    rows.append([InlineKeyboardButton("💸 Cashout", callback_data="m_cash")])
    return InlineKeyboardMarkup(rows)

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get(update.effective_user.id)
    save()

    await update.message.reply_text(
        home(u),
        reply_markup=home_kb()
    )

# ---------------- WALLET ----------------
async def withdraw(update, context):
    u = get(update.effective_user.id)

    try:
        amount = int(context.args[0])
        method = context.args[1]
        address = context.args[2]
    except:
        return await update.message.reply_text("Usage: /withdraw 500 BTC ADDRESS")

    if amount > u["coins"]:
        return await update.message.reply_text("❌ Not enough balance")

    u["coins"] -= amount

    u["wallet"]["withdrawals"].append({
        "amount": amount,
        "method": method,
        "address": address,
        "status": "pending",
        "time": str(datetime.now())
    })

    save()

    await update.message.reply_text("⬆ Withdrawal queued (pending admin approval)")

# ---------------- MINES ENGINE ----------------
async def mines_start(update, context):
    uid = str(update.effective_user.id)
    u = get(uid)

    u["coins"] -= 50
    sessions[uid] = new_mines()

    await update.message.reply_text(
        mines_ui(sessions[uid]),
        reply_markup=mines_kb()
    )

async def mines_click(update, context):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    u = get(uid)
    s = sessions.get(uid)

    if not s:
        return

    if q.data == "m_cash":
        payout = int(50 * s["mult"] * u["boost"])
        u["coins"] += payout
        sessions.pop(uid, None)
        save()
        return await q.edit_message_text(f"💸 +{payout}", reply_markup=home_kb())

    i = int(q.data.split("_")[1])

    if i in s["mines"]:
        sessions.pop(uid, None)
        return await q.edit_message_text("💥 BOOM", reply_markup=home_kb())

    s["revealed"].add(i)
    s["mult"] += 0.35

    await q.edit_message_text(mines_ui(s), reply_markup=mines_kb())

# ---------------- DICE ----------------
async def dice(update, context):
    u = get(update.effective_user.id)

    msg = await context.bot.send_dice(
        chat_id=update.effective_chat.id,
        emoji="🎲"
    )

    if msg.dice.value >= 4:
        u["coins"] += 100

    save()

# ---------------- CALLBACK ROUTER ----------------
async def cb(update, context):
    q = update.callback_query
    await q.answer()

    u = get(str(q.from_user.id))

    if q.data == "home":
        await q.edit_message_text(home(u), reply_markup=home_kb())

    elif q.data == "wallet":
        await q.edit_message_text(header(u) + "💼 WALLET", reply_markup=wallet_kb())

    elif q.data == "deposit":
        await q.edit_message_text(deposit_screen(), reply_markup=wallet_kb())

    elif q.data == "withdraw":
        await q.edit_message_text(withdraw_screen(u), reply_markup=wallet_kb())

    elif q.data == "games":
        await mines_start(update, context)

    elif q.data.startswith("m_"):
        await mines_click(update, context)

# ---------------- MAIN ----------------
def main():
    load()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CallbackQueryHandler(cb))

    print("🚀 TOKEN ARCADE PROD READY")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
