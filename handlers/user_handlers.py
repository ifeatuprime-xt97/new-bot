"""
User command handlers
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import InvestmentPlan, WALLET_ADDRESSES, ADMIN_USER_IDS
from database import db
from market_data import market
import random

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    if not user.username:
        await update.message.reply_text(
            "⚠️ Username Required!\n\n"
            "Please set a Telegram username first:\n"
            "1. Go to Settings → Edit Profile\n"
            "2. Create a username\n"
            "3. Come back and use /start again\n\n"
            "A username is required for security and tracking."
        )
        return
    
    # Check if user is registered
    user_data = db.get_user(user.id)
    if user_data and len(user_data) >= 5 and user_data[3] and user_data[4]:  # Has full_name and email
        await show_main_menu(update, context, user)
        return
    
    # Handle referral code
    referred_by_id = None
    if context.args and len(context.args) > 0:
        referral_code = context.args[0]
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
            referrer = cursor.fetchone()
            if referrer:
                referred_by_id = referrer[0]
    
    context.user_data['referred_by_id'] = referred_by_id
    context.user_data['registration_step'] = 'name'
    
    await update.message.reply_text(
        "🚀 Welcome to The Alpha Vault Investment Platform!\n\n"
        "To get started, please provide your full name:"
    )

async def show_main_menu(update, context, user):
    """Display the main menu"""
    keyboard = [
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
         InlineKeyboardButton("💰 Invest", callback_data="invest_menu")],
        [InlineKeyboardButton("📊 Portfolio", callback_data="portfolio")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("📈 Live Prices", callback_data="live_prices")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile"),
         InlineKeyboardButton("📖 Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🚀 Welcome to The Alpha Vault Investment Platform!

Hello {user.first_name}! Your AI-powered crypto investment hub.

🏆 *Check the leaderboard to see what top traders are earning!*

💎 Investment Plans:
• 🥉 Core: $1K-$15K (1.43% daily)
• 🥈 Growth: $20K-$80K (2.14% daily) 
• 🥇 Alpha: $100K+ (2.86% daily)

🎯 Features:
• Automated daily profits
• Secure multi-crypto wallets
• Real-time portfolio tracking
• Instant withdrawals
• Referral bonuses

⚡ *Start your journey to the top!* 👇
    """
    
    if update.message:
        await update.message.reply_text(welcome_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.edit_text(welcome_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user portfolio"""
    user = update.effective_user
    
    try:
        user_data = db.get_user(user.id)
        if not user_data:
            error_msg = "❌ You're not registered yet. Use /start first!"
            if update.message:
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.message.edit_text(error_msg)
            return
        
        # Calculate profits first
        calculate_user_profits()
        user_data = db.get_user(user.id)  # Refresh data
        
        if len(user_data) < 13:
            logging.error(f"Incomplete user data for user {user.id}")
            error_msg = "❌ Account data incomplete. Please contact support."
            if update.message:
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.message.edit_text(error_msg)
            return
        
        # Unpack user data safely
        (user_id, username, first_name, full_name, email, reg_date, 
         plan, total_invested, current_balance, profit_earned, 
         last_update, referral_code, referred_by) = user_data
        
        # Get stock data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT stock_ticker, amount_invested_usd, purchase_price
                FROM stock_investments
                WHERE user_id = ? AND status = 'confirmed'
            ''', (user.id,))
            stock_investments = cursor.fetchall()
        
        # Calculate stock P&L
        total_stock_pnl = 0
        total_stock_invested = 0
        for ticker, amount, price in stock_investments:
            total_stock_invested += amount
            pnl = market.calculate_stock_pnl(ticker, amount, price)
            total_stock_pnl += pnl
        
        # Build portfolio text
        portfolio_text = f"""📊 YOUR INVESTMENT PORTFOLIO

👤 Account Details:
• Username: @{username or 'N/A'}
• Plan: {plan if plan else 'No active plan'}
• Member Since: {reg_date[:10] if reg_date else 'Unknown'}

💰 Financial Summary:
• Total Crypto Invested: ${total_invested:,.2f}
• Current Crypto Balance: ${current_balance:,.2f}
• Total Crypto Profit: ${profit_earned:,.2f}"""
        
        # Add ROI calculation
        if total_invested > 0:
            roi = ((current_balance / total_invested - 1) * 100)
            portfolio_text += f"\n• Crypto ROI: {roi:.2f}%"
        
        # Add stock information
        if stock_investments:
            portfolio_text += f"\n\n📈 Stock Portfolio:"
            portfolio_text += f"\n• Total Stock Invested: ${total_stock_invested:,.2f}"
            portfolio_text += f"\n• Current Stock P&L: ${total_stock_pnl:,.2f}"
        
        # Add daily earnings
        if total_invested > 0 and plan:
            plan_map = {
                'CORE': InvestmentPlan.CORE.value,
                'GROWTH': InvestmentPlan.GROWTH.value,
                'ALPHA': InvestmentPlan.ALPHA.value
            }
            plan_info = plan_map.get(plan.upper())
            if plan_info:
                daily_earnings = total_invested * plan_info['daily_return']
                portfolio_text += f"\n\n💎 Daily Crypto Earnings: ${daily_earnings:.2f}"
        
        portfolio_text += f"\n\n🎁 Referral Code: `{referral_code}`"
        portfolio_text += "\nShare your code and earn 5% commission!"
        
        keyboard = [
            [InlineKeyboardButton("💰 Invest More", callback_data="invest_menu"),
             InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton("👥 Referrals", callback_data="referrals"),
             InlineKeyboardButton("🔄 Refresh", callback_data="refresh_portfolio")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(portfolio_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
        elif update.callback_query:
            await update.callback_query.message.edit_text(portfolio_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    
    except Exception as e:
        logging.error(f"Error in portfolio_command: {e}")
        error_text = "❌ Error loading portfolio. Please try again later."
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(error_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(error_text, reply_markup=reply_markup)

def calculate_user_profits():
    """Calculate and update user profits"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get users with investments
            cursor.execute('''
                SELECT user_id, total_invested, current_balance, plan, last_profit_update
                FROM users
                WHERE total_invested > 0 AND plan IS NOT NULL
            ''')
            users = cursor.fetchall()
            
            for user_id, total_invested, current_balance, plan, last_update in users:
                try:
                    last_update_date = datetime.fromisoformat(last_update)
                    days_passed = (datetime.now() - last_update_date).days
                    
                    if days_passed >= 1:
                        plan_map = {
                            'CORE': InvestmentPlan.CORE.value,
                            'GROWTH': InvestmentPlan.GROWTH.value,
                            'ALPHA': InvestmentPlan.ALPHA.value
                        }
                        plan_info = plan_map.get(plan.upper())
                        
                        if plan_info and total_invested >= plan_info['min_amount']:
                            daily_return = plan_info['daily_return']
                            profit = total_invested * daily_return * days_passed
                            new_balance = current_balance + profit
                            
                            cursor.execute('''
                                UPDATE users
                                SET current_balance = ?, profit_earned = profit_earned + ?, last_profit_update = ?
                                WHERE user_id = ?
                            ''', (new_balance, profit, datetime.now().isoformat(), user_id))
                
                except Exception as e:
                    logging.error(f"Error calculating profit for user {user_id}: {e}")
            
            conn.commit()
    
    except Exception as e:
        logging.error(f"Error in calculate_user_profits: {e}")

def get_random_wallet(crypto_type: str) -> str:
    """Get random wallet address for crypto type"""
    if crypto_type.lower() in WALLET_ADDRESSES:
        return random.choice(WALLET_ADDRESSES[crypto_type.lower()])
    return None