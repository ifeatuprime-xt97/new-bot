"""
Text message handlers
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .utils import log_admin_action
from config import ADMIN_USER_IDS
from database import db
from handlers.user_handlers import show_main_menu
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
    await send_temporary_message(
    update, context,
    "❌ I didn't understand that. Use /start for the main menu or click a button from the keyboard.",
    delete_after=60  # Shorter timeout for error messages
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
        
        await send_temporary_message(
            update, context,
            "✅ Registration completed! Welcome to Alpha Vault!\n\n"
            "🏆 *Pro Tip:* Check the leaderboard to see what top traders are earning!",
            delete_after=120
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
            await send_temporary_message(
            update, context,
            "✅ **Payment Submitted Successfully!**\n\n"
            f"💰 Amount: ${amount:,.2f}\n"
            f"💎 Crypto: {investment_data['crypto'].upper()}\n"
            f"📄 Transaction ID: `{tx_id}`\n\n"
            "⏳ Your investment is pending admin confirmation.\n"
            "You'll be notified once verified and your portfolio will be updated!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]),
            parse_mode='Markdown',
            delete_after=120
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
        
        await send_temporary_message(
        update, context,
        "✅ **Withdrawal Request Submitted!**\n\n"
        f"💰 Amount: ${amount:,.2f}\n"
        f"💳 Address: `{wallet_address}`\n\n"
        "⏰ Your request will be processed within 24 hours.\n"
        "You'll receive a confirmation once the funds are sent!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]),
        parse_mode='Markdown',
        delete_after=120
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
    async def handle_stock_sale(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
        """Process a stock sale request, update DB, notify admin, and request approval/rejection."""
        user = update.effective_user
        # Fetch stock info from DB
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT stock_ticker, shares, purchase_price FROM stock_investments WHERE id = ?', (stock_id,))
            stock = cursor.fetchone()
        if not stock:
            await update.callback_query.message.edit_text("❌ Stock not found or invalid sale request.")
            return
        ticker, shares, purchase_price = stock
        # Mark sale request in DB (add a pending sale entry)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO stock_sales (user_id, stock_id, stock_ticker, shares, purchase_price, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user.id, stock_id, ticker, shares, purchase_price, 'pending'))
            conn.commit()
        # Notify user
        await update.callback_query.message.edit_text(
            f"✅ Stock sale request submitted for {shares} shares of {ticker.upper()} at ${purchase_price:,.2f} per share.\n\nYour request is pending admin approval.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
        )
        # Notify admins
        for admin_id in ADMIN_USER_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"🚨 **NEW STOCK SALE REQUEST** 🚨\n\n"
                        f"👤 User: @{user.username or user.id}\n"
                        f"Stock: {ticker.upper()}\nShares: {shares}\nPurchase Price: ${purchase_price:,.2f}\n"
                        f"Sale ID: {stock_id}\n\n"
                        f"Approve or reject this sale in the admin panel."
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Failed to notify admin {admin_id} about stock sale: {e}")
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

# Add these functions to your message_handlers.py for admin functionality

async def handle_admin_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle admin-specific text message inputs"""
    user = update.effective_user
    
    # Only process for admin users
    if user.id not in ADMIN_USER_IDS:
        return False  # Not handled by admin system
    
    # Handle user search
    if context.user_data.get('awaiting_user_search'):
        await handle_user_search_input(update, context, message_text)
        return True
    
    # Handle balance editing - user ID input
    elif context.user_data.get('awaiting_balance_user_id'):
        await handle_balance_user_id_input(update, context, message_text)
        return True
    
    # Handle balance editing - amount input
    elif context.user_data.get('awaiting_balance_amount'):
        await handle_balance_amount_input(update, context, message_text)
        return True
    
    # Handle broadcast message
    elif context.user_data.get('awaiting_broadcast_message'):
        await handle_broadcast_message_admin(update, context, message_text)
        return True
    
    return False  # Not handled by admin system

