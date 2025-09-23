"""
Callback query handlers for inline keyboards
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import InvestmentPlan, TECH_STOCKS, NON_TECH_STOCKS, ALL_STOCKS, ADMIN_USER_IDS
from database import db
from market_data import market
from .utils import log_admin_action
from handlers.user_handlers import show_main_menu, get_random_wallet
from .message_handlers import handle_stock_sale
from config import ADMIN_USER_IDS

import asyncio

async def schedule_message_deletion(context, chat_id, message_id, delay_seconds=120):
    """Schedule a message for deletion after delay"""
    try:
        await asyncio.sleep(delay_seconds)
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logging.error(f"Failed to delete message {message_id}: {e}")

async def send_temporary_message(update, context, text, reply_markup=None, parse_mode=None, delete_after=120):
    """Send a message that will be auto-deleted"""
    if update.message:
        sent_message = await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        # Schedule deletion of both user message and bot response
        asyncio.create_task(schedule_message_deletion(context, update.message.chat_id, update.message.message_id, delete_after))
        asyncio.create_task(schedule_message_deletion(context, sent_message.chat_id, sent_message.message_id, delete_after))
        return sent_message
    elif update.callback_query:
        # For callback queries, edit the message and schedule deletion
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        asyncio.create_task(schedule_message_deletion(context, update.callback_query.message.chat_id, 
                                                    update.callback_query.message.message_id, delete_after))
        return update.callback_query.message
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main callback query handler - handles ALL callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user = query.from_user
    
    try:
        # Main navigation
        if data == "main_menu":
            await show_main_menu(update, context, user)
        
        elif data == "portfolio":
            from handlers.user_handlers import portfolio_command
            await portfolio_command(update, context)
        
        elif data == "refresh_portfolio":
            from handlers.user_handlers import portfolio_command, calculate_user_profits
            calculate_user_profits()
            await portfolio_command(update, context)
        
        elif data == "invest_menu":
            await show_invest_menu(update, context)
        
        elif data == "withdraw":
            await show_withdraw_menu(update, context)
        
        elif data == "live_prices":
            await show_live_prices_menu(update, context)
        
        elif data == "leaderboard":
            await show_leaderboard(update, context)
        
        elif data == "profile":
            await show_profile(update, context)
        
        elif data == "help":
            await show_help(update, context)
        
        # Investment flow
        elif data == "crypto_plans":
            await show_crypto_plans(update, context)
        
        elif data.startswith("plan_"):
            await handle_plan_selection(update, context, data)
        
        elif data.startswith("crypto_"):
            await handle_crypto_selection(update, context, data)
        
        elif data == "confirm_payment":
            await handle_payment_confirmation(update, context)
        
        # Stock investment
        elif data.startswith("stocks_"):
            await handle_stock_pages(update, context, data)
        
        elif data.startswith("buy_stock_"):
            await handle_stock_purchase(update, context, data)
        
        elif data == "confirm_stock_payment":
            await handle_stock_payment_confirmation(update, context)
        
        # Withdrawal
        elif data.startswith("withdraw_"):
            await handle_withdrawal_options(update, context, data)
        
        # Live prices
        elif data.startswith("live_crypto"):
            await handle_live_crypto_prices(update, context, data)
        
        elif data.startswith("live_stock"):
            await handle_live_stock_prices(update, context, data)
        
        # Admin callbacks
        elif data.startswith("admin_"):
            if user.id in ADMIN_USER_IDS:
                await handle_admin_callbacks(update, context, data)
            else:
                await query.message.edit_text(
                    "❌ You do not have permission to access the admin panel.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
                )
        
        elif data == "user_history":
            await show_user_transaction_history(update, context)

        elif data == "withdraw_stocks":
            await handle_stock_withdrawal(update, context)
        elif data.startswith("sell_stock_"):
            stock_id = int(data.replace("sell_stock_", ""))
            await handle_stock_sale(update, context, stock_id)        
        
        else:
            await query.message.edit_text(
                "❌ Unknown action. Returning to main menu.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
            )
    
    except Exception as e:
        logging.error(f"Error in callback handler for '{data}': {e}")
        await query.message.edit_text(
            "❌ An error occurred. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
        )

async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle all admin-related callbacks"""
    from handlers.admin_handlers import handle_admin_callback, admin_command
    
    if data == "admin_panel":
        await admin_command(update, context)
    else:
        await handle_admin_callback(update, context, data)

