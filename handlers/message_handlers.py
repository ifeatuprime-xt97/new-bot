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
    

# Add these functions to your handlers/message_handlers.py

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced text message handler with complete admin support"""
    user = update.effective_user
    message_text = update.message.text.strip()
    
    # Check if admin system should handle this message FIRST
    if user.id in ADMIN_USER_IDS:
        # Handle admin balance editing
        if context.user_data.get('awaiting_balance_user_id'):
            await handle_balance_user_id_input(update, context, message_text)
            return
        elif context.user_data.get('awaiting_balance_amount'):
            await handle_balance_amount_input(update, context, message_text)
            return
        
        # Handle admin user editing
        elif context.user_data.get('awaiting_user_edit'):
            await handle_user_edit_input(update, context, message_text)
            return
        elif context.user_data.get('awaiting_investment_edit'):
            await handle_investment_edit_input(update, context, message_text)
            return
        elif context.user_data.get('awaiting_stock_edit'):
            await handle_stock_edit_input(update, context, message_text)
            return
        
        # Handle admin search and broadcast
        elif context.user_data.get('awaiting_user_search'):
            await handle_user_search_input(update, context, message_text)
            return
        elif context.user_data.get('awaiting_broadcast_message'):
            await handle_broadcast_message_admin(update, context, message_text)
            return
    
    # Continue with regular user message handling...
    
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

# Admin user editing handlers

async def handle_user_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE, input_text: str):
    """Handle user profile edit input from admin"""
    edit_field = context.user_data.get('edit_field')
    user_id = context.user_data.get('edit_user_id')
    
    if not edit_field or not user_id:
        await update.message.reply_text("❌ Edit session expired. Please start over.")
        context.user_data.pop('awaiting_user_edit', None)
        return
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if edit_field == 'name':
                if len(input_text) < 2:
                    await update.message.reply_text("❌ Name must be at least 2 characters long.")
                    return
                
                cursor.execute('UPDATE users SET full_name = ? WHERE user_id = ?', (input_text, user_id))
                conn.commit()
                
                success_msg = f"✅ **NAME UPDATED**\n\nUser's full name changed to: **{input_text}**"
                
            elif edit_field == 'email':
                if '@' not in input_text or '.' not in input_text:
                    await update.message.reply_text("❌ Please enter a valid email address.")
                    return
                
                cursor.execute('UPDATE users SET email = ? WHERE user_id = ?', (input_text, user_id))
                conn.commit()
                
                success_msg = f"✅ **EMAIL UPDATED**\n\nUser's email changed to: **{input_text}**"
                
            elif edit_field == 'regdate':
                # Validate date format
                try:
                    from datetime import datetime
                    parsed_date = datetime.strptime(input_text, '%Y-%m-%d')
                    formatted_date = parsed_date.isoformat()
                except ValueError:
                    await update.message.reply_text(
                        "❌ Invalid date format. Please use YYYY-MM-DD format.\n\n"
                        "Example: 2024-01-15"
                    )
                    return
                
                cursor.execute('UPDATE users SET registration_date = ? WHERE user_id = ?', (formatted_date, user_id))
                conn.commit()
                
                success_msg = f"✅ **REGISTRATION DATE UPDATED**\n\nUser's registration date changed to: **{input_text}**"
        
        # Log the action
        log_admin_action(
            admin_id=update.effective_user.id,
            action_type=f"profile_edit_{edit_field}",
            target_user_id=user_id,
            notes=f"Changed {edit_field} to: {input_text}"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit More", callback_data=f"admin_edit_profile_{user_id}")],
            [InlineKeyboardButton("👤 View Profile", callback_data=f"admin_user_profile_{user_id}")],
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(success_msg, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logging.error(f"Error updating user {edit_field}: {e}")
        await update.message.reply_text(f"❌ Error updating {edit_field}: {str(e)}")
    
    # Clean up
    context.user_data.pop('awaiting_user_edit', None)
    context.user_data.pop('edit_field', None)
    context.user_data.pop('edit_user_id', None)

async def handle_investment_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE, input_text: str):

    """Handle investment editing input"""
    edit_data = context.user_data.get('investment_edit_data')
    if not edit_data:
        await update.message.reply_text("❌ Edit session expired.")
        return
    field = edit_data.get('field')
    investment_id = edit_data.get('investment_id')

    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            if field == 'amount':
                amount = float(input_text.replace(',', ''))
                cursor.execute('UPDATE investments SET amount = ? WHERE id = ?', (amount, investment_id))
                success_msg = f"✅ Investment amount updated to ${amount:,.2f}"
            elif field == 'status':
                if input_text.lower() not in ['confirmed', 'pending', 'rejected']:
                    await update.message.reply_text("❌ Status must be: confirmed, pending, or rejected")
                    return
                cursor.execute('UPDATE investments SET status = ? WHERE id = ?', (input_text.lower(), investment_id))
                success_msg = f"✅ Investment status updated to {input_text.title()}"
            elif field == 'plan':
                if input_text.upper() not in ['CORE', 'GROWTH', 'ALPHA']:
                    await update.message.reply_text("❌ Plan must be: CORE, GROWTH, or ALPHA")
                    return
                cursor.execute('UPDATE investments SET plan = ? WHERE id = ?', (input_text.upper(), investment_id))
                success_msg = f"✅ Investment plan updated to {input_text.upper()}"
            conn.commit()
        # Log the action
        log_admin_action(
            admin_id=update.effective_user.id,
            action_type=f"investment_edit_{field}",
            target_user_id=edit_data.get('user_id'),
            notes=f"Investment {investment_id} {field} changed to: {input_text}"
        )
        user_id = edit_data.get('user_id')
        keyboard = [
            [InlineKeyboardButton("💰 Edit More Investments", callback_data=f"admin_edit_investments_{user_id}")],
            [InlineKeyboardButton("👤 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(success_msg, reply_markup=reply_markup)
    except ValueError:
        await update.message.reply_text("❌ Invalid input format. Please try again.")
    except Exception as e:
        logging.error(f"Error updating investment: {e}")
        await update.message.reply_text(f"❌ Error updating investment: {str(e)}")

    # Clean up
    context.user_data.pop('awaiting_investment_edit', None)
    context.user_data.pop('investment_edit_data', None)

async def handle_stock_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE, input_text: str):
    """Handle stock editing input"""
    edit_data = context.user_data.get('stock_edit_data')
    
    if not edit_data:
        await update.message.reply_text("❌ Edit session expired.")
        return
    
    field = edit_data.get('field')
    stock_id = edit_data.get('stock_id')
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if field == 'amount':
                amount = float(input_text.replace(',', ''))
                cursor.execute('UPDATE stock_investments SET amount_invested_usd = ? WHERE id = ?', (amount, stock_id))
                success_msg = f"✅ Stock investment amount updated to ${amount:,.2f}"

            elif field == 'price':
                price = float(input_text.replace(',', ''))
                cursor.execute('UPDATE stock_investments SET purchase_price = ? WHERE id = ?', (price, stock_id))
                success_msg = f"✅ Stock purchase price updated to ${price:,.2f}"
                
            elif field == 'status':
                if input_text.lower() not in ['confirmed', 'pending', 'rejected']:
                    await update.message.reply_text("❌ Status must be: confirmed, pending, or rejected")
                    return
                cursor.execute('UPDATE stock_investments SET status = ? WHERE id = ?', (input_text.lower(), stock_id))
                success_msg = f"✅ Stock status updated to {input_text.title()}"
            
            conn.commit()
        
        # Log the action
        log_admin_action(
            admin_id=update.effective_user.id,
            action_type=f"stock_edit_{field}",
            target_user_id=edit_data.get('user_id'),
            notes=f"Stock {stock_id} {field} changed to: {input_text}"
        )
        
        user_id = edit_data.get('user_id')
        keyboard = [
            [InlineKeyboardButton("📈 Edit More Stocks", callback_data=f"admin_edit_stocks_{user_id}")],
            [InlineKeyboardButton("👤 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(success_msg, reply_markup=reply_markup)
        
    except ValueError:
        await update.message.reply_text("❌ Invalid input format. Please try again.")
    except Exception as e:
        logging.error(f"Error updating stock: {e}")
        await update.message.reply_text(f"❌ Error updating stock: {str(e)}")
    
    # Clean up
    context.user_data.pop('awaiting_stock_edit', None)
    context.user_data.pop('stock_edit_data', None)
    

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
        # Clean the input - remove any extra characters
        cleaned_input = user_id_str.strip().replace('@', '').replace('#', '')
        
        # Try to parse as integer
        user_id = int(cleaned_input)
        
        # Debug logging
        logging.info(f"Admin balance edit: searching for user ID {user_id}")
        
        # Verify user exists
        user_data = db.get_user(user_id)
        
        if not user_data:
            # Get total user count for debugging
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM users')
                total_users = cursor.fetchone()[0]
                
                # Show some example user IDs
                cursor.execute('SELECT user_id FROM users ORDER BY registration_date DESC LIMIT 3')
                example_ids = [str(row[0]) for row in cursor.fetchall()]
            
            keyboard = [
                [InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
                [InlineKeyboardButton("👥 View All Users", callback_data="admin_user_list")],
                [InlineKeyboardButton("🔙 Balance Menu", callback_data="admin_edit_balance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"❌ **USER NOT FOUND**\n\n"
                f"User ID '{user_id}' does not exist in the database.\n\n"
                f"**Database Info:**\n"
                f"• Total users: {total_users}\n"
                f"• Recent user IDs: {', '.join(example_ids)}\n\n"
                f"**What to try:**\n"
                f"• Use 'Search User' to find by username\n"
                f"• Use 'View All Users' to browse\n"
                f"• Double-check the user ID number\n"
                f"• Make sure user has used /start",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            context.user_data.pop('awaiting_balance_user_id', None)
            return
        
        # User found - store data for next step
        context.user_data['balance_target_user'] = user_data
        context.user_data.pop('awaiting_balance_user_id', None)
        
        action = context.user_data.get('balance_action')
        current_balance = user_data[8]  # current_balance field
        username = user_data[1]
        full_name = user_data[3]
        
        logging.info(f"User found: {username} (ID: {user_id}) - Balance: ${current_balance}")
        
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
                f"✅ **USER FOUND!**\n\n"
                f"💳 **{action_text[action].upper()} USER BALANCE**\n\n"
                f"**User:** @{username} ({full_name or 'N/A'})\n"
                f"**User ID:** {user_data[0]}\n"
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
            f"❌ **INVALID FORMAT**\n\n"
            f"'{user_id_str}' is not a valid user ID.\n\n"
            f"**Please enter:**\n"
            f"• Numbers only (e.g., 123456789)\n"
            f"• No letters, symbols, or spaces\n\n"
            f"**Example:** 652353552"
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


# Add this to the bottom of your message_handlers.py file
async def handle_stock_sale(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
    """Start stock sale request, insert into DB, and ask for wallet details."""
    user = update.effective_user

    # Fetch stock info
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT stock_ticker, amount_invested_usd, purchase_price
            FROM stock_investments
            WHERE id = ? AND user_id = ? AND status = 'confirmed'
        ''', (stock_id, user.id))
        stock = cursor.fetchone()

    if not stock:
        await update.callback_query.message.edit_text("❌ Stock not found or invalid sale request.")
        return

    ticker, invested_amount, purchase_price = stock
    shares = invested_amount / purchase_price if purchase_price > 0 else 0
    total_value = shares * purchase_price  # You can also use current market price here

    # Create sale record (awaiting wallet)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO stock_sales (
                user_id, stock_investment_id, shares_sold, sale_price, total_value, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (user.id, stock_id, shares, purchase_price, total_value, 'awaiting_wallet'))
        sale_id = cursor.lastrowid
        conn.commit()

    # Save sale_id in user context so we can update wallet later
    context.user_data['pending_sale_id'] = sale_id

    # Ask user for wallet address
    await update.callback_query.message.edit_text(
        f"📈 You are selling **{shares:.2f} shares of {ticker.upper()}** "
        f"at ${purchase_price:,.2f}/share (Total: ${total_value:,.2f}).\n\n"
        "💰 Please enter your **USDT (TRC20) wallet address** where payment will be sent."
    )


async def handle_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture wallet address for pending stock sale."""
    user = update.effective_user
    wallet_address = update.message.text
    sale_id = context.user_data.get('pending_sale_id')

    if not sale_id:
        await update.message.reply_text("❌ No pending sale request found.")
        return

    # Update sale with wallet address
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE stock_sales
            SET wallet_address = ?, status = 'pending'
            WHERE id = ? AND user_id = ?
        ''', (wallet_address, sale_id, user.id))
        conn.commit()

    await update.message.reply_text(
        f"✅ Wallet address saved.\n\n"
        f"Your stock sale request is now pending admin approval."
    )

    # Notify admins
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🚨 **NEW STOCK SALE REQUEST** 🚨\n\n"
                    f"👤 User: @{user.username or user.id}\n"
                    f"Wallet: `{wallet_address}`\n"
                    f"Sale ID: {sale_id}\n"
                    f"Status: pending\n\n"
                    f"Approve or reject this sale in the admin panel."
                ),
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Failed to notify admin {admin_id} about stock sale: {e}")

# Add this handler to your message processing logic
async def handle_manual_investment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the admin's input during the manual investment creation process."""
    if 'manual_investment' not in context.user_data:
        return

    data = context.user_data['manual_investment']
    user_id = data['user_id']
    step = data['step']
    text = update.message.text
    
    try:
        if step == 'amount':
            amount = float(text)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            data['amount'] = amount
            data['step'] = 'crypto_type'
            
            await update.message.reply_text(
                f"✅ Amount set to ${amount:,.2f}\n\n"
                f"**Step 2 of 3: Crypto Type**\n"
                f"Enter the cryptocurrency symbol (e.g., BTC, ETH, USDT):"
            )

        elif step == 'crypto_type':
            crypto = text.strip().upper()
            if not crypto or len(crypto) > 10:
                raise ValueError("Invalid crypto symbol.")
            data['crypto_type'] = crypto
            data['step'] = 'plan'
            
            await update.message.reply_text(
                f"✅ Crypto set to {crypto}\n\n"
                f"**Step 3 of 3: Plan**\n"
                f"Enter the investment plan (e.g., CORE, GROWTH, ALPHA):"
            )

        elif step == 'plan':
            plan = text.strip().upper()
            if not plan or len(plan) > 20:
                raise ValueError("Invalid plan name.")
            data['plan'] = plan
            
            # Final confirmation step
            keyboard = [[
                InlineKeyboardButton("✅ Confirm & Add", callback_data="admin_confirm_manual_investment"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"admin_user_profile_{user_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"**CONFIRM INVESTMENT**\n\n"
                f"**User:** @{data['username']} (ID: {user_id})\n"
                f"**Amount:** ${data['amount']:,.2f}\n"
                f"**Crypto:** {data['crypto_type']}\n"
                f"**Plan:** {data['plan']}\n\n"
                f"Please confirm to add this investment.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            context.user_data.pop('awaiting_manual_investment', None)

    except (ValueError, TypeError) as e:
        await update.message.reply_text(f"❌ Invalid input: {e}\nPlease try again.")

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main text message handler - routes messages based on user state"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # ADMIN TEXT INPUT ROUTING
    if user_id in ADMIN_USER_IDS:
        
        # Check if admin is adding manual stock (waiting for shares input)
        #if context.user_data.get('awaiting_manual_stock'):
         #   await handle_manual_stock_input(update, context)
          #  return
        
        # Check if admin is editing stock details
        if context.user_data.get('awaiting_stock_edit'):
            await handle_stock_edit_input(update, context)
            return
        
        # Check if admin is searching for user
        if context.user_data.get('awaiting_user_search'):
            await handle_user_search_input(update, context)
            return
        
        # Check if admin is editing user profile fields
        if context.user_data.get('awaiting_user_edit'):
            await handle_user_edit_input(update, context)
            return
        
        # Check if admin is entering user ID for balance edit
        if context.user_data.get('awaiting_balance_user_id'):
            await handle_balance_user_id_input(update, context, message_text)
            return
        
        # Check if admin is entering balance amount
        if context.user_data.get('awaiting_balance_amount'):
            await handle_balance_amount_input(update, context)
            return
        
        # Check if admin is adding manual investment
        if context.user_data.get('awaiting_manual_investment'):
            await handle_manual_investment_input(update, context)
            return
        
        # Check if admin is entering broadcast message
        if context.user_data.get('awaiting_broadcast_message'):
            await handle_broadcast_input(update, context)
            return
        
        # Check if admin is editing investment details
        if context.user_data.get('awaiting_investment_edit'):
            await handle_investment_edit_input(update, context)
            return
    
    # REGULAR USER MESSAGE HANDLING
    # Add your existing user message handling logic here
    # For example:
    if message_text.lower() in ['hi', 'hello', 'hey']:
        await update.message.reply_text(
            "Hello! Use /start to see the main menu or /help for assistance."
        )
        return
    
    # Default response for unrecognized text
    await update.message.reply_text(
        "I didn't understand that. Use /start to see available options."
    )


# ADMIN INPUT HANDLERS

async def handle_user_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user search input from admin"""
    search_term = update.message.text.strip()
    
    try:
        # Try searching by user ID first
        if search_term.isdigit():
            user_id = int(search_term)
            user_data = db.get_user(user_id)
            if user_data:
                from .admin_handlers import show_user_profile
                await show_user_profile(update, context, user_id)
                context.user_data.pop('awaiting_user_search', None)
                return
        
        # Search by username, email, or name
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, full_name, email 
                FROM users 
                WHERE username LIKE ? OR email LIKE ? OR full_name LIKE ?
                ORDER BY registration_date DESC
                LIMIT 10
            ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
            results = cursor.fetchall()
        
        if not results:
            await update.message.reply_text(
                f"No users found matching '{search_term}'\n\nTry:\n"
                "• User ID (numbers only)\n"
                "• Username (with or without @)\n"
                "• Email address\n"
                "• Full name"
            )
            return
            
        if len(results) == 1:
            # Single result - show profile directly
            from .admin_handlers import show_user_profile
            await show_user_profile(update, context, results[0][0])
            context.user_data.pop('awaiting_user_search', None)
            return
        
        # Multiple results - show selection menu
        text = f"Found {len(results)} users matching '{search_term}':\n\n"
        keyboard = []
        
        for user_id, username, full_name, email in results:
            display_name = f"@{username}" if username else full_name if full_name else f"ID: {user_id}"
            text += f"• {display_name}\n"
            keyboard.append([InlineKeyboardButton(
                display_name, 
                callback_data=f"admin_user_profile_{user_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔍 New Search", callback_data="admin_search_user")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        context.user_data.pop('awaiting_user_search', None)
        
    except Exception as e:
        logging.error(f"User search error: {e}")
        await update.message.reply_text(f"Search error: {str(e)}")


async def handle_user_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user profile field editing input"""
    user_id = context.user_data.get('edit_user_id')
    field = context.user_data.get('edit_field')
    new_value = update.message.text.strip()
    
    if not user_id or not field:
        await update.message.reply_text("Error: Missing edit context. Please start over.")
        return
        
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if field == 'name':
                cursor.execute('UPDATE users SET full_name = ? WHERE user_id = ?', (new_value, user_id))
                success_msg = f"Name updated to: {new_value}"
                
            elif field == 'email':
                # Basic email validation
                if '@' not in new_value or '.' not in new_value:
                    await update.message.reply_text("Invalid email format. Please try again:")
                    return
                cursor.execute('UPDATE users SET email = ? WHERE user_id = ?', (new_value, user_id))
                success_msg = f"Email updated to: {new_value}"
                
            elif field == 'regdate':
                from datetime import datetime
                try:
                    parsed_date = datetime.strptime(new_value, '%Y-%m-%d')
                    cursor.execute('UPDATE users SET registration_date = ? WHERE user_id = ?', 
                                 (parsed_date.isoformat(), user_id))
                    success_msg = f"Registration date updated to: {new_value}"
                except ValueError:
                    await update.message.reply_text("Invalid date format. Use YYYY-MM-DD (e.g., 2024-01-15)")
                    return
                    
            elif field == 'profit':
                profit = float(new_value.replace(',', '').replace('$', ''))
                cursor.execute('UPDATE users SET profit_earned = ? WHERE user_id = ?', (profit, user_id))
                success_msg = f"Profit updated to: ${profit:,.2f}"
                
            else:
                await update.message.reply_text("Unknown field to edit.")
                return
            
            conn.commit()
        
        # Log the action
        log_admin_action(
            admin_id=update.effective_user.id,
            action_type=f"user_{field}_edit",
            target_user_id=user_id,
            notes=f"{field} changed to: {new_value}"
        )
        
        keyboard = [
            [InlineKeyboardButton("✏️ Edit More", callback_data=f"admin_edit_profile_{user_id}")],
            [InlineKeyboardButton("👤 View Profile", callback_data=f"admin_user_profile_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **UPDATE SUCCESSFUL**\n\n{success_msg}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("Invalid value format. Please try again:")
        return
    except Exception as e:
        logging.error(f"User edit error: {e}")
        await update.message.reply_text(f"Error updating {field}: {str(e)}")
    finally:
        # Clean up context
        context.user_data.pop('awaiting_user_edit', None)
        context.user_data.pop('edit_user_id', None)
        context.user_data.pop('edit_field', None)


async def handle_balance_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle balance amount input"""
    try:
        amount_text = update.message.text.strip().replace(',', '').replace('$', '')
        amount = float(amount_text)
        
        if amount <= 0:
            await update.message.reply_text(
                "Amount must be greater than 0.\nPlease enter a valid amount:"
            )
            return
            
        action = context.user_data.get('balance_action')
        from .admin_handlers import confirm_balance_change
        await confirm_balance_change(update, context, amount, action.upper())
        context.user_data.pop('awaiting_balance_amount', None)
        
    except (ValueError, TypeError):
        await update.message.reply_text(
            "Invalid amount format. Please enter a valid number:"
        )


async def handle_manual_investment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle manual crypto investment input"""
    investment_data = context.user_data.get('manual_investment')
    if not investment_data:
        await update.message.reply_text("Investment data not found. Please start over.")
        return
        
    step = investment_data.get('step')
    text = update.message.text.strip()
    
    try:
        if step == 'amount':
            amount = float(text.replace(',', '').replace('$', ''))
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            investment_data['amount'] = amount
            investment_data['step'] = 'crypto_type'
            
            keyboard = [
                [InlineKeyboardButton("Bitcoin (BTC)", callback_data=f"admin_inv_crypto_btc_{investment_data['user_id']}")],
                [InlineKeyboardButton("Ethereum (ETH)", callback_data=f"admin_inv_crypto_eth_{investment_data['user_id']}")],
                [InlineKeyboardButton("USDT", callback_data=f"admin_inv_crypto_usdt_{investment_data['user_id']}")],
                [InlineKeyboardButton("Cancel", callback_data=f"admin_user_profile_{investment_data['user_id']}")]
            ]
            
            await update.message.reply_text(
                f"✅ Amount set to ${amount:,.2f}\n\n"
                f"**Step 2 of 3:** Choose cryptocurrency type:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            context.user_data.pop('awaiting_manual_investment', None)
            
    except (ValueError, TypeError) as e:
        await update.message.reply_text(f"❌ Invalid input: {e}\nPlease try again.")


async def handle_broadcast_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message input"""
    message = update.message.text.strip()
    
    if len(message) > 2000:
        await update.message.reply_text(
            f"Message too long ({len(message)} characters, max 2000).\n"
            "Please shorten your message:"
        )
        return
        
    context.user_data['broadcast_message'] = message
    context.user_data.pop('awaiting_broadcast_message', None)
    
    keyboard = [
        [InlineKeyboardButton("📢 Send to All Users", callback_data="admin_confirm_broadcast")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]
    ]
    
    await update.message.reply_text(
        f"**BROADCAST MESSAGE PREVIEW**\n\n"
        f"{message}\n\n"
        f"**Character count:** {len(message)}/2000\n\n"
        f"Confirm to send this message to all users:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_investment_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle investment editing input"""
    investment_data = context.user_data.get('investment_edit_data')
    if not investment_data:
        return
        
    field = investment_data.get('field')
    investment_id = investment_data.get('investment_id')
    user_id = investment_data.get('user_id')
    new_value = update.message.text.strip()
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            if field == 'amount':
                amount = float(new_value.replace(',', '').replace('$', ''))
                if amount <= 0:
                    raise ValueError("Amount must be positive")
                cursor.execute('UPDATE investments SET amount = ? WHERE id = ?', (amount, investment_id))
                success_msg = f"Amount updated to ${amount:,.2f}"
                
            elif field == 'status':
                if new_value.lower() not in ['pending', 'confirmed', 'rejected']:
                    raise ValueError("Status must be: pending, confirmed, or rejected")
                cursor.execute('UPDATE investments SET status = ? WHERE id = ?', (new_value.lower(), investment_id))
                success_msg = f"Status updated to {new_value.lower()}"
                
            elif field == 'plan':
                cursor.execute('UPDATE investments SET plan = ? WHERE id = ?', (new_value, investment_id))
                success_msg = f"Plan updated to {new_value}"
            
            conn.commit()
        
        # Log the action
        log_admin_action(
            admin_id=update.effective_user.id,
            action_type=f"investment_{field}_edit",
            target_user_id=user_id,
            notes=f"Investment {investment_id} - {field} changed to: {new_value}"
        )
        
        await update.message.reply_text(
            f"✅ **{field.upper()} UPDATED**\n\n{success_msg}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Edit More", callback_data=f"admin_edit_inv_{investment_id}")],
                [InlineKeyboardButton("📊 View Investments", callback_data=f"admin_edit_investments_{user_id}")]
            ]),
            parse_mode='Markdown'
        )
        
    except ValueError as e:
        await update.message.reply_text(f"Invalid input: {e}\nPlease try again:")
        return
    except Exception as e:
        logging.error(f"Investment edit error: {e}")
        await update.message.reply_text(f"Error updating {field}: {str(e)}")
    finally:
        context.user_data.pop('awaiting_investment_edit', None)
        context.user_data.pop('investment_edit_data', None)