async def handle_user_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE, search_term: str):
    """Handle user search input from admin"""
    search_term = search_term.strip()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Try different search methods
            users = []
            
            # Search by user ID
            if search_term.isdigit():
                cursor.execute('SELECT * FROM users WHERE user_id = ?', (int(search_term),))
                user = cursor.fetchone()
                if user:
                    users.append(user)
            
            # Search by username
            if not users:
                username = search_term.replace('@', '')
                cursor.execute('SELECT * FROM users WHERE username LIKE ?', (f'%{username}%',))
                users = cursor.fetchall()
            
            # Search by email
            if not users and '@' in search_term:
                cursor.execute('SELECT * FROM users WHERE email LIKE ?', (f'%{search_term}%',))
                users = cursor.fetchall()
            
            # Search by name
            if not users:
                cursor.execute('SELECT * FROM users WHERE full_name LIKE ?', (f'%{search_term}%',))
                users = cursor.fetchall()
    
    except Exception as e:
        logging.error(f"Error in user search: {e}")
        await update.message.reply_text("❌ Error performing search. Please try again.")
        context.user_data.pop('awaiting_user_search', None)
        return
    
    if not users:
        keyboard = [
            [InlineKeyboardButton("🔍 Try Again", callback_data="admin_search_user")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"❌ No users found matching '{search_term}'\n\n"
            "Try searching by:\n"
            "• User ID (numbers only)\n"
            "• Username (with or without @)\n"
            "• Email address\n"
            "• Full name",
            reply_markup=reply_markup
        )
    else:
        text = f"🔍 **SEARCH RESULTS** ({len(users)} found)\n\n"
        keyboard = []
        
        for user in users[:10]:  # Limit to 10 results
            user_id, username, first_name, full_name, email, reg_date, plan, invested, balance, profit, last_update, referral_code, referred_by = user
            
            text += f"**ID:** {user_id}\n"
            text += f"**Username:** @{username or 'N/A'}\n"
            text += f"**Name:** {full_name or 'N/A'}\n"
            text += f"**Email:** {email or 'N/A'}\n"
            text += f"**Balance:** ${balance:,.2f}\n"
            text += f"**Invested:** ${invested:,.2f}\n"
            text += "─────────────\n"
            
            keyboard.append([InlineKeyboardButton(f"View {username or user_id}", callback_data=f"admin_user_profile_{user_id}")])
        
        if len(users) > 10:
            text += f"\n... and {len(users) - 10} more results"
        
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    
    context.user_data.pop('awaiting_user_search', None)

async def handle_balance_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str):
    """Handle user ID input for balance editing"""
    try:
        user_id = int(user_id_str.strip())
        
        # Verify user exists
        user_data = db.get_user(user_id)
        if not user_data:
            keyboard = [
                [InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
                [InlineKeyboardButton("🔙 Balance Menu", callback_data="admin_edit_balance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"❌ User with ID {user_id} not found.\n\n"
                "Please check the User ID or use Search User to find the correct ID.",
                reply_markup=reply_markup
            )
            context.user_data.pop('awaiting_balance_user_id', None)
            return
        
        # Store user data for next step
        context.user_data['balance_target_user'] = user_data
        context.user_data.pop('awaiting_balance_user_id', None)
        
        action = context.user_data.get('balance_action')
        current_balance = user_data[8]  # current_balance field
        username = user_data[1]
        full_name = user_data[3]
        
        if action == "reset":
            # Direct reset, no amount needed
            await confirm_balance_change(update, context, 0, "RESET")
        else:
            context.user_data['awaiting_balance_amount'] = True
            
            action_text = {
                "add": "ADD to",
                "subtract": "SUBTRACT from", 
                "set": "SET as new balance for"
            }
            
            keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data="admin_edit_balance")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"💳 **{action_text[action].upper()} USER BALANCE**\n\n"
                f"**User:** @{username} ({full_name or 'N/A'})\n"
                f"**Current Balance:** ${current_balance:,.2f}\n\n"
                f"Enter the amount to {action}:\n\n"
                f"**Examples:**\n"
                f"• 100\n"
                f"• 500.50\n"
                f"• 1000\n\n"
                f"Type the amount below:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid User ID. Please enter numbers only.\n\n"
            "Example: 123456789"
        )

async def handle_balance_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE, amount_str: str):
    """Handle amount input for balance editing"""
    try:
        amount = float(amount_str.strip().replace('$', '').replace(',', ''))
        
        if amount < 0:
            await update.message.reply_text("❌ Amount cannot be negative. Please enter a positive number.")
            return
        
        action = context.user_data.get('balance_action')
        if action == 'subtract' and amount <= 0:
            await update.message.reply_text("❌ Subtraction amount must be greater than 0.")
            return
        
        await confirm_balance_change(update, context, amount, action.upper())
    
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount format.\n\n"
            "Please enter a valid number:\n"
            "• 100\n"
            "• 500.50\n"
            "• 1000"
        )

