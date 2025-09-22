"""
Text message handlers
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_USER_IDS
from database import db
from handlers.user_handlers import show_main_menu

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user = update.effective_user
    message_text = update.message.text.strip()
    
    # Registration flow
    if context.user_data.get('registration_step') == 'name':
        await handle_registration_name(update, context, message_text)
        return
    
    elif context.user_data.get('registration_step') == 'email':
        await handle_registration_email(update, context, message_text)
        return
    
    # Investment payment details
    elif context.user_data.get('awaiting_payment_details'):
        await handle_payment_details(update, context, message_text)
        return
    
    # Withdrawal amount
    elif context.user_data.get('awaiting_withdraw_amount'):
        await handle_withdrawal_amount(update, context, message_text)
        return
    
    # Withdrawal address
    elif context.user_data.get('pending_withdrawal'):
        await handle_withdrawal_address(update, context, message_text)
        return
    
    # Admin broadcast message
    elif context.user_data.get('awaiting_broadcast_message') and user.id in ADMIN_USER_IDS:
        await handle_broadcast_message(update, context, message_text)
        return
    
    # Stock shares input
    elif context.user_data.get('awaiting_stock_shares'):
        await handle_stock_shares_input(update, context, message_text)
        return
    
    # Stock payment details
    elif context.user_data.get('awaiting_stock_payment_details'):
        await handle_stock_payment_details(update, context, message_text)
        return
    
    # Default response for unhandled messages
    await update.message.reply_text(
        "❌ I didn't understand that. Use /start for the main menu or click a button from the keyboard."
    )

async def handle_registration_name(update: Update, context: ContextTypes.DEFAULT_TYPE, full_name: str):
    """Handle full name input during registration"""
    if len(full_name) < 2:
        await update.message.reply_text("Please provide a valid full name (at least 2 characters):")
        return
    
    context.user_data['full_name'] = full_name
    context.user_data['registration_step'] = 'email'
    await update.message.reply_text("Great! Now please provide your email address:")

async def handle_registration_email(update: Update, context: ContextTypes.DEFAULT_TYPE, email: str):
    """Handle email input during registration"""
    if '@' not in email or '.' not in email:
        await update.message.reply_text("Please provide a valid email address:")
        return
    
    user = update.effective_user
    referred_by_id = context.user_data.get('referred_by_id')
    full_name = context.user_data.get('full_name')
    
    success = db.create_or_update_user(
        user.id, user.username, user.first_name, full_name, email, referred_by_id
    )
    
    if success:
        # Clean up registration data
        context.user_data.pop('registration_step', None)
        context.user_data.pop('full_name', None)
        context.user_data.pop('referred_by_id', None)
        
        await update.message.reply_text(
            "✅ Registration completed! Welcome to Alpha Vault!\n\n"
            "🏆 *Pro Tip:* Check the leaderboard to see what top traders are earning!"
        )
        await show_main_menu(update, context, user)
    else:
        await update.message.reply_text(
            "❌ Registration failed. Please try again or contact support."
        )

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle crypto investment payment details"""
    investment_data = context.user_data.get('awaiting_tx_details')
    if not investment_data:
        await update.message.reply_text("❌ Investment session expired. Please start again.")
        return
    
    # Parse payment details
    lines = message_text.split('\n')
    amount_line = next((line for line in lines if line.strip().lower().startswith('amount:')), None)
    txid_line = next((line for line in lines if line.strip().lower().startswith('transaction id:')), None)
    network_line = next((line for line in lines if line.strip().lower().startswith('network:')), None)
    
    if not all([amount_line, txid_line]):
        await update.message.reply_text(
            "❌ Invalid format. Please include:\n"
            "```\n"
            "Amount: $X,XXX\n"
            "Transaction ID: [your_tx_hash]\n"
            "Network: [network_name]\n"
            "```",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Extract values
        amount_str = amount_line.split(':', 1)[1].strip().replace('$', '').replace(',', '')
        amount = float(amount_str)
        tx_id = txid_line.split(':', 1)[1].strip()
        network = network_line.split(':', 1)[1].strip() if network_line else 'Not specified'
        
        # Validate amount against plan
        plan_info = investment_data['plan_info']
        notes = None
        if amount < plan_info['min_amount']:
            notes = f"Amount (${amount}) below minimum (${plan_info['min_amount']}). Needs review."
        
        # Save investment to database
        success = db.add_investment(
            investment_data['user_id'],
            amount,
            investment_data['crypto'],
            investment_data['wallet_address'],
            tx_id,
            investment_data['plan_type'].upper(),
            notes
        )
        
        if success:
            await update.message.reply_text(
                "✅ **Payment Submitted Successfully!**\n\n"
                f"💰 Amount: ${amount:,.2f}\n"
                f"💎 Crypto: {investment_data['crypto'].upper()}\n"
                f"📄 Transaction ID: `{tx_id}`\n\n"
                "⏳ Your investment is pending admin confirmation.\n"
                "You'll be notified once verified and your portfolio will be updated!",
                parse_mode='Markdown'
            )
            
            # Notify admins
            await notify_admins_new_investment(context, investment_data, amount, tx_id, network)
        else:
            await update.message.reply_text("❌ Failed to save investment. Please try again.")
    
    except (ValueError, IndexError) as e:
        logging.error(f"Error parsing payment details: {e}")
        await update.message.reply_text("❌ Invalid format. Please check your input and try again.")
    
    # Clean up
    context.user_data.pop('awaiting_payment_details', None)
    context.user_data.pop('awaiting_tx_details', None)

async def handle_withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle custom withdrawal amount input"""
    try:
        amount = float(message_text.replace('$', '').replace(',', ''))
        user = update.effective_user
        user_data = db.get_user(user.id)
        
        if not user_data:
            await update.message.reply_text("❌ User data not found.")
            return
        
        current_balance = user_data[8] if len(user_data) > 8 else 0
        
        if amount < 10:
            await update.message.reply_text("❌ Minimum withdrawal amount is $10.")
            return
        
        if amount > current_balance:
            await update.message.reply_text(f"❌ Insufficient balance. Available: ${current_balance:,.2f}")
            return
        
        context.user_data['pending_withdrawal'] = {
            'amount': amount,
            'user_id': user.id
        }
        context.user_data.pop('awaiting_withdraw_amount', None)
        
        await update.message.reply_text(
            f"💸 **Withdrawal Request: ${amount:,.2f}**\n\n"
            "Please provide your USDT wallet address (TRC20 network only):\n\n"
            "⚠️ **Important:**\n"
            "• Only TRC20 USDT addresses accepted\n"
            "• Double-check your address carefully\n"
            "• Wrong address = permanent loss of funds\n\n"
            "Send your wallet address below:",
            parse_mode='Markdown'
        )
    
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Please enter a valid number.")

async def handle_withdrawal_address(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_address: str):
    """Handle withdrawal wallet address input"""
    withdrawal_data = context.user_data.get('pending_withdrawal')
    if not withdrawal_data:
        await update.message.reply_text("❌ Withdrawal session expired. Please start again.")
        return
    
    amount = withdrawal_data['amount']
    user_id = withdrawal_data['user_id']
    
    # Basic validation for USDT TRC20 address
    if not wallet_address.startswith('T') or len(wallet_address) != 34:
        await update.message.reply_text(
            "❌ Invalid USDT TRC20 address format.\n\n"
            "TRC20 addresses should:\n"
            "• Start with 'T'\n"
            "• Be exactly 34 characters long\n\n"
            "Please provide a valid address:"
        )
        return
    
    # Save withdrawal request
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO withdrawals (user_id, amount, wallet_address)
                VALUES (?, ?, ?)
            ''', (user_id, amount, wallet_address))
            conn.commit()
        
        await update.message.reply_text(
            "✅ **Withdrawal Request Submitted!**\n\n"
            f"💰 Amount: ${amount:,.2f}\n"
            f"💳 Address: `{wallet_address}`\n\n"
            "⏰ Your request will be processed within 24 hours.\n"
            "You'll receive a confirmation once the funds are sent!",
            parse_mode='Markdown'
        )
        
        # Notify admins
        await notify_admins_new_withdrawal(context, user_id, amount, wallet_address)
        
    except Exception as e:
        logging.error(f"Error saving withdrawal: {e}")
        await update.message.reply_text("❌ Failed to save withdrawal request. Please try again.")
    
    # Clean up
    context.user_data.pop('pending_withdrawal', None)

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle admin broadcast message"""
    if len(message_text) > 2000:
        await update.message.reply_text("❌ Message too long. Maximum 2000 characters.")
        return
    
    # Get all users
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
    
    success_count = 0
    total_users = len(users)
    
    # Send broadcast message
    for user_tuple in users:
        try:
            await context.bot.send_message(
                chat_id=user_tuple[0],
                text=f"📢 **ANNOUNCEMENT**\n\n{message_text}",
                parse_mode='Markdown'
            )
            success_count += 1
            await asyncio.sleep(0.1)  # Rate limiting
        except Exception as e:
            logging.error(f"Failed to send broadcast to {user_tuple[0]}: {e}")
    
    await update.message.reply_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"📊 Sent to: {success_count}/{total_users} users\n"
        f"📈 Success Rate: {(success_count/total_users)*100:.1f}%"
    )
    
    context.user_data.pop('awaiting_broadcast_message', None)