async def show_invest_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show investment options menu"""
    keyboard = [
        [InlineKeyboardButton("💰 Crypto Plans", callback_data="crypto_plans")],
        [InlineKeyboardButton("📈 Stocks", callback_data="stocks_page_0")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
💰 INVESTMENT OPTIONS

Choose your investment type:

• **Crypto Plans**: Automated daily profits with our tiered investment plans
• **Stocks**: Invest in individual stocks from top companies

Your investment journey starts here! 👇
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_crypto_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show crypto investment plans"""
    keyboard = [
        [InlineKeyboardButton("🥉 Core Plan ($1K-$15K)", callback_data="plan_core")],
        [InlineKeyboardButton("🥈 Growth Plan ($20K-$80K)", callback_data="plan_growth")],
        [InlineKeyboardButton("🥇 Alpha Plan ($100K+)", callback_data="plan_alpha")],
        [InlineKeyboardButton("🔙 Invest Menu", callback_data="invest_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
💰 CRYPTO INVESTMENT PLANS

🥉 **CORE PLAN** - Perfect for Beginners
• Range: $1,000 - $15,000
• Daily Return: 1.43%
• Annual ROI: ~520%

🥈 **GROWTH PLAN** - Balanced Approach  
• Range: $20,000 - $80,000
• Daily Return: 2.14%
• Annual ROI: ~780%

🥇 **ALPHA PLAN** - Maximum Returns
• Range: $100,000+
• Daily Return: 2.86%
• Annual ROI: ~1040%

💎 All plans include:
✅ Automated daily compounding
✅ Anytime withdrawals
✅ Multi-crypto support
✅ Professional management

Select your plan below: 👇
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_plan_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle crypto plan selection"""
    plan_type = data.split("_")[1]
    
    plan_map = {
        "core": InvestmentPlan.CORE.value,
        "growth": InvestmentPlan.GROWTH.value,
        "alpha": InvestmentPlan.ALPHA.value
    }
    
    plan_info = plan_map.get(plan_type)
    if not plan_info:
        await update.callback_query.message.edit_text("❌ Invalid plan selected.")
        return
    
    keyboard = [
        [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data=f"crypto_btc_{plan_type}")],
        [InlineKeyboardButton("💎 Ethereum (ETH)", callback_data=f"crypto_eth_{plan_type}")],
        [InlineKeyboardButton("💵 USDT (TRC20)", callback_data=f"crypto_usdt_{plan_type}")],
        [InlineKeyboardButton("☀️ Solana (SOL)", callback_data=f"crypto_sol_{plan_type}")],
        [InlineKeyboardButton("💙 TON", callback_data=f"crypto_ton_{plan_type}")],
        [InlineKeyboardButton("🔙 Crypto Plans", callback_data="crypto_plans")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
🎯 **{plan_info['name'].upper()}** SELECTED

💰 Investment Range: ${plan_info['min_amount']:,} - ${plan_info['max_amount']:,}
📈 Daily Return: {plan_info['daily_return'] * 100:.2f}%
📊 Expected Annual ROI: ~{plan_info['daily_return'] * 365 * 100:.0f}%

**Choose your preferred cryptocurrency:**

Each crypto has secure rotating wallet addresses.
After selection, you'll receive:
• Unique wallet address
• Exact payment instructions
• Investment tracking

⚠️ **Important:**
• Minimum investment applies
• Profits start once confirmed
• Send exact amount to avoid delays

Select cryptocurrency below: 👇
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_crypto_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle cryptocurrency selection"""
    parts = data.split("_")
    crypto = parts[1]
    plan_type = parts[2]
    
    plan_map = {
        "core": InvestmentPlan.CORE.value,
        "growth": InvestmentPlan.GROWTH.value,
        "alpha": InvestmentPlan.ALPHA.value
    }
    
    plan_info = plan_map.get(plan_type)
    if not plan_info:
        await update.callback_query.message.edit_text("❌ Invalid plan selected.")
        return
    
    wallet_address = get_random_wallet(crypto)
    if not wallet_address:
        await update.callback_query.message.edit_text("❌ Invalid cryptocurrency selected.")
        return
    
    # Store investment details in user data
    context.user_data['awaiting_tx_details'] = {
        'plan_type': plan_type,
        'plan_info': plan_info,
        'crypto': crypto,
        'wallet_address': wallet_address,
        'user_id': update.callback_query.from_user.id
    }
    
    keyboard = [
        [InlineKeyboardButton("✅ I've Sent Payment", callback_data="confirm_payment")],
        [InlineKeyboardButton("🔙 Back to Plans", callback_data="crypto_plans")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💰 **INVESTMENT DEPOSIT - {crypto.upper()}**

🎯 Plan: {plan_info['name']}
💎 Cryptocurrency: {crypto.upper()}
📈 Daily Return: {plan_info['daily_return'] * 100:.2f}%

🔒 **PAYMENT DETAILS:**

**Wallet Address:**
`{wallet_address}`
*(Tap to copy)*

💰 **Investment Range:**
• Minimum: ${plan_info['min_amount']:,} USD
• Maximum: ${plan_info['max_amount']:,} USD

⚠️ **IMPORTANT INSTRUCTIONS:**

1️⃣ Send your desired investment amount to the wallet above
2️⃣ Send the **EXACT USD equivalent** in {crypto.upper()}
3️⃣ Click "✅ I've Sent Payment" after sending
4️⃣ Admin will verify and activate your plan

🎯 **Example:**
Want to invest $5,000? Send $5,000 worth of {crypto.upper()} to the address above.

⚡ Your profits start once admin confirms payment!

Click the button below after sending: 👇
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_stock_pages(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle stock page navigation"""
    page = int(data.split("_")[-1])
    stocks_per_page = 10
    start_idx = page * stocks_per_page
    
    page_stocks = ALL_STOCKS[start_idx:start_idx + stocks_per_page]
    
    if not page_stocks:
        await update.callback_query.message.edit_text("❌ No stocks found on this page.")
        return
    
    # Get stock prices
    stock_data = []
    for ticker in page_stocks:
        try:
            price = market.get_current_stock_price(ticker)
            stock_data.append((ticker, price))
        except Exception as e:
            logging.error(f"Error getting price for {ticker}: {e}")
            stock_data.append((ticker, 0))
    
    text = f"📈 **STOCK INVESTMENT - Page {page + 1}**\n\n"
    text += "Choose a stock to purchase:\n\n"
    
    keyboard = []
    for ticker, price in stock_data:
        if price > 0:
            text += f"• **{ticker}**: ${price:.2f}\n"
            keyboard.append([InlineKeyboardButton(f"{ticker} - ${price:.2f}", callback_data=f"buy_stock_{ticker}")])
        else:
            text += f"• **{ticker}**: Price unavailable\n"
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"stocks_page_{page-1}"))
    if start_idx + stocks_per_page < len(ALL_STOCKS):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"stocks_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Invest Menu", callback_data="invest_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_stock_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle stock purchase initiation"""
    ticker = data.replace("buy_stock_", "")
    
    # Get current stock price
    try:
        current_price = market.get_current_stock_price(ticker)
        if current_price <= 0:
            raise ValueError("Invalid price")
    except Exception as e:
        logging.error(f"Error getting stock price: {e}")
        await update.callback_query.message.edit_text(
            f"❌ Unable to get current price for {ticker}. Please try again later.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="stocks_page_0")]])
        )
        return
    
    context.user_data['stock_to_buy'] = ticker
    context.user_data['awaiting_stock_shares'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Stocks", callback_data="stocks_page_0")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
📊 **BUY {ticker.upper()} STOCK**

💰 Current Price: ${current_price:.2f} per share

Please reply with the number of shares you want to purchase:

**Examples:**
• 10 shares = ${current_price * 10:.2f}
• 50 shares = ${current_price * 50:.2f}
• 100 shares = ${current_price * 100:.2f}

Enter number of shares below:
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_stock_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stock payment confirmation button"""
    stock_data = context.user_data.get('awaiting_stock_investment')
    if not stock_data:
        await update.callback_query.message.edit_text("❌ Stock investment session expired. Please start again.")
        return
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="stocks_page_0")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
💸 **STOCK PAYMENT CONFIRMATION**

Please reply with the following information:

**Format:**
```
Amount: $X,XXX
Transaction ID: [your_tx_hash]
```

**Example:**
```
Amount: $5,000
Transaction ID: 0x1234...abcd
```

This helps our admin verify your payment quickly!
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['awaiting_stock_payment_details'] = True

async def show_withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdrawal options"""
    user = update.callback_query.from_user
    user_data = db.get_user(user.id)
    
    if not user_data:
        await update.callback_query.message.edit_text("❌ You're not registered yet. Use /start first!")
        return
    
    current_balance = user_data[8] if len(user_data) > 8 else 0
    
    # Get stock portfolio value
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT stock_ticker, amount_invested_usd, purchase_price
            FROM stock_investments
            WHERE user_id = ? AND status = 'confirmed'
        ''', (user.id,))
        stock_investments = cursor.fetchall()
    
    total_stock_value = 0
    for ticker, amount, price in stock_investments:
        current_price = market.get_current_stock_price(ticker)
        shares = amount / price if price > 0 else 0
        current_value = shares * current_price
        total_stock_value += current_value
    
    if current_balance <= 0 and total_stock_value <= 0:
        text = f"""
❌ **Insufficient Balance**

Your current balance: ${current_balance:.2f}
Your stock portfolio value: ${total_stock_value:.2f}

To withdraw funds, you need to:
- Make an investment first
- Wait for profits to accumulate
- Ensure minimum $10 balance

Use the Invest button to start earning!
        """
        keyboard = [
            [InlineKeyboardButton("💰 Invest Now", callback_data="invest_menu")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Store withdrawal options
    context.user_data['withdraw_options'] = {
        '25%': current_balance * 0.25,
        '50%': current_balance * 0.50,
        '100%': current_balance
    }
    
    keyboard = [
        [InlineKeyboardButton("💸 Withdraw 25%", callback_data="withdraw_25"),
         InlineKeyboardButton("💸 Withdraw 50%", callback_data="withdraw_50")],
        [InlineKeyboardButton("💸 Withdraw 100%", callback_data="withdraw_100"),
         InlineKeyboardButton("💰 Custom Amount", callback_data="withdraw_custom")],
        [InlineKeyboardButton("📈 Sell Stocks", callback_data="withdraw_stocks")],  # ADD THIS LINE
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💸 **WITHDRAWAL CENTER**

💰 **Available Cash Balance:** ${current_balance:,.2f}
📈 **Stock Portfolio Value:** ${total_stock_value:,.2f}
💎 **Total Assets:** ${(current_balance + total_stock_value):,.2f}

**Quick Cash Withdrawals:**
- 25%: ${context.user_data['withdraw_options']['25%']:,.2f}
- 50%: ${context.user_data['withdraw_options']['50%']:,.2f}
- 100%: ${context.user_data['withdraw_options']['100%']:,.2f}

⚡ **Process:**
1. Select amount or sell stocks below
2. Provide USDT wallet address (TRC20)
3. Admin processes within 24 hours

🔒 **Security:**
- All withdrawals verified
- Minimum: $10 USDT
- Network: TRC20 only

Select option below: 👇
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_stock_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stock withdrawal/selling"""
    logging.info("handle_stock_withdrawal triggered by Sell Stocks button.")
    user = update.callback_query.from_user
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT si.id, si.stock_ticker, si.amount_invested_usd, si.purchase_price, si.investment_date
            FROM stock_investments si
            WHERE si.user_id = ? AND si.status = 'confirmed'
            ORDER BY si.investment_date DESC
        ''', (user.id,))
        stocks = cursor.fetchall()
    
    if not stocks:
        text = "📈 **NO STOCKS TO SELL**\n\nYou don't have any confirmed stock investments to sell."
        keyboard = [[InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = "📈 **YOUR STOCK PORTFOLIO**\n\nSelect a stock to sell:\n\n"
    keyboard = []
    
    for stock in stocks:
        stock_id, ticker, invested_amount, purchase_price, date = stock
        current_price = market.get_current_stock_price(ticker)
        shares = invested_amount / purchase_price if purchase_price > 0 else 0
        current_value = shares * current_price
        pnl = current_value - invested_amount
        pnl_percent = (pnl / invested_amount * 100) if invested_amount > 0 else 0
        
        emoji = "📈" if pnl >= 0 else "📉"
        text += f"{emoji} **{ticker.upper()}**\n"
        text += f"   Invested: ${invested_amount:.2f}\n"
        text += f"   Current Value: ${current_value:.2f}\n"
        text += f"   P&L: ${pnl:.2f} ({pnl_percent:+.1f}%)\n\n"
        
        keyboard.append([InlineKeyboardButton(f"Sell {ticker.upper()} - ${current_value:.2f}", 
                                            callback_data=f"sell_stock_{stock_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')


async def handle_withdrawal_options(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle withdrawal option selection"""
    withdrawal_type = data.replace("withdraw_", "")
    
    if withdrawal_type == "custom":
        context.user_data['awaiting_withdraw_amount'] = True
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            "💸 **Custom Withdrawal Amount**\n\n"
            "Please reply with the amount you want to withdraw:\n\n"
            "**Examples:**\n"
            "• 100\n"
            "• 500.50\n"
            "• 1000\n\n"
            "**Note:** Minimum $10, maximum is your available balance.\n"
            "Enter amount below:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return
    
    # Handle percentage withdrawals
    withdraw_options = context.user_data.get('withdraw_options', {})
    
    if withdrawal_type in withdraw_options:
        amount = withdraw_options[withdrawal_type]
        
        context.user_data['pending_withdrawal'] = {
            'amount': amount,
            'user_id': update.callback_query.from_user.id
        }
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="withdraw")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(
            f"💸 **Withdrawal Request: ${amount:,.2f}**\n\n"
            "Please provide your USDT wallet address (TRC20 network only):\n\n"
            "⚠️ **Important:**\n"
            "• Only TRC20 USDT addresses accepted\n"
            "• Double-check your address carefully\n"
            "• Wrong address = permanent loss of funds\n\n"
            "Send your wallet address below:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def show_live_prices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live prices menu"""
    keyboard = [
        [InlineKeyboardButton("💎 Crypto Prices", callback_data="live_crypto_0")],
        [InlineKeyboardButton("📊 Stock Prices", callback_data="live_stock_0")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
📈 **LIVE MARKET PRICES**

Choose the market you want to view:

💎 **Crypto Prices** - Top 20 cryptocurrencies by market cap
📊 **Stock Prices** - Top 20 stocks from major indices

All prices are updated in real-time for accurate trading decisions.

Select an option below: 👇
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_live_crypto_prices(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle live crypto prices display"""
    try:
        crypto_prices = market.get_top_crypto_prices(20)
        
        text = "💎 **LIVE CRYPTO PRICES**\n\n"
        
        for i, (crypto, price) in enumerate(crypto_prices.items(), 1):
            change = f"{(price * 0.02 - 0.01):.2%}"  # Mock price change
            emoji = "📈" if price > 1 else "📊"
            text += f"{i}. **{crypto.replace('-', ' ').title()}** {emoji}\n"
            text += f"   💰 ${price:,.4f} ({change})\n\n"
        
        text += "*Prices update every minute*"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="live_crypto_0")],
            [InlineKeyboardButton("🔙 Live Prices", callback_data="live_prices")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logging.error(f"Error showing crypto prices: {e}")
        await update.callback_query.message.edit_text("❌ Error loading crypto prices. Please try again.")

async def handle_live_stock_prices(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle live stock prices display"""
    try:
        stock_prices = market.get_stock_list_prices(ALL_STOCKS[:20])
        
        text = "📊 **LIVE STOCK PRICES**\n\n"
        
        for i, (ticker, price) in enumerate(stock_prices.items(), 1):
            change = f"{(price * 0.01 - 0.005):.2%}"  # Mock price change
            emoji = "📈" if price > 100 else "📊"
            text += f"{i}. **{ticker}** {emoji}\n"
            text += f"   💰 ${price:,.2f} ({change})\n\n"
        
        text += "*Prices update every minute during market hours*"
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="live_stock_0")],
            [InlineKeyboardButton("🔙 Live Prices", callback_data="live_prices")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logging.error(f"Error showing stock prices: {e}")
        await update.callback_query.message.edit_text("❌ Error loading stock prices. Please try again.")

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show leaderboard"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, rank_position, total_earnings, weekly_earnings, success_rate 
            FROM leaderboard_dummy 
            ORDER BY rank_position ASC 
            LIMIT 8
        ''')
        leaderboard_data = cursor.fetchall()
    
    if not leaderboard_data:
        text = "🏆 LEADERBOARD\n\nNo data available yet.\nStart investing to climb the ranks!"
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = "🏆 **TOP TRADERS LEADERBOARD**\n\n🚀 *See what top investors are earning!*\n\n"
    
    rank_emojis = ["🥇", "🥈", "🥉", "👨‍💼", "👩‍💼", "💎", "🔥", "⚡"]
    
    for i, (username, rank_pos, total_earnings, weekly_earnings, success_rate) in enumerate(leaderboard_data, 1):
        display_name = username.replace('_', ' ')[:18]
        emoji = rank_emojis[i-1] if i <= len(rank_emojis) else f"{i}."
        profit_emoji = "📈" if weekly_earnings > 5000 else "📊"
        
        text += f"{emoji} **{display_name}**\n"
        text += f"   💰 Total: ${total_earnings:,.0f}\n"
        text += f"   {profit_emoji} This Week: +${weekly_earnings:,.0f}\n"
        text += f"   🎯 Success Rate: {success_rate:.1f}%\n\n"
    
    text += "💡 *Join the ranks of successful traders!*\n"
    text += "Start investing today and watch your profits grow! 🚀"
    
    keyboard = [
        [InlineKeyboardButton("💰 Start Investing", callback_data="invest_menu")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile"""
    user = update.callback_query.from_user
    user_data = db.get_user(user.id)
    
    if not user_data:
        await update.callback_query.message.edit_text("❌ You're not registered yet. Use /start first!")
        return
    
    # Unpack user data
    user_id, username, first_name, full_name, email, reg_date, plan, total_invested, current_balance, profit_earned, last_update, referral_code, referred_by = user_data
    
    # Get additional stats
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user.id,))
        referral_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM investments WHERE user_id = ? AND status = "confirmed"', (user.id,))
        investment_count = cursor.fetchone()[0]
    
    text = f"""
👤 **YOUR PROFILE**

📋 **Personal Information:**
• Full Name: {full_name or 'Not provided'}
• Email: {email or 'Not provided'}
• Telegram: @{username}
• Member Since: {reg_date[:10] if reg_date else 'Unknown'}

💼 **Account Summary:**
• Investment Plan: {plan if plan else 'No active plan'}
• Total Invested: ${total_invested:,.2f}
• Current Balance: ${current_balance:,.2f}
• Total Profit: ${profit_earned:,.2f}

📊 **Activity Stats:**
• Investments Made: {investment_count}
• Referrals Made: {referral_count}

🎯 **Referral Code:** `{referral_code}`
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Portfolio", callback_data="portfolio")],
        [InlineKeyboardButton("📜 Transaction History", callback_data="user_history")],  # ADD THIS
        [InlineKeyboardButton("👥 Referrals", callback_data="referrals")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    text = """
📖 **HELP & SUPPORT**

🚀 **Getting Started:**
• Use /start to register
• Complete profile with name and email
• Check leaderboard for inspiration!

💰 **Investing:**
• Choose from Crypto Plans or Stocks
• Send payment to provided addresses
• Admin confirms within 24 hours

💸 **Withdrawing:**
• Minimum $10 USDT (TRC20 only)
• Provide correct wallet address
• Processed within 24 hours

📊 **Tracking:**
• Portfolio shows all investments
• Live Prices for market data
• Real-time profit calculations

👥 **Referrals:**
• Share your code to earn 5% commission
• Use: /start YOURCODE

⚠️ **Security:**
• Double-check wallet addresses
• Use only TRC20 for USDT
• Never share private keys

Need more help? Contact support!
    """
    
    keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment confirmation button"""
    investment_data = context.user_data.get('awaiting_tx_details')
    if not investment_data:
        await update.callback_query.message.edit_text("❌ Investment session expired. Please start again.")
        return
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="crypto_plans")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
💸 **PAYMENT CONFIRMATION**

Please reply with the following information:

**Format:**
```
Amount: $X,XXX
Transaction ID: [your_tx_hash]
Network: [network_name]
```

**Example:**
```
Amount: $5,000
Transaction ID: 0x1234...abcd
Network: Bitcoin
```

This helps our admin verify your payment quickly!
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['awaiting_payment_details'] = True

async def show_user_transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's transaction history"""
    user = update.callback_query.from_user
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get all transactions for user
        cursor.execute('''
            SELECT 'Investment' as type, amount, investment_date as date, status, crypto_type as details
            FROM investments WHERE user_id = ?
            UNION ALL
            SELECT 'Withdrawal' as type, amount, withdrawal_date as date, status, wallet_address as details
            FROM withdrawals WHERE user_id = ?
            UNION ALL
            SELECT 'Stock Purchase' as type, amount_invested_usd as amount, investment_date as date, status, stock_ticker as details
            FROM stock_investments WHERE user_id = ?
            ORDER BY date DESC
            LIMIT 20
        ''', (user.id, user.id, user.id))
        
        transactions = cursor.fetchall()
    
    if not transactions:
        text = "📜 **TRANSACTION HISTORY**\n\nNo transactions found.\nStart investing to see your history here!"
    else:
        text = "📜 **YOUR TRANSACTION HISTORY**\n\n"
        
        for i, (tx_type, amount, date, status, details) in enumerate(transactions[:15], 1):
            status_emoji = {"confirmed": "✅", "pending": "⏳", "rejected": "❌"}.get(status.lower(), "❓")
            type_emoji = {"Investment": "💰", "Withdrawal": "💸", "Stock Purchase": "📈"}.get(tx_type, "📋")
            
            text += f"{i}. {type_emoji} **{tx_type}**\n"
            text += f"   Amount: ${amount:,.2f}\n"
            text += f"   Status: {status_emoji} {status.title()}\n"
            text += f"   Details: {details}\n"
            text += f"   Date: {date[:16] if date else 'N/A'}\n\n"
        
        if len(transactions) > 15:
            text += f"... and {len(transactions) - 15} more transactions"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="user_history")],
        [InlineKeyboardButton("📊 Portfolio", callback_data="portfolio")],
        [InlineKeyboardButton("🔙 Profile", callback_data="profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')