async def confirm_balance_change(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: float, action: str):
    """Show confirmation for balance change"""
    user_data = context.user_data.get('balance_target_user')
    if not user_data:
        await update.message.reply_text("❌ Session expired. Please start over.")
        return
    
    target_user_id = user_data[0]
    username = user_data[1]
    full_name = user_data[3]
    current_balance = user_data[8]
    
    # Calculate new balance
    if action == "ADD":
        new_balance = current_balance + amount
    elif action == "SUBTRACT":
        new_balance = max(0, current_balance - amount)  # Don't go negative
    elif action == "SET":
        new_balance = amount
    elif action == "RESET":
        new_balance = 0
        amount = current_balance  # For logging purposes
    
    # Store confirmation data
    context.user_data['balance_confirmation'] = {
        'target_user_id': target_user_id,
        'username': username,
        'full_name': full_name,
        'action': action,
        'amount': amount,
        'old_balance': current_balance,
        'new_balance': new_balance
    }
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="admin_confirm_balance_change")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_edit_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    warning = ""
    if action == "SUBTRACT" and amount > current_balance:
        warning = "\n⚠️ **Warning:** Amount exceeds current balance. Balance will be set to $0.00"
    
    await update.message.reply_text(
        f"⚠️ **CONFIRM BALANCE CHANGE**\n\n"
        f"**User:** @{username} ({full_name or 'N/A'})\n"
        f"**Action:** {action}\n"
        f"**Amount:** ${amount:,.2f}\n"
        f"**Current Balance:** ${current_balance:,.2f}\n"
        f"**New Balance:** ${new_balance:,.2f}\n"
        f"{warning}\n\n"
        f"⚠️ **This action cannot be undone!**\n"
        f"Are you sure you want to proceed?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Clean up temporary states
    context.user_data.pop('awaiting_balance_amount', None)
    context.user_data.pop('balance_action', None)
    context.user_data.pop('balance_target_user', None)

async def handle_broadcast_message_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle broadcast message from admin"""
    if len(message_text) > 2000:
        await update.message.reply_text("❌ Message too long. Maximum 2000 characters allowed.")
        return
    
    # Store message for confirmation
    context.user_data['broadcast_message'] = message_text
    context.user_data.pop('awaiting_broadcast_message', None)
    
    keyboard = [
        [InlineKeyboardButton("✅ Send Broadcast", callback_data="admin_confirm_broadcast")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get user count
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
    
    await update.message.reply_text(
        f"📢 **BROADCAST PREVIEW**\n\n"
        f"**Message:**\n{message_text}\n\n"
        f"**Recipients:** {user_count} users\n\n"
        f"⚠️ **Warning:** This will send the message to all users immediately and cannot be undone!\n\n"
        f"Are you sure you want to send this broadcast?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Add these callback handlers to your existing admin_handlers.py

async def handle_balance_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance change confirmation callback"""
    confirmation_data = context.user_data.get('balance_confirmation')
    if not confirmation_data:
        await update.callback_query.message.edit_text("❌ Session expired. Please start over.")
        return
    
    target_user_id = confirmation_data['target_user_id']
    username = confirmation_data['username']
    full_name = confirmation_data['full_name']
    action = confirmation_data['action']
    amount = confirmation_data['amount']
    old_balance = confirmation_data['old_balance']
    new_balance = confirmation_data['new_balance']
    
    admin_id = update.callback_query.from_user.id
    
    try:
        # Update user balance in database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET current_balance = ? WHERE user_id = ?
            ''', (new_balance, target_user_id))
            conn.commit()
        
        # Log the admin action
        log_admin_action(
            admin_id=admin_id,
            action_type=f"balance_{action.lower()}",
            target_user_id=target_user_id,
            amount=amount,
            old_balance=old_balance,
            new_balance=new_balance,
            notes=f"Admin balance modification: {action}"
        )
        
        # Send confirmation
        await update.callback_query.message.edit_text(
            f"✅ **BALANCE UPDATED SUCCESSFULLY**\n\n"
            f"**User:** @{username} ({full_name or 'N/A'})\n"
            f"**Action:** {action}\n"
            f"**Amount:** ${amount:,.2f}\n"
            f"**Previous Balance:** ${old_balance:,.2f}\n"
            f"**New Balance:** ${new_balance:,.2f}\n\n"
            f"✅ Change has been logged in admin records.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Edit Another Balance", callback_data="admin_edit_balance")],
                [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode='Markdown'
        )
        
        # Notify the user about balance change
        try:
            if action == "ADD":
                notification = f"🎉 **BALANCE UPDATED!**\n\n💰 ${amount:,.2f} has been added to your account!\n\nNew Balance: ${new_balance:,.2f}"
            elif action == "SUBTRACT":
                notification = f"ℹ️ **BALANCE UPDATED**\n\n💸 ${amount:,.2f} has been deducted from your account.\n\nNew Balance: ${new_balance:,.2f}"
            elif action == "SET":
                notification = f"ℹ️ **BALANCE UPDATED**\n\n💳 Your balance has been set to ${new_balance:,.2f}"
            elif action == "RESET":
                notification = f"ℹ️ **BALANCE RESET**\n\n💳 Your account balance has been reset to $0.00"
            
            await context.bot.send_message(
                chat_id=target_user_id,
                text=notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify user {target_user_id} about balance change: {e}")
    
    except Exception as e:
        logging.error(f"Error updating user balance: {e}")
        await update.callback_query.message.edit_text(
            f"❌ **ERROR UPDATING BALANCE**\n\n{str(e)}\n\nPlease try again or contact technical support.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]])
        )
    
    # Clean up
    context.user_data.pop('balance_confirmation', None)

async def handle_broadcast_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast confirmation callback"""
    broadcast_message = context.user_data.get('broadcast_message')
    if not broadcast_message:
        await update.callback_query.message.edit_text("❌ Session expired. Please start over.")
        return
    
    # Get all users
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
    
    success_count = 0
    total_users = len(users)
    admin_id = update.callback_query.from_user.id
    
    # Update message to show progress
    await update.callback_query.message.edit_text(
        f"📢 **SENDING BROADCAST...**\n\n"
        f"📤 Sending to {total_users} users...\n"
        f"⏳ Please wait...",
        parse_mode='Markdown'
    )
    
    # Send broadcast message
    for user_tuple in users:
        try:
            await context.bot.send_message(
                chat_id=user_tuple[0],
                text=f"📢 **ANNOUNCEMENT**\n\n{broadcast_message}",
                parse_mode='Markdown'
            )
            success_count += 1
            await asyncio.sleep(0.05)  # Rate limiting to avoid hitting limits
        except Exception as e:
            logging.error(f"Failed to send broadcast to {user_tuple[0]}: {e}")
    
    # Log the broadcast
    log_admin_action(
        admin_id=admin_id,
        action_type="broadcast_message",
        notes=f"Broadcast sent to {success_count}/{total_users} users"
    )
    
    # Send completion message
    await update.callback_query.message.edit_text(
        f"✅ **BROADCAST COMPLETE!**\n\n"
        f"📊 **Results:**\n"
        f"• Total Users: {total_users}\n"
        f"• Successfully Sent: {success_count}\n"
        f"• Failed: {total_users - success_count}\n"
        f"• Success Rate: {(success_count/total_users)*100:.1f}%\n\n"
        f"✅ Broadcast has been logged in admin records.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Send Another", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
        ]),
        parse_mode='Markdown'
    )
    
    # Clean up
    context.user_data.pop('broadcast_message', None)

# Update the main handle_admin_callback function to include new callbacks
def update_admin_callback_handler():
    """Add these cases to your existing handle_admin_callback function"""
    # Add these cases to the existing function:
    
    # elif data == "admin_confirm_balance_change":
    #     await handle_balance_confirmation_callback(update, context)
    # elif data == "admin_confirm_broadcast":
    #     await handle_broadcast_confirmation_callback(update, context)
    
    pass

# Add this to the bottom of your message_handlers.py file
async def handle_stock_sale(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
    """Process a stock sale request, update DB, notify admin, and request approval/rejection."""
    user = update.effective_user
    # Fetch stock info from DB
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT stock_ticker, shares, purchase_price FROM stock_investments WHERE id = ?', (stock_id,))
        stock = cursor.fetchone()
    if not stock:
        await update.callback_query.message.edit_text("❌ Stock not found or invalid sale request.")
        return
    ticker, shares, purchase_price = stock
    # Mark sale request in DB (add a pending sale entry)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO stock_sales (user_id, stock_id, stock_ticker, shares, purchase_price, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user.id, stock_id, ticker, shares, purchase_price, 'pending'))
        conn.commit()
    # Notify user
    await update.callback_query.message.edit_text(
        f"✅ Stock sale request submitted for {shares} shares of {ticker.upper()} at ${purchase_price:,.2f} per share.\n\nYour request is pending admin approval.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
    )
    # Notify admins
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🚨 **NEW STOCK SALE REQUEST** 🚨\n\n"
                    f"👤 User: @{user.username or user.id}\n"
                    f"Stock: {ticker.upper()}\nShares: {shares}\nPurchase Price: ${purchase_price:,.2f}\n"
                    f"Sale ID: {stock_id}\n\n"
                    f"Approve or reject this sale in the admin panel."
                ),
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id} about stock sale: {e}")
async def enhanced_handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced text message handler that includes admin functionality"""
    user = update.effective_user
    message_text = update.message.text.strip()
    
    # Check if admin system handles this message
    if user.id in ADMIN_USER_IDS:
        from handlers.admin_handlers import handle_admin_text_messages
        if await handle_admin_text_messages(update, context, message_text):
            return  # Message was handled by admin system
    
    # Continue with existing message handling logic...
    # (Your existing handle_text_message code here)
    
    # Registration flow
    if context.user_data.get('registration_step') == 'name':
        await handle_registration_name(update, context, message_text)
        return
    
    elif context.user_data.get('registration_step') == 'email':
        await handle_registration_email(update, context, message_text)
        return
            