async def handle_stock_shares_input(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle stock shares input"""
    try:
        shares = int(message_text)
        if shares <= 0:
            await update.message.reply_text("❌ Please enter a positive number of shares.")
            return
        
        ticker = context.user_data.get('stock_to_buy')
        if not ticker:
            await update.message.reply_text("❌ Stock selection expired. Please start again.")
            return
        
        # Get current stock price
        from market_data import market
        current_price = market.get_current_stock_price(ticker)
        
        if current_price <= 0:
            await update.message.reply_text("❌ Unable to get current price. Please try again later.")
            return
        
        total_cost = shares * current_price
        
        # Store stock investment data
        context.user_data['awaiting_stock_investment'] = {
            'ticker': ticker,
            'shares': shares,
            'price_per_share': current_price,
            'total_cost': total_cost,
            'user_id': update.effective_user.id
        }
        
        # Get random USDT wallet
        from handlers.user_handlers import get_random_wallet
        usdt_wallet = get_random_wallet('usdt')
        
        keyboard = [
            [InlineKeyboardButton("✅ I've Sent Payment", callback_data="confirm_stock_payment")],
            [InlineKeyboardButton("🔙 Back to Stocks", callback_data="stocks_page_0")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"📈 **BUY {ticker.upper()} STOCK**\n\n"
            f"**Order Details:**\n"
            f"• Shares: {shares}\n"
            f"• Price per Share: ${current_price:,.2f}\n"
            f"• Total Cost: ${total_cost:,.2f}\n\n"
            f"**Payment Instructions:**\n"
            f"Send the equivalent of ${total_cost:,.2f} in USDT to:\n\n"
            f"`{usdt_wallet}`\n\n"
            f"⚠️ Send exact USD equivalent in USDT (TRC20)\n"
            f"Click 'I've Sent Payment' after sending to provide transaction details.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        context.user_data.pop('awaiting_stock_shares', None)
        context.user_data.pop('stock_to_buy', None)
        context.user_data['awaiting_stock_payment_details'] = True
    
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number of shares.")

async def handle_stock_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle stock payment details"""
    stock_data = context.user_data.get('awaiting_stock_investment')
    if not stock_data:
        await update.message.reply_text("❌ Stock investment session expired. Please start again.")
        return
    
    # Parse payment details (similar to crypto)
    lines = message_text.split('\n')
    amount_line = next((line for line in lines if line.strip().lower().startswith('amount:')), None)
    txid_line = next((line for line in lines if line.strip().lower().startswith('transaction id:')), None)
    
    if not all([amount_line, txid_line]):
        await update.message.reply_text(
            "❌ Invalid format. Please include:\n"
            "```\n"
            "Amount: $X,XXX\n"
            "Transaction ID: [your_tx_hash]\n"
            "```",
            parse_mode='Markdown'
        )
        return
    
    try:
        amount_str = amount_line.split(':', 1)[1].strip().replace('$', '').replace(',', '')
        amount = float(amount_str)
        tx_id = txid_line.split(':', 1)[1].strip()
        
        # Save stock investment
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO stock_investments (user_id, amount_invested_usd, stock_ticker, purchase_price)
                VALUES (?, ?, ?, ?)
            ''', (stock_data['user_id'], amount, stock_data['ticker'], stock_data['price_per_share']))
            conn.commit()
        
        await update.message.reply_text(
            "✅ **Stock Investment Submitted!**\n\n"
            f"📈 Stock: {stock_data['ticker'].upper()}\n"
            f"💰 Amount: ${amount:,.2f}\n"
            f"📊 Price: ${stock_data['price_per_share']:,.2f}\n"
            f"📄 Transaction ID: `{tx_id}`\n\n"
            "⏳ Your stock purchase is pending admin confirmation.\n"
            "You'll be notified once verified!",
            parse_mode='Markdown'
        )
        
        # Notify admins about stock investment
        await notify_admins_new_stock_investment(context, stock_data, amount, tx_id)
    
    except (ValueError, IndexError) as e:
        logging.error(f"Error parsing stock payment details: {e}")
        await update.message.reply_text("❌ Invalid format. Please check your input and try again.")
    
    # Clean up
    context.user_data.pop('awaiting_stock_payment_details', None)
    context.user_data.pop('awaiting_stock_investment', None)

# Notification helper functions
async def notify_admins_new_investment(context, investment_data, amount, tx_id, network):
    """Notify admins about new crypto investment"""
    user_id = investment_data['user_id']
    
    # Get user details
    user_data = db.get_user(user_id)
    if user_data:
        full_name = user_data[3] or 'N/A'
        email = user_data[4] or 'N/A'
        username = user_data[1] or 'N/A'
    else:
        full_name = email = username = 'N/A'
    
    notification = f"""
🚨 **NEW CRYPTO INVESTMENT** 🚨

👤 **User Details:**
• Name: {full_name}
• Email: {email}
• Username: @{username}
• User ID: {user_id}

💰 **Investment Details:**
• Amount: ${amount:,.2f}
• Crypto: {investment_data['crypto'].upper()}
• Plan: {investment_data['plan_type'].upper()}
• Transaction ID: `{tx_id}`
• Network: {network}
• Wallet: `{investment_data['wallet_address']}`

⚠️ **Action Required:** Verify transaction before confirming.

**Command:** `/confirm_investment {user_id} {amount}`
    """
    
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification.strip(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

async def notify_admins_new_withdrawal(context, user_id, amount, wallet_address):
    """Notify admins about new withdrawal request"""
    user_data = db.get_user(user_id)
    if user_data:
        full_name = user_data[3] or 'N/A'
        email = user_data[4] or 'N/A'
        username = user_data[1] or 'N/A'
    else:
        full_name = email = username = 'N/A'
    
    notification = f"""
🚨 **NEW WITHDRAWAL REQUEST** 🚨

👤 **User Details:**
• Name: {full_name}
• Email: {email}
• Username: @{username}
• User ID: {user_id}

💸 **Withdrawal Details:**
• Amount: ${amount:,.2f}
• Wallet: `{wallet_address}`
• Network: TRC20 (USDT)
• Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

⚠️ **Action Required:** Verify user identity and wallet address.

**Command:** `/confirm_withdrawal {user_id}`
    """
    
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification.strip(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")

async def notify_admins_new_stock_investment(context, stock_data, amount, tx_id):
    """Notify admins about new stock investment"""
    user_id = stock_data['user_id']
    
    user_data = db.get_user(user_id)
    if user_data:
        full_name = user_data[3] or 'N/A'
        email = user_data[4] or 'N/A'
        username = user_data[1] or 'N/A'
    else:
        full_name = email = username = 'N/A'
    
    notification = f"""
📈 **NEW STOCK INVESTMENT** 📈

👤 **User Details:**
• Name: {full_name}
• Email: {email}
• Username: @{username}
• User ID: {user_id}

📊 **Stock Details:**
• Stock: {stock_data['ticker'].upper()}
• Amount: ${amount:,.2f}
• Price per Share: ${stock_data['price_per_share']:,.2f}
• Transaction ID: `{tx_id}`

⚠️ **Action Required:** Verify payment and purchase stock.

**Command:** `/confirm_stock {user_id} {amount}`
    """
    
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=notification.strip(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id}: {e}")