from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json
import os
import random
from datetime import datetime

TOKEN = os.getenv('TELEGRAM_TOKEN')
DATA_FILE = 'arcade_users_tg.json'

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users():
    with open(DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def get_user(user_id):
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            'coins': 500,
            'xp': 0,
            'ref_code': f"TG{user_id % 10000:04d}",
            'referrals': [],
            'stats': {'games_played': 0, 'total_wagered': 0, 'biggest_win': 0, 'last_daily': None}
        }
        save_users()
    return users[uid]

users = load_users()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data='balance')],
        [InlineKeyboardButton("📊 Profile", callback_data='profile')],
        [InlineKeyboardButton("🎲 Dice (10 coins)", callback_data='dice_demo')],
        [InlineKeyboardButton("🎰 Slots (10 coins)", callback_data='slots_demo')],
        [InlineKeyboardButton("💣 Mines", callback_data='mines_info')],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data='leaderboard')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎰 *TokenArcade on Telegram!*\n\nHi {update.effective_user.first_name}!\n\n💰 Coins: `{user['coins']}`\n🎮 Games Played: `{user['stats']['games_played']}`",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🎮 *TokenArcade Commands*

/start - Main menu
/balance - Check coins
/daily - Get 50 free coins
/help - This message
/mines 50 5 - Play mines (bet, bombs)
/keno 50 - Play keno
/slots 50 - Play slots
/dice 50 high - Roll dice (bet, high/low)
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    level = (user['xp'] // 500) + 1
    text = f"""
💰 *Your Balance*

Coins: `{user['coins']} ¢`
Level: `{level}`
XP: `{user['xp'] % 500}/500`
Games: `{user['stats']['games_played']}`
Wagered: `{user['stats']['total_wagered']}`
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    today = datetime.now().date().isoformat()
    
    if user['stats']['last_daily'] == today:
        await update.message.reply_text("❌ Already claimed today! Come back tomorrow for 50 more coins.")
        return
    
    user['coins'] += 50
    user['stats']['last_daily'] = today
    save_users()
    await update.message.reply_text("✅ *Daily bonus claimed!*\n\n+50 coins 💰", parse_mode='Markdown')

async def mines_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: `/mines 50 5`\n(bet amount, number of bombs 3/5/10)", parse_mode='Markdown')
        return
    
    try:
        bet = int(context.args[0])
        bombs = int(context.args[1])
    except:
        await update.message.reply_text("Invalid format. Usage: `/mines 50 5`", parse_mode='Markdown')
        return
    
    user = get_user(update.effective_user.id)
    
    if bet < 1:
        await update.message.reply_text("❌ Bet must be at least 1 coin!")
        return
    if bet > user['coins']:
        await update.message.reply_text(f"❌ You only have {user['coins']} coins!")
        return
    if bombs not in [3, 5, 10]:
        await update.message.reply_text("❌ Bombs must be 3, 5, or 10!")
        return
    
    user['coins'] -= bet
    
    safe_tiles = random.randint(1, min(8, 25 - bombs))
    mult = 1
    for i in range(safe_tiles):
        mult *= (25 - i) / (25 - i - bombs)
    mult *= 0.95
    
    hit_bomb = random.random() < (safe_tiles / (25 - bombs))
    
    if hit_bomb:
        result = f"💥 *BOOM!* You hit a bomb!\n\nLost: `{bet} ¢`\nNew balance: `{user['coins']} ¢`"
    else:
        payout = int(bet * mult)
        user['coins'] += payout
        result = f"✅ *Won {payout} coins!*\n\nSafe tiles: `{safe_tiles}`\nMultiplier: `{mult:.2f}x`\nNew balance: `{user['coins']} ¢`"
        if payout > user['stats']['biggest_win']:
            user['stats']['biggest_win'] = payout
    
    user['stats']['games_played'] += 1
    user['stats']['total_wagered'] += bet
    user['xp'] += max(5, bet // 10)
    save_users()
    
    await update.message.reply_text(result, parse_mode='Markdown')

async def keno_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/keno 50`", parse_mode='Markdown')
        return
    
    try:
        bet = int(context.args[0])
    except:
        await update.message.reply_text("Invalid bet amount.", parse_mode='Markdown')
        return
    
    user = get_user(update.effective_user.id)
    
    if bet < 1 or bet > user['coins']:
        await update.message.reply_text(f"❌ Invalid bet! You have {user['coins']} coins.", parse_mode='Markdown')
        return
    
    user['coins'] -= bet
    
    drawn = set()
    while len(drawn) < 10:
        drawn.add(random.randint(1, 40))
    
    picks = set()
    temp = list(range(1, 41))
    random.shuffle(temp)
    picks = set(temp[:random.randint(4, 10)])
    
    matches = len(picks & drawn)
    
    pt = {4: {2: 1, 3: 5, 4: 15}, 6: {3: 1.5, 4: 4, 5: 15, 6: 40}, 8: {3: 1, 4: 2, 5: 5, 6: 12, 7: 25, 8: 50}, 10: {4: 1, 5: 2, 6: 5, 7: 10, 8: 20, 9: 35, 10: 50}}
    picks_count = len(picks)
    best_key = max([k for k in pt.keys() if k <= picks_count])
    mult = pt[best_key].get(matches, 0)
    payout = int(bet * mult)
    
    if payout > 0:
        user['coins'] += payout
        if payout > user['stats']['biggest_win']:
            user['stats']['biggest_win'] = payout
    
    user['stats']['games_played'] += 1
    user['stats']['total_wagered'] += bet
    user['xp'] += max(5, bet // 10)
    save_users()
    
    result = f"""🎱 *Keno Result*

Numbers picked: `{picks_count}`
Matches: `{matches}/{picks_count}`
Payout: `{payout} ¢`
New balance: `{user['coins']} ¢`
    """
    await update.message.reply_text(result, parse_mode='Markdown')

async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/slots 50`", parse_mode='Markdown')
        return
    
    try:
        bet = int(context.args[0])
    except:
        await update.message.reply_text("Invalid bet amount.", parse_mode='Markdown')
        return
    
    user = get_user(update.effective_user.id)
    
    if bet < 1 or bet > user['coins']:
        await update.message.reply_text(f"❌ Invalid bet! You have {user['coins']} coins.", parse_mode='Markdown')
        return
    
    user['coins'] -= bet
    
    symbols = ['🍒', '🍋', '🍊', '🔔', '💎', '7️⃣']
    reels = [random.choice(symbols) for _ in range(3)]
    
    mult = 0
    if reels[0] == reels[1] == reels[2]:
        if reels[0] == '7️⃣':
            mult = 100
        elif reels[0] == '💎':
            mult = 50
        else:
            mult = 10
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        mult = 2
    
    payout = int(bet * mult)
    if payout > 0:
        user['coins'] += payout
        if payout > user['stats']['biggest_win']:
            user['stats']['biggest_win'] = payout
    
    user['stats']['games_played'] += 1
    user['stats']['total_wagered'] += bet
    user['xp'] += max(5, bet // 10)
    save_users()
    
    result = "".join(reels)
    status = f"✅ *WON {payout} coins!*" if mult > 0 else "❌ No match"
    
    text = f"""🎰 *Slots Result*

{result}

{status}
New balance: `{user['coins']} ¢`
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def dice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: `/dice 50 high` or `/dice 50 low`", parse_mode='Markdown')
        return
    
    try:
        bet = int(context.args[0])
        prediction = context.args[1].lower()
    except:
        await update.message.reply_text("Invalid format.", parse_mode='Markdown')
        return
    
    if prediction not in ['high', 'low']:
        await update.message.reply_text("Prediction must be 'high' or 'low'", parse_mode='Markdown')
        return
    
    user = get_user(update.effective_user.id)
    
    if bet < 1 or bet > user['coins']:
        await update.message.reply_text(f"❌ Invalid bet! You have {user['coins']} coins.", parse_mode='Markdown')
        return
    
    user['coins'] -= bet
    
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    total = d1 + d2
    
    is_high = total >= 7
    won = (is_high and prediction == 'high') or (not is_high and prediction == 'low')
    
    payout = bet * 2 if won else 0
    if payout > 0:
        user['coins'] += payout
        if payout > user['stats']['biggest_win']:
            user['stats']['biggest_win'] = payout
    
    user['stats']['games_played'] += 1
    user['stats']['total_wagered'] += bet
    user['xp'] += max(5, bet // 10)
    save_users()
    
    result = "✅ *WON!*" if won else "❌ *LOST!*"
    
    text = f"""🎲 *Dice Result*

Roll: `{d1} + {d2} = {total}`
Prediction: `{prediction.upper()}`
{result}

Payout: `{payout} ¢`
New balance: `{user['coins']} ¢`
    """
    await update.message.reply_text(text, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = get_user(query.from_user.id)
    
    if query.data == 'balance':
        level = (user['xp'] // 500) + 1
        text = f"💰 *Balance*\n\nCoins: `{user['coins']} ¢`\nLevel: `{level}`\nGames: `{user['stats']['games_played']}`"
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == 'profile':
        level = (user['xp'] // 500) + 1
        text = f"""👤 *Your Profile*

💰 Coins: `{user['coins']}`
📊 Level: `{level}`
🎮 Games: `{user['stats']['games_played']}`
💸 Wagered: `{user['stats']['total_wagered']}`
🏆 Biggest Win: `{user['stats']['biggest_win']}`
        """
        await query.edit_message_text(text, parse_mode='Markdown')
    
    elif query.data == 'dice_demo':
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2
        won = random.choice([True, False])
        payout = 10 if won else 0
        user['coins'] += payout
        user['stats']['games_played'] += 1
        save_users()
        result = "✅ Won 10!" if won else "❌ Lost"
        await query.edit_message_text(f"🎲 {d1}+{d2}={total}\n{result}\nBalance: `{user['coins']}`", parse_mode='Markdown')
    
    elif query.data == 'slots_demo':
        symbols = ['🍒', '🍋', '🍊', '🔔', '💎', '7️⃣']
        reels = [random.choice(symbols) for _ in range(3)]
        mult = 10 if reels[0] == reels[1] == reels[2] else (2 if reels[0] == reels[1] or reels[1] == reels[2] else 0)
        payout = 10 * mult
        user['coins'] += payout
        user['stats']['games_played'] += 1
        save_users()
        result = f"✅ Won {payout}!" if payout else "❌ No match"
        await query.edit_message_text(f"🎰 {''.join(reels)}\n{result}\nBalance: `{user['coins']}`", parse_mode='Markdown')
    
    elif query.data == 'mines_info':
        await query.edit_message_text("💣 *Mines Game*\n\nUsage: `/mines 50 5`\n(bet, bombs: 3/5/10)\n\nDodge bombs, escalate multiplier!", parse_mode='Markdown')
    
    elif query.data == 'leaderboard':
        sorted_users = sorted(users.items(), key=lambda x: x[1]['coins'], reverse=True)[:5]
        text = "🏆 *Top 5 Players*\n\n"
        for i, (uid, u) in enumerate(sorted_users, 1):
            text += f"{i}. User{uid[:3]} - `{u['coins']} ¢`\n"
        await query.edit_message_text(text, parse_mode='Markdown')

async def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("mines", mines_cmd))
    app.add_handler(CommandHandler("keno", keno_cmd))
    app.add_handler(CommandHandler("slots", slots_cmd))
    app.add_handler(CommandHandler("dice", dice_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("🤖 TokenArcade Telegram Bot is running!")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
