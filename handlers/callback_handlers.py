"""
Callback query handlers for inline keyboards
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import InvestmentPlan, TECH_STOCKS, NON_TECH_STOCKS
from database import db
from market_data import market
from handlers.user_handlers import show_main_menu, get_random_wallet

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main callback query handler"""
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
        
        # Withdrawal
        elif data.startswith("withdraw_"):
            await handle_withdrawal_options(update, context, data)
        
        # Live prices
        elif data.startswith("live_crypto_"):
            await handle_live_crypto_prices(update, context, data)
        
        elif data.startswith("live_stock_"):
            await handle_live_stock_prices(update, context, data)

        elif data.startswith("admin_"):
            if user.id in ADMIN_USER_IDS:
                from handlers.admin_handlers import handle_admin_callback, admin_command
                if data == "admin_panel":
                    await admin_command(update, context)
                else:
                    await handle_admin_callback(update, context, data)
            else:
                await query.message.edit_text(
                    "❌ You do not have permission to access the admin panel.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
                )
    
    except Exception as e:
        logging.error(f"Error in callback handler for '{data}': {e}")
        await query.message.edit_text(
            "❌ An error occurred. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
        )

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

🔑 **PAYMENT DETAILS:**

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

async def show_withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdrawal options"""
    user = update.callback_query.from_user
    user_data = db.get_user(user.id)
    
    if not user_data:
        await update.callback_query.message.edit_text("❌ You're not registered yet. Use /start first!")
        return
    
    current_balance = user_data[8] if len(user_data) > 8 else 0
    
    if current_balance <= 0:
        text = f"""
❌ **Insufficient Balance**

Your current balance: ${current_balance:.2f}

To withdraw funds, you need to:
• Make an investment first
• Wait for profits to accumulate
• Ensure minimum $10 balance

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
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
💸 **WITHDRAWAL CENTER**

💰 **Available Balance:** ${current_balance:,.2f}

**Quick Options:**
• 25%: ${context.user_data['withdraw_options']['25%']:,.2f}
• 50%: ${context.user_data['withdraw_options']['50%']:,.2f}
• 100%: ${context.user_data['withdraw_options']['100%']:,.2f}

⚡ **Process:**
1. Select amount below
2. Provide USDT wallet address (TRC20)
3. Admin processes within 24 hours

🔒 **Security:**
• All withdrawals verified
• Minimum: $10 USDT
• Network: TRC20 only

Select option below: 👇
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

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
# Add these functions to callback_handlers.py

async def handle_stock_pages(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle stock page navigation"""
    page = int(data.split("_")[-1])
    stocks_per_page = 10
    start_idx = page * stocks_per_page
    
    from config import ALL_STOCKS
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
        except:
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
    except:
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

# Additional handler functions would go here...
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