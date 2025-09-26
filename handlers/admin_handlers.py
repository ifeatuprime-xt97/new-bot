"""
Admin command handlers - Complete functionality with full user management
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import random
from config import ALL_STOCKS
from config import ADMIN_USER_IDS
from database import db
from .utils import log_admin_action

from .message_handlers import (
    confirm_balance_change,
    handle_balance_confirmation_callback,
    handle_broadcast_confirmation_callback,
)


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin panel command"""
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("Access denied. Admin permissions required.")
        return
    
    keyboard = [
        [InlineKeyboardButton("💰 Pending Investments", callback_data="admin_investments"),
         InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("📈 Pending Stock Investments", callback_data="admin_stock_investments"),
         InlineKeyboardButton("📉 Pending Stock Sales", callback_data="admin_stock_sales")],
        [InlineKeyboardButton("👥 User Management", callback_data="admin_user_management"),
         InlineKeyboardButton("📊 Bot Statistics", callback_data="admin_user_stats")],
        [InlineKeyboardButton("💳 Edit User Balance", callback_data="admin_edit_balance"),
         InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"),
         InlineKeyboardButton("📋 Admin Logs", callback_data="admin_logs")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    stats = db.get_user_stats()
    text = f"""
**ADMIN CONTROL PANEL**

**Quick Stats:**
• Total Users: {stats.get('total_users', 0)}
• Active Investors: {stats.get('active_investors', 0)}
• Pending Investments: {stats.get('pending_investments', 0)}
• Pending Withdrawals: {stats.get('pending_withdrawals', 0)}

Select an option below:
    """
    
    if update.message:
        await update.message.reply_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def get_realtime_price(ticker):
    raise NotImplementedError

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Master callback handler for all admin functions"""
    user = update.callback_query.from_user
    if user.id not in ADMIN_USER_IDS:
        await update.callback_query.message.edit_text("Access denied.")
        return
    
    try:
        # Main admin functions
        if data == "admin_panel":
            await admin_command(update, context)
        elif data == "admin_investments":
            await show_pending_investments(update, context)
        elif data == "admin_withdrawals":
            await show_pending_withdrawals(update, context)
        elif data == "admin_stock_investments":
            await show_pending_stock_investments(update, context)
        elif data == "admin_stock_sales":
            await show_pending_stock_sales(update, context)
        elif data == "admin_user_management":
            await show_user_management(update, context)
        elif data == "admin_user_stats":
            await show_user_stats(update, context)
        elif data == "admin_edit_balance":
            await show_balance_edit_menu(update, context)
        elif data == "admin_search_user":
            await setup_user_search(update, context)
        elif data == "admin_broadcast":
            await setup_broadcast_message(update, context)
        elif data == "admin_logs":
            await show_admin_logs(update, context)
        
        # User management
        elif data == "admin_user_list":
            await show_user_list(update, context, 0)
        elif data.startswith("admin_user_list_"):
            page = int(data.split("_")[-1])
            await show_user_list(update, context, page)
        elif data.startswith("admin_user_profile_"):
            user_id = int(data.split("_")[-1])
            await show_user_profile(update, context, user_id)
        
        # Profile editing
        elif data.startswith("admin_edit_profile_"):
            user_id = int(data.split("_")[-1])
            await show_user_edit_profile_menu(update, context, user_id)
        elif data.startswith("admin_edit_name_"):
            user_id = int(data.split("_")[-1])
            await setup_name_edit(update, context, user_id)
        elif data.startswith("admin_edit_email_"):
            user_id = int(data.split("_")[-1])
            await setup_email_edit(update, context, user_id)
        elif data.startswith("admin_edit_regdate_"):
            user_id = int(data.split("_")[-1])
            await setup_regdate_edit(update, context, user_id)
        elif data.startswith("admin_edit_plan_"):
            user_id = int(data.split("_")[-1])
            await show_plan_edit_menu(update, context, user_id)
        elif data.startswith("admin_set_plan_"):
            parts = data.split("_")
            user_id = int(parts[3])
            plan = parts[4] if parts[4] != 'NONE' else None
            await set_user_plan(update, context, user_id, plan)
        elif data.startswith("admin_reset_refcode_"):
            user_id = int(data.split("_")[-1])
            await reset_referral_code(update, context, user_id)
        elif data.startswith("admin_edit_profits_"):
            user_id = int(data.split("_")[-1])
            await setup_profit_edit(update, context, user_id)
        
        # Investment and stock management
        elif data.startswith("admin_edit_investments_"):
            user_id = int(data.split("_")[-1])
            await show_user_investments_edit(update, context, user_id)
        elif data.startswith("admin_edit_stocks_"):
            user_id = int(data.split("_")[-1])
            await show_user_stocks_edit(update, context, user_id)
        elif data.startswith("admin_user_history_"):
            user_id = int(data.split("_")[-1])
            await show_user_transaction_history_admin(update, context, user_id)
        elif data.startswith("admin_add_investment_"):
            user_id = int(data.split("_")[-1])
            await setup_add_investment(update, context, user_id)
        elif data.startswith("admin_add_stock_"):
            user_id = int(data.split("_")[-1])
            await setup_add_stock(update, context, user_id)
        elif data.startswith("admin_edit_inv_"):
            inv_id = int(data.split("_")[-1])
            await show_investment_edit_menu(update, context, inv_id)
        elif data.startswith("admin_edit_stock_"):
            stock_id = int(data.split("_")[-1])
            await show_stock_edit_menu(update, context, stock_id)
        elif data.startswith("admin_delete_user_"):
            user_id = int(data.split("_")[-1])
            await confirm_user_deletion(update, context, user_id)
        elif data.startswith("admin_confirm_delete_"):
            user_id = int(data.split("_")[-1])
            await execute_user_deletion(update, context, user_id)
        elif data.startswith("admin_clear_history_"):
            user_id = int(data.split("_")[-1])
            await clear_user_history(update, context, user_id)
        
        # Balance management
        elif data.startswith("admin_balance_"):
            await handle_balance_edit_callback(update, context, data)
        elif data == "admin_confirm_balance_change":
            await handle_balance_confirmation_callback(update, context)
        elif data.startswith("admin_edit_user_balance_"):
            user_id = int(data.split("_")[-1])
            await setup_user_balance_edit(update, context, user_id)
        elif data.startswith("admin_add_stock_ticker_"):
            parts = data.split("_")
            ticker = parts[4]
            user_id = int(parts[5])

            # Store state
            context.user_data['manual_stock'] = {
                'user_id': user_id,
                'ticker': ticker,
                'step': 'amount'
            }

            keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data=f"admin_user_profile_{user_id}")]]
            await update.callback_query.message.edit_text(
                f"💰 **ADD STOCK**\n\n"
                f"✅ Selected: {ticker}\n\n"
                f"Step 2 of 3: Enter the amount (USD) to invest:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )


        # Manual investment addition
        elif data == "admin_confirm_manual_investment":
            investment_data = context.user_data.get('manual_investment')
            if not investment_data:
                await update.callback_query.message.edit_text("❌ Error: Investment data not found. Please start over.")
                return

            # Use the existing db.confirm_investment logic or a new dedicated function
            success, message = db.add_manual_investment(
                admin_id=update.callback_query.from_user.id,
                user_id=investment_data['user_id'],
                amount=investment_data['amount'],
                crypto_type=investment_data['crypto_type'],
                plan=investment_data['plan']
            )

            if success:
                await update.callback_query.message.edit_text(
                    f"✅ Investment of ${investment_data['amount']:,.2f} successfully added for user {investment_data['user_id']}.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 View Profile", callback_data=f"admin_user_profile_{investment_data['user_id']}")]]))
            else:
                await update.callback_query.message.edit_text(f"❌ Failed to add investment: {message}")
            
            context.user_data.pop('manual_investment', None)

        elif data.startswith("admin_add_stock_page_"):
            parts = data.split("_")
            # ["admin", "add", "stock", "page", "<user_id>", "<page>"]
            user_id = int(parts[4])   # correct index for user_id
            page = int(parts[5])      # correct index for page
            await setup_add_stock(update, context, user_id, page)


        elif data.startswith("admin_add_stock_ticker_"):
            parts = data.split("_")
            # ["admin", "add", "stock", "ticker", "<ticker>", "<user_id>"]
            ticker = parts[4]
            user_id = int(parts[5])

            # ✅ fetch realtime price from your API helper
            try:
                price = await get_realtime_price(ticker)   # <-- you should have this function already
            except Exception as e:
                await update.callback_query.message.edit_text(
                    f"❌ Could not fetch price for {ticker}. Error: {e}"
                )
                return

            amount = 1  # default amount (or however you want to define it)

            # ✅ Save to DB
            db.add_stock(user_id, ticker, amount, price)

            # ✅ Confirmation message
            keyboard = [[InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]]
            await update.callback_query.message.edit_text(
                f"✅ Stock added successfully!\n\n"
                f"📊 Ticker: {ticker}\n"
                f"💵 Current Price: ${price:,.2f}\n"
                f"📈 Amount: {amount}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )


                # Add this elif block to your handle_admin_callback function
        elif data == "admin_confirm_manual_stock":
            stock_data = context.user_data.get('manual_stock')
            if not stock_data:
                await update.callback_query.message.edit_text("❌ Error: Stock data not found. Please start over.")
                return

            try:
                # This function should be created in your database.py file
                db.add_manual_stock(
                    admin_id=update.callback_query.from_user.id,
                    user_id=stock_data['user_id'],
                    ticker=stock_data['ticker'],
                    amount=stock_data['amount'],
                    price=stock_data['price']
                )
                await update.callback_query.message.edit_text(
                    f"✅ Stock investment in {stock_data['ticker']} successfully added for user {stock_data['user_id']}.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👤 View Profile", callback_data=f"admin_user_profile_{stock_data['user_id']}")]]))
                
            except Exception as e:
                await update.callback_query.message.edit_text(f"❌ Failed to add stock: {e}")
            
            context.user_data.pop('manual_stock', None)

        # Confirmations and rejections
        elif data.startswith("admin_confirm_"):
            await handle_admin_confirmation(update, context, data)
        elif data.startswith("admin_reject_"):
            await handle_admin_rejection(update, context, data)
        
        # Broadcasting
        elif data == "admin_confirm_broadcast":
            await handle_broadcast_confirmation_callback(update, context)
        
        else:
            await update.callback_query.message.edit_text(
                "Unknown admin action.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Admin Panel", callback_data="admin_panel")]])
            )

            
    
    except Exception as e:
        logging.error(f"Admin callback error for '{data}': {e}")
        await update.callback_query.message.edit_text(
            f"Error processing admin action: {str(e)}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Admin Panel", callback_data="admin_panel")]])
        )

async def setup_profit_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Setup profit earned editing for a user."""
    user_data = db.get_user(user_id)
    if not user_data:
        await update.callback_query.message.edit_text("❌ User not found.")
        return
        
    current_profit = user_data[9]  # profit_earned column
    
    context.user_data['edit_user_id'] = user_id
    context.user_data['edit_field'] = 'profit'
    context.user_data['awaiting_user_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_profile_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"💰 **EDIT USER PROFIT**\n\n"
        f"**Current Profit:** ${current_profit:,.2f}\n\n"
        f"Enter the new total profit amount for this user. This is a direct override.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_user_investments_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show a user's crypto investments for editing."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, amount, crypto_type, status FROM investments WHERE user_id = ? ORDER BY investment_date DESC', (user_id,))
        investments = cursor.fetchall()

    if not investments:
        keyboard = [[InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]]
        await update.callback_query.message.edit_text("This user has no crypto investments.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = "📝 **EDIT USER INVESTMENTS**\n\nSelect an investment to manage:\n\n"
    keyboard = []
    for inv_id, amount, crypto, status in investments:
        text += f"• ID {inv_id}: ${amount:,.2f} ({crypto}) - {status.title()}\n"
        keyboard.append([InlineKeyboardButton(f"Edit Investment #{inv_id}", callback_data=f"admin_edit_inv_{inv_id}")])

    keyboard.append([InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_stocks_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show a user's stock investments for editing."""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, amount_invested_usd, stock_ticker, status FROM stock_investments WHERE user_id = ? ORDER BY investment_date DESC', (user_id,))
        stocks = cursor.fetchall()

    if not stocks:
        keyboard = [[InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]]
        await update.callback_query.message.edit_text("This user has no stock investments.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = "📝 **EDIT USER STOCKS**\n\nSelect a stock to manage:\n\n"
    keyboard = []
    for stock_id, amount, ticker, status in stocks:
        text += f"• ID {stock_id}: ${amount:,.2f} ({ticker}) - {status.title()}\n"
        keyboard.append([InlineKeyboardButton(f"Edit Stock #{stock_id}", callback_data=f"admin_edit_stock_{stock_id}")])

    keyboard.append([InlineKeyboardButton("➕ Add Stock Investment", callback_data=f"admin_add_stock_{user_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_transaction_history_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Display a user's full transaction history for an admin."""
    # This is a simplified example. A full implementation would use UNION across multiple tables.
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 'Investment' as type, amount, status, investment_date as date 
            FROM investments WHERE user_id = ?
            UNION ALL
            SELECT 'Withdrawal' as type, amount, status, withdrawal_date as date 
            FROM withdrawals WHERE user_id = ?
            ORDER BY date DESC LIMIT 10
        ''', (user_id, user_id))
        history = cursor.fetchall()

    if not history:
        keyboard = [[InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]]
        await update.callback_query.message.edit_text("No transaction history found for this user.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    text = "📜 **USER TRANSACTION HISTORY**\n\n"
    for type, amount, status, date in history:
        text += f"**{type}** - ${amount:,.2f}\n"
        text += f"Status: {status.title()} | Date: {date[:10]}\n"
        text += "──────────\n"

    keyboard = [[InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def execute_user_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Permanently delete a user and all their data."""
    admin_id = update.callback_query.from_user.id
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # It's crucial to delete from all related tables
            cursor.execute('DELETE FROM investments WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM withdrawals WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM stock_investments WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM stock_sales WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM referrals WHERE referrer_id = ? OR referred_id = ?', (user_id, user_id))
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            conn.commit()

        log_admin_action(
            admin_id=admin_id,
            action_type="user_deletion",
            target_user_id=user_id,
            notes="User account and all associated data permanently deleted."
        )
        await update.callback_query.message.edit_text(
            f"✅ **USER DELETED**\n\nUser ID {user_id} has been permanently removed from the database.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 User Management", callback_data="admin_user_management")]])
        )
    except Exception as e:
        logging.error(f"Error deleting user {user_id}: {e}")
        await update.callback_query.message.edit_text(f"❌ An error occurred during deletion: {e}")

async def clear_user_history(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Clear all transaction history for a user."""
    admin_id = update.callback_query.from_user.id
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM investments WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM withdrawals WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM stock_investments WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM stock_sales WHERE user_id = ?', (user_id,))
            conn.commit()

        log_admin_action(
            admin_id=admin_id,
            action_type="history_clear",
            target_user_id=user_id,
            notes="User transaction history cleared."
        )
        await update.callback_query.message.edit_text(
            f"✅ **HISTORY CLEARED**\n\nAll transaction history for user {user_id} has been deleted.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]]))
    except Exception as e:
        logging.error(f"Error clearing history for user {user_id}: {e}")
        await update.callback_query.message.edit_text(f"❌ An error occurred while clearing history: {e}")

async def setup_user_balance_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Setup balance editing directly from a user's profile."""
    user_data = db.get_user(user_id)
    if not user_data:
        await update.callback_query.message.edit_text("❌ User not found.")
        return

    context.user_data['balance_target_user'] = user_data
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Balance", callback_data="admin_balance_direct_add")],
        [InlineKeyboardButton("➖ Subtract Balance", callback_data="admin_balance_direct_subtract")],
        [InlineKeyboardButton("🎯 Set Balance", callback_data="admin_balance_direct_set")],
        [InlineKeyboardButton("🔙 Back to Profile", callback_data=f"admin_user_profile_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.edit_text(
        f"💳 **EDIT BALANCE** for @{user_data[1]}\n\n"
        f"Current Balance: ${user_data[8]:,.2f}\n\n"
        "Choose an action:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )                         

async def setup_investment_status_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, inv_id: int):
    """Setup investment status editing"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, status FROM investments WHERE id = ?', (inv_id,))
        result = cursor.fetchone()
    
    if not result:
        await update.callback_query.message.edit_text("❌ Investment not found.")
        return
    
    user_id, current_status = result
    
    context.user_data['investment_edit_data'] = {
        'investment_id': inv_id,
        'user_id': user_id,
        'field': 'status'
    }
    context.user_data['awaiting_investment_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_inv_{inv_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"📊 **EDIT INVESTMENT STATUS**\n\n"
        f"**Current Status:** {current_status.title()}\n\n"
        f"Enter the new status:\n\n"
        f"**Possible values:** pending, confirmed, rejected\n\n"
        f"Type the new status below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def setup_investment_plan_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, inv_id: int):
    """Setup investment plan editing"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, plan FROM investments WHERE id = ?', (inv_id,))
        result = cursor.fetchone()
    
    if not result:
        await update.callback_query.message.edit_text("❌ Investment not found.")
        return
    
    user_id, current_plan = result
    
    context.user_data['investment_edit_data'] = {
        'investment_id': inv_id,
        'user_id': user_id,
        'field': 'plan'
    }
    context.user_data['awaiting_investment_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_inv_{inv_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"🎯 **EDIT INVESTMENT PLAN**\n\n"
        f"**Current Plan:** {current_plan or 'None'}\n\n"
        f"Enter the new plan name:\n\n"
        f"**Examples:**\n"
        f"• basic\n"
        f"• standard\n"
        f"• premium\n\n"
        f"Type the new plan below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def setup_stock_amount_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
    """Setup stock amount editing"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, amount_invested_usd FROM stock_investments WHERE id = ?', (stock_id,))
        result = cursor.fetchone()
    
    if not result:
        await update.callback_query.message.edit_text("❌ Stock investment not found.")
        return
    
    user_id, current_amount = result
    
    context.user_data['stock_edit_data'] = {
        'stock_id': stock_id,
        'user_id': user_id,
        'field': 'amount'
    }
    context.user_data['awaiting_stock_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_stock_{stock_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"💰 **EDIT STOCK AMOUNT**\n\n"
        f"**Current Amount:** ${current_amount:,.2f}\n\n"
        f"Enter the new amount invested:\n\n"
        f"**Examples:**\n"
        f"• 1000\n"
        f"• 5500.50\n"
        f"• 25000\n\n"
        f"Type the new amount below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def setup_stock_price_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
    """Setup stock price editing"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, purchase_price FROM stock_investments WHERE id = ?', (stock_id,))
        result = cursor.fetchone()
    
    if not result:
        await update.callback_query.message.edit_text("❌ Stock investment not found.")
        return
    
    user_id, current_price = result
    
    context.user_data['stock_edit_data'] = {
        'stock_id': stock_id,
        'user_id': user_id,
        'field': 'price'
    }
    context.user_data['awaiting_stock_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_stock_{stock_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"💲 **EDIT STOCK PRICE**\n\n"
        f"**Current Price:** ${current_price:,.2f}\n\n"
        f"Enter the new purchase price:\n\n"
        f"**Examples:**\n"
        f"• 150.75\n"
        f"• 42.00\n"
        f"• 500\n\n"
        f"Type the new price below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def setup_stock_status_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
    """Setup stock status editing"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, status FROM stock_investments WHERE id = ?', (stock_id,))
        result = cursor.fetchone()
    
    if not result:
        await update.callback_query.message.edit_text("❌ Stock investment not found.")
        return
    
    user_id, current_status = result
    
    context.user_data['stock_edit_data'] = {
        'stock_id': stock_id,
        'user_id': user_id,
        'field': 'status'
    }
    context.user_data['awaiting_stock_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_stock_{stock_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"📊 **EDIT STOCK STATUS**\n\n"
        f"**Current Status:** {current_status.title()}\n\n"
        f"Enter the new status:\n\n"
        f"**Possible values:** pending, confirmed, rejected\n\n"
        f"Type the new status below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def setup_regdate_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Setup registration date editing"""
    user_data = db.get_user(user_id)
    current_date = user_data[5][:10] if user_data and user_data[5] else 'N/A'
    
    context.user_data['edit_user_id'] = user_id
    context.user_data['edit_field'] = 'regdate'
    context.user_data['awaiting_user_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_profile_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"📅 **EDIT REGISTRATION DATE**\n\n"
        f"**Current Date:** {current_date}\n\n"
        f"Enter the new registration date:\n\n"
        f"**Format:** YYYY-MM-DD\n"
        f"**Examples:**\n"
        f"• 2024-01-15\n"
        f"• 2023-12-25\n"
        f"• 2024-03-10\n\n"
        f"Type the new date below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def set_user_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, plan: str):
    """Set user's investment plan"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET plan = ? WHERE user_id = ?', (plan, user_id))
            conn.commit()
        
        # Log the action
        log_admin_action(
            admin_id=update.callback_query.from_user.id,
            action_type="plan_change",
            target_user_id=user_id,
            notes=f"Plan changed to: {plan or 'None'}"
        )
        
        plan_display = plan or "None"
        await update.callback_query.message.edit_text(
            f"✅ **PLAN UPDATED**\n\n"
            f"User's investment plan changed to: **{plan_display}**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Edit More", callback_data=f"admin_edit_profile_{user_id}")],
                [InlineKeyboardButton("👤 View Profile", callback_data=f"admin_user_profile_{user_id}")]
            ]),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logging.error(f"Error setting user plan: {e}")
        await update.callback_query.message.edit_text(f"❌ Error updating plan: {str(e)}")

async def confirm_user_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show confirmation for user deletion"""
    user_data = db.get_user(user_id)
    if not user_data:
        await update.callback_query.message.edit_text("❌ User not found.")
        return
    
    username = user_data[1]
    full_name = user_data[3]
    
    keyboard = [
        [InlineKeyboardButton("⚠️ YES, DELETE USER", callback_data=f"admin_confirm_delete_{user_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"admin_user_profile_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"⚠️ **CONFIRM USER DELETION**\n\n"
        f"**User:** @{username} ({full_name or 'N/A'})\n"
        f"**ID:** {user_id}\n\n"
        f"⚠️ **WARNING:** This will permanently delete:\n"
        f"• User profile and account\n"
        f"• All investments and transactions\n"
        f"• Transaction history\n"
        f"• Referral data\n\n"
        f"**THIS CANNOT BE UNDONE!**\n\n"
        f"Are you absolutely sure?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_investment_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, inv_id: int):
    """Show investment editing menu"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT i.user_id, i.amount, i.crypto_type, i.status, i.plan, u.username
            FROM investments i
            JOIN users u ON i.user_id = u.user_id
            WHERE i.id = ?
        ''', (inv_id,))
        investment = cursor.fetchone()
    
    if not investment:
        await update.callback_query.message.edit_text("❌ Investment not found.")
        return
    
    user_id, amount, crypto, status, plan, username = investment
    
    keyboard = [
        [InlineKeyboardButton("💰 Edit Amount", callback_data=f"admin_edit_inv_amount_{inv_id}")],
        [InlineKeyboardButton("📊 Edit Status", callback_data=f"admin_edit_inv_status_{inv_id}")],
        [InlineKeyboardButton("🎯 Edit Plan", callback_data=f"admin_edit_inv_plan_{inv_id}")],
        [InlineKeyboardButton("🗑️ Delete Investment", callback_data=f"admin_delete_inv_{inv_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"admin_edit_investments_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"✏️ **EDIT INVESTMENT {inv_id}**\n\n"
        f"**User:** @{username}\n"
        f"**Amount:** ${amount:,.2f}\n"
        f"**Crypto:** {crypto.upper()}\n"
        f"**Status:** {status.title()}\n"
        f"**Plan:** {plan}\n\n"
        f"Select what to edit:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_stock_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
    """Show stock editing menu"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT si.user_id, si.stock_ticker, si.amount_invested_usd, si.purchase_price, si.status, u.username
            FROM stock_investments si
            JOIN users u ON si.user_id = u.user_id
            WHERE si.id = ?
        ''', (stock_id,))
        stock = cursor.fetchone()
    
    if not stock:
        await update.callback_query.message.edit_text("❌ Stock investment not found.")
        return
    
    user_id, ticker, amount, price, status, username = stock
    
    keyboard = [
        [InlineKeyboardButton("💰 Edit Amount", callback_data=f"admin_edit_stock_amount_{stock_id}")],
        [InlineKeyboardButton("💲 Edit Price", callback_data=f"admin_edit_stock_price_{stock_id}")],
        [InlineKeyboardButton("📊 Edit Status", callback_data=f"admin_edit_stock_status_{stock_id}")],
        [InlineKeyboardButton("🗑️ Delete Stock", callback_data=f"admin_delete_stock_{stock_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"admin_edit_stocks_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"✏️ **EDIT STOCK INVESTMENT**\n\n"
        f"**User:** @{username}\n"
        f"**Stock:** {ticker.upper()}\n"
        f"**Amount:** ${amount:,.2f}\n"
        f"**Price:** ${price:,.2f}\n"
        f"**Status:** {status.title()}\n\n"
        f"Select what to edit:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Add these handlers to process individual field edits
async def handle_individual_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle individual field edit callbacks"""
    parts = data.split("_")
    
    if "inv" in data and "amount" in data:
        inv_id = int(parts[-1])
        await setup_investment_amount_edit(update, context, inv_id)
    elif "inv" in data and "status" in data:
        inv_id = int(parts[-1])
        await setup_investment_status_edit(update, context, inv_id)
    elif "inv" in data and "plan" in data:
        inv_id = int(parts[-1])
        await setup_investment_plan_edit(update, context, inv_id)
    elif "stock" in data and "amount" in data:
        stock_id = int(parts[-1])
        await setup_stock_amount_edit(update, context, stock_id)
    elif "stock" in data and "price" in data:
        stock_id = int(parts[-1])
        await setup_stock_price_edit(update, context, stock_id)
    elif "stock" in data and "status" in data:
        stock_id = int(parts[-1])
        await setup_stock_status_edit(update, context, stock_id)



async def show_pending_investments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending crypto investments"""
    pending_investments = db.get_pending_investments()
    
    if not pending_investments:
        text = "✅ No pending investments at the moment."
        keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = "💰 **PENDING CRYPTO INVESTMENTS**\n\n"
    keyboard = []
    
    for inv in pending_investments[:5]:  # Show max 5 at a time
        inv_id, user_id, username, full_name, email, amount, crypto_type, tx_id, date, notes = inv
        
        text += f"**ID:** {inv_id}\n"
        text += f"**User:** @{username or 'N/A'} [{user_id}]\n"
        text += f"**Name:** {full_name or 'N/A'}\n"
        text += f"**Amount:** ${amount:,.2f} ({crypto_type.upper()})\n"
        text += f"**TX ID:** `{tx_id[:20]}...`\n"
        text += f"**Date:** {date[:16]}\n"
        if notes:
            text += f"**Notes:** {notes}\n"
        text += "─────────────────────\n"
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_investment_{inv_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_investment_{inv_id}")
        ])
    
    if len(pending_investments) > 5:
        text += f"\n... and {len(pending_investments) - 5} more"
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending withdrawals"""
    pending_withdrawals = db.get_pending_withdrawals()
    
    if not pending_withdrawals:
        text = "✅ No pending withdrawals at the moment."
        keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = "💸 **PENDING WITHDRAWALS**\n\n"
    keyboard = []
    
    for wd in pending_withdrawals[:5]:  # Show max 5 at a time
        wd_id, user_id, username, full_name, email, amount, wallet_address, date = wd
        
        text += f"**ID:** {wd_id}\n"
        text += f"**User:** @{username or 'N/A'} [{user_id}]\n"
        text += f"**Name:** {full_name or 'N/A'}\n"
        text += f"**Amount:** ${amount:,.2f}\n"
        text += f"**Wallet:** `{wallet_address[:20]}...`\n"
        text += f"**Date:** {date[:16]}\n"
        text += "─────────────────────\n"
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_withdrawal_{wd_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_withdrawal_{wd_id}")
        ])
    
    if len(pending_withdrawals) > 5:
        text += f"\n... and {len(pending_withdrawals) - 5} more"
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_pending_stock_investments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending stock investments"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT si.id, si.user_id, u.username, u.full_name, u.email,
                   si.amount_invested_usd, si.stock_ticker, si.purchase_price, si.investment_date
            FROM stock_investments si
            JOIN users u ON si.user_id = u.user_id
            WHERE si.status = 'pending'
            ORDER BY si.investment_date DESC
            LIMIT 5
        ''')
        pending_stocks = cursor.fetchall()
    
    if not pending_stocks:
        text = "✅ No pending stock investments at the moment."
        keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = "📈 **PENDING STOCK INVESTMENTS**\n\n"
    keyboard = []
    
    for stock in pending_stocks:
        stock_id, user_id, username, full_name, email, amount, ticker, price, date = stock
        
        text += f"**ID:** {stock_id}\n"
        text += f"**User:** @{username or 'N/A'} [{user_id}]\n"
        text += f"**Name:** {full_name or 'N/A'}\n"
        text += f"**Stock:** {ticker.upper()}\n"
        text += f"**Amount:** ${amount:,.2f}\n"
        text += f"**Price:** ${price:,.2f}\n"
        text += f"**Date:** {date[:16]}\n"
        text += "─────────────────────\n"
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_stock_{stock_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_stock_{stock_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_pending_stock_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending stock sales"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT ss.id, ss.user_id, u.username, si.stock_ticker, ss.shares_sold,
                   ss.sale_price, ss.total_value, ss.sale_date
            FROM stock_sales ss
            JOIN users u ON ss.user_id = u.user_id
            JOIN stock_investments si ON ss.stock_investment_id = si.id
            WHERE ss.status = 'pending'
            ORDER BY ss.sale_date DESC
            LIMIT 5
        ''')
        pending_sales = cursor.fetchall()
    
    if not pending_sales:
        text = "✅ No pending stock sales at the moment."
        keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        return
    
    text = "📉 **PENDING STOCK SALES**\n\n"
    keyboard = []
    
    for sale in pending_sales:
        sale_id, user_id, username, ticker, shares, price, total, date = sale
        
        text += f"**ID:** {sale_id}\n"
        text += f"**User:** @{username or 'N/A'} [{user_id}]\n"
        text += f"**Stock:** {ticker.upper()}\n"
        text += f"**Shares:** {shares}\n"
        text += f"**Price:** ${price:,.2f}\n"
        text += f"**Total:** ${total:,.2f}\n"
        text += f"**Date:** {date[:16]}\n"
        text += "─────────────────────\n"
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_sale_{sale_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_sale_{sale_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management options"""
    keyboard = [
        [InlineKeyboardButton("👤 View All Users", callback_data="admin_user_list"),
         InlineKeyboardButton("🔍 Find User", callback_data="admin_search_user")],
        [InlineKeyboardButton("💳 Edit Balances", callback_data="admin_edit_balance"),
         InlineKeyboardButton("🚫 Ban/Unban User", callback_data="admin_ban_user")],
        [InlineKeyboardButton("📊 User Statistics", callback_data="admin_detailed_stats"),
         InlineKeyboardButton("💰 Top Investors", callback_data="admin_top_investors")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
👥 **USER MANAGEMENT**

Choose an action:

• **View All Users** - Browse all registered users
• **Find User** - Search by ID, username, or email
• **Edit Balances** - Modify user balances
• **Ban/Unban User** - User access control
• **User Statistics** - Detailed analytics
• **Top Investors** - View highest investors
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_balance_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance editing options"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Balance", callback_data="admin_balance_add"),
         InlineKeyboardButton("➖ Subtract Balance", callback_data="admin_balance_subtract")],
        [InlineKeyboardButton("🎯 Set Balance", callback_data="admin_balance_set"),
         InlineKeyboardButton("🔄 Reset Balance", callback_data="admin_balance_reset")],
        [InlineKeyboardButton("📊 View Balance History", callback_data="admin_balance_history")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
💳 **BALANCE MANAGEMENT**

Choose an action:

• **Add Balance** - Add funds to user account
• **Subtract Balance** - Remove funds from user account
• **Set Balance** - Set exact balance amount
• **Reset Balance** - Set balance to zero
• **View Balance History** - See all balance changes

⚠️ **Warning:** Balance changes are logged and irreversible.
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def setup_user_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Setup user search"""
    keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
🔍 **USER SEARCH**

Send me the user information to search for:

**Search by:**
• User ID (e.g., 123456789)
• Username (e.g., @username or username)
• Email address
• Full name (partial match)

**Examples:**
- 123456789
- @johnsmith
- john.smith@email.com
- John Smith

Type your search term below:
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['awaiting_user_search'] = True

async def setup_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Setup broadcast message"""
    keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
📢 **BROADCAST MESSAGE**

Send me the message you want to broadcast to all users.

⚠️ **Important:**
• Maximum 2000 characters
• Supports Markdown formatting
• Will be sent to all registered users
• Cannot be undone once sent

**Example:**
```
🚀 **New Feature Alert!**

We've added stock trading to the platform!
Check it out in the Invest menu.

Happy trading! 💰
```

Type your broadcast message below:
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['awaiting_broadcast_message'] = True

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed user statistics"""
    stats = db.get_user_stats()
    
    # Get additional stats
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get registration stats
        cursor.execute('''
            SELECT DATE(registration_date) as date, COUNT(*) as count
            FROM users 
            WHERE registration_date >= date('now', '-7 days')
            GROUP BY DATE(registration_date)
            ORDER BY date DESC
        ''')
        recent_registrations = cursor.fetchall()
        
        # Get investment stats
        cursor.execute('''
            SELECT plan, COUNT(*) as count, SUM(total_invested) as total
            FROM users 
            WHERE plan IS NOT NULL 
            GROUP BY plan
        ''')
        plan_stats = cursor.fetchall()
    
    text = f"""
📊 **DETAILED BOT STATISTICS**

👥 **User Overview:**
• Total Registered Users: {stats.get('total_users', 0):,}
• Active Investors: {stats.get('active_investors', 0):,}
• Inactive Users: {stats.get('total_users', 0) - stats.get('active_investors', 0):,}

💰 **Investment Overview:**
• Total Crypto Invested: ${stats.get('total_crypto_invested', 0):,.2f}
• Total Stock Invested: ${stats.get('total_stock_invested', 0):,.2f}
• Total User Balances: ${stats.get('total_balances', 0):,.2f}

📈 **Investment Plans:**
    """
    
    for plan, count, total in plan_stats:
        text += f"• {plan}: {count} users (${total:,.2f})\n"
    
    text += f"""

⏳ **Pending Items:**
• Pending Investments: {stats.get('pending_investments', 0)}
• Pending Withdrawals: {stats.get('pending_withdrawals', 0)}

📅 **Recent Activity (Last 7 days):**
    """
    
    for date, count in recent_registrations:
        text += f"• {date}: {count} new users\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_user_stats")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display recent admin activity logs"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT abl.timestamp, abl.admin_id, u1.username as admin_username,
                   abl.target_user_id, u2.username as target_username, abl.action_type,
                   abl.amount, abl.old_balance, abl.new_balance, abl.notes
            FROM admin_balance_logs abl
            LEFT JOIN users u1 ON abl.admin_id = u1.user_id
            LEFT JOIN users u2 ON abl.target_user_id = u2.user_id
            ORDER BY abl.timestamp DESC
            LIMIT 15
        ''')
        logs = cursor.fetchall()
    
    if not logs:
        text = "**ADMIN ACTIVITY LOGS**\n\nNo admin activity recorded yet."
    else:
        text = "**RECENT ADMIN ACTIVITY**\n\n"
        
        for log in logs:
            timestamp, admin_id, admin_username, target_id, target_username, action, amount, old_bal, new_bal, notes = log
            
            text += f"**{timestamp[:16]}**\n"
            text += f"Admin: @{admin_username or str(admin_id)}\n"
            text += f"Action: {action.replace('_', ' ').title()}\n"
            
            if target_id:
                text += f"Target: @{target_username or str(target_id)}\n"
            
            if amount is not None:
                text += f"Amount: ${amount:,.2f}\n"
            
            if old_bal is not None and new_bal is not None:
                text += f"Balance: ${old_bal:,.2f} → ${new_bal:,.2f}\n"
            
            if notes:
                text += f"Notes: {notes[:50]}{'...' if len(notes) > 50 else ''}\n"
            
            text += "─" * 20 + "\n"
    
    keyboard = [
        [InlineKeyboardButton("Refresh Logs", callback_data="admin_logs"),
         InlineKeyboardButton("Export Logs", callback_data="admin_export_logs")],
        [InlineKeyboardButton("Clear Old Logs", callback_data="admin_clear_logs"),
         InlineKeyboardButton("Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')


async def handle_admin_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle admin confirmations"""
    parts = data.split("_")
    if len(parts) < 4:
        return
    
    action_type = parts[2]  # investment, withdrawal, stock, sale
    item_id = int(parts[3])
    admin_id = update.callback_query.from_user.id
    
    try:
        if action_type == "investment":
            success = db.confirm_investment(item_id, admin_id)
            if success:
                # Get investment details for user notification
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT user_id, amount FROM investments WHERE id = ?
                    ''', (item_id,))
                    inv_data = cursor.fetchone()
                    
                    if inv_data:
                        user_id, amount = inv_data
                        # Notify user
                        try:
                            await context.bot.send_message(
                                chat_id=user_id,
                                text=f"🎉 **INVESTMENT CONFIRMED!**\n\n"
                                     f"✅ Your investment of ${amount:,.2f} has been confirmed!\n"
                                     f"💰 Your portfolio has been updated\n"
                                     f"📈 Daily profits are now active\n\n"
                                     f"Check your portfolio to see your updated balance!",
                                parse_mode='Markdown'
                            )
                        except Exception as e:
                            logging.error(f"Failed to notify user {user_id}: {e}")
                
                await update.callback_query.message.edit_text(
                    f"✅ Investment {item_id} confirmed successfully.\nUser has been notified.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_investments")]])
                )
            else:
                await update.callback_query.message.edit_text(f"❌ Failed to confirm investment {item_id}.")
        
        elif action_type == "withdrawal":
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get withdrawal details
                cursor.execute('''
                    SELECT user_id, amount, wallet_address FROM withdrawals 
                    WHERE id = ? AND status = 'pending'
                ''', (item_id,))
                withdrawal = cursor.fetchone()
                
                if withdrawal:
                    user_id, amount, wallet_address = withdrawal
                    
                    # Confirm withdrawal
                    cursor.execute('''
                        UPDATE withdrawals 
                        SET status = 'confirmed', processed_by = ? 
                        WHERE id = ?
                    ''', (admin_id, item_id))
                    
                    # Deduct from user balance
                    cursor.execute('''
                        UPDATE users SET current_balance = current_balance - ? WHERE user_id = ?
                    ''', (amount, user_id))
                    
                    conn.commit()
                    
                    # Notify user
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"✅ **WITHDRAWAL CONFIRMED!**\n\n"
                                 f"💰 Amount: ${amount:,.2f}\n"
                                 f"💳 To: `{wallet_address}`\n"
                                 f"⏰ Processing: Within 24 hours\n\n"
                                 f"Funds will be sent to your wallet shortly!",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logging.error(f"Failed to notify user {user_id}: {e}")
                    
                    await update.callback_query.message.edit_text(
                        f"✅ Withdrawal {item_id} confirmed successfully.\nUser has been notified.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_withdrawals")]])
                    )
                else:
                    await update.callback_query.message.edit_text("❌ Withdrawal not found or already processed.")
        
        elif action_type == "stock":
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE stock_investments 
                    SET status = 'confirmed', confirmed_by = ?, confirmed_date = ? 
                    WHERE id = ?
                ''', (admin_id, datetime.now().isoformat(), item_id))
                conn.commit()
                
                await update.callback_query.message.edit_text(
                    f"✅ Stock investment {item_id} confirmed successfully.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_stock_investments")]])
                )
        
        elif action_type == "sale":
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get sale details
                cursor.execute('''
                    SELECT user_id, total_value FROM stock_sales WHERE id = ?
                ''', (item_id,))
                sale_data = cursor.fetchone()
                
                if sale_data:
                    user_id, total_value = sale_data
                    
                    # Confirm sale and add to user balance
                    cursor.execute('''
                        UPDATE stock_sales 
                        SET status = 'confirmed', processed_by = ?, processed_date = ?
                        WHERE id = ?
                    ''', (admin_id, datetime.now().isoformat(), item_id))
                    
                    cursor.execute('''
                        UPDATE users 
                        SET current_balance = current_balance + ?
                        WHERE user_id = ?
                    ''', (total_value, user_id))
                    
                    conn.commit()
                    
                    await update.callback_query.message.edit_text(
                        f"✅ Stock sale {item_id} confirmed successfully.\nUser balance updated.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_stock_sales")]])
                    )
    
    except Exception as e:
        logging.error(f"Error in admin confirmation: {e}")
        await update.callback_query.message.edit_text(f"❌ Error processing confirmation: {str(e)}")

async def handle_admin_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle admin rejections"""
    parts = data.split("_")
    if len(parts) < 4:
        return
    
    action_type = parts[2]
    item_id = int(parts[3])
    
    # Update status to rejected
    table_map = {
        'investment': 'investments',
        'withdrawal': 'withdrawals', 
        'stock': 'stock_investments',
        'sale': 'stock_sales'
    }
    
    table = table_map.get(action_type)
    if table:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE {table} SET status = 'rejected' WHERE id = ?
            ''', (item_id,))
            conn.commit()
    
    await update.callback_query.message.edit_text(
        f"❌ {action_type.title()} {item_id} rejected.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"admin_{action_type}{'s' if action_type != 'stock' else '_investments'}")]])
    )

async def handle_balance_edit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle balance editing callbacks"""
    action = data.replace("admin_balance_", "")
    
    if action in ["add", "subtract", "set", "reset"]:
        context.user_data['balance_action'] = action
        context.user_data['awaiting_balance_user_id'] = True
        
        action_text = {
            "add": "ADD balance to",
            "subtract": "SUBTRACT balance from", 
            "set": "SET exact balance for",
            "reset": "RESET balance for"
        }
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_edit_balance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
💳 **{action_text[action].upper()} USER**

Send me the User ID of the user you want to modify:

**Examples:**
- 123456789
- 987654321

**Note:** You can also search for users first using the Search User option to find their ID.

Type the User ID below:
        """
        
        await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    
    elif action == "history":
        await show_balance_history(update, context)

async def handle_balance_user_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id_str: str):
    """Handle user ID input for balance editing"""
    try:
        # Clean the input - remove any extra characters
        cleaned_input = user_id_str.strip().replace('@', '').replace('#', '')
        
        # Try to parse as integer
        user_id = int(cleaned_input)
        
        # Verify user exists
        user_data = db.get_user(user_id)
        if not user_data:
            # Also try searching by username if direct ID fails
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users WHERE username LIKE ? OR user_id = ?', 
                             (f'%{cleaned_input}%', user_id))
                user_data = cursor.fetchone()
        
        if not user_data:
            keyboard = [
                [InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")],
                [InlineKeyboardButton("🔙 Balance Menu", callback_data="admin_edit_balance")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"❌ User with ID '{user_id_str}' not found.\n\n"
                "**Tips:**\n"
                "• Enter only numbers (e.g., 123456789)\n"
                "• Use Search User to find the correct ID\n"
                "• Check if user is registered with /start\n\n"
                f"**Debug Info:**\n"
                f"• Input received: '{user_id_str}'\n"
                f"• Parsed as: {user_id}\n"
                f"• Total users in database: {get_total_user_count()}",
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
            f"❌ Invalid User ID format: '{user_id_str}'\n\n"
            "**Please enter:**\n"
            "• Numbers only (e.g., 123456789)\n"
            "• No letters, symbols, or spaces\n\n"
            "**Example:** 652353552"
        )

def get_total_user_count():
    """Helper function to get total user count"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            return cursor.fetchone()[0]
    except:
        return "unknown"

async def show_balance_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance change history"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT abl.timestamp, abl.admin_id, u1.username as admin_username,
                   abl.target_user_id, u2.username as target_username, u2.full_name,
                   abl.action_type, abl.amount, abl.old_balance, abl.new_balance, abl.notes
            FROM admin_balance_logs abl
            LEFT JOIN users u1 ON abl.admin_id = u1.user_id
            LEFT JOIN users u2 ON abl.target_user_id = u2.user_id
            WHERE abl.action_type LIKE '%balance%'
            ORDER BY abl.timestamp DESC
            LIMIT 15
        ''')
        history = cursor.fetchall()
    
    if not history:
        text = "📊 **BALANCE HISTORY**\n\nNo balance modifications found."
    else:
        text = "📊 **BALANCE MODIFICATION HISTORY**\n\n"
        
        for record in history:
            timestamp, admin_id, admin_username, target_id, target_username, target_name, action, amount, old_bal, new_bal, notes = record
            
            text += f"**{timestamp[:16]}**\n"
            text += f"Admin: @{admin_username or str(admin_id)}\n"
            text += f"User: @{target_username or str(target_id)} ({target_name or 'N/A'})\n"
            text += f"Action: {action}\n"
            text += f"Amount: ${amount:,.2f}\n"
            text += f"Balance: ${old_bal:,.2f} → ${new_bal:,.2f}\n"
            if notes:
                text += f"Notes: {notes}\n"
            text += "─────────────\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_balance_history")],
        [InlineKeyboardButton("🔙 Balance Menu", callback_data="admin_edit_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_user_management_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle user management callbacks"""
    action = data.replace("admin_user_", "")
    
    if action == "list":
        await show_user_list(update, context)
    elif action.startswith("profile_"):
        user_id = int(action.replace("profile_", ""))
        await show_user_profile(update, context, user_id)

async def show_user_list(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Show paginated user list"""
    users_per_page = 8
    offset = page * users_per_page
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, full_name, total_invested, current_balance, registration_date
            FROM users 
            ORDER BY registration_date DESC 
            LIMIT ? OFFSET ?
        ''', (users_per_page, offset))
        users = cursor.fetchall()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
    
    if not users:
        text = "👥 **USER LIST**\n\nNo users found."
        keyboard = [[InlineKeyboardButton("🔙 User Management", callback_data="admin_user_management")]]
    else:
        text = f"👥 **USER LIST - Page {page + 1}**\n\n"
        keyboard = []
        
        for user in users:
            user_id, username, full_name, invested, balance, reg_date = user
            
            text += f"**ID:** {user_id}\n"
            text += f"**Username:** @{username or 'N/A'}\n"
            text += f"**Name:** {full_name or 'N/A'}\n"
            text += f"**Invested:** ${invested:,.2f}\n"
            text += f"**Balance:** ${balance:,.2f}\n"
            text += f"**Joined:** {reg_date[:10]}\n"
            text += "─────────────\n"
            
            keyboard.append([InlineKeyboardButton(f"View {username or user_id}", callback_data=f"admin_user_profile_{user_id}")])
        
        # Navigation
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_user_list_{page-1}"))
        if offset + users_per_page < total_users:
            nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_user_list_{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 User Management", callback_data="admin_user_management")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show detailed user profile for admin"""
    user_data = db.get_user(user_id)
    if not user_data:
        await update.callback_query.message.edit_text("❌ User not found.")
        return
    
    # Unpack user data
    user_id, username, first_name, full_name, email, reg_date, plan, total_invested, current_balance, profit_earned, last_update, referral_code, referred_by = user_data
    
    # Get additional data
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Get investment count
        cursor.execute('SELECT COUNT(*) FROM investments WHERE user_id = ? AND status = "confirmed"', (user_id,))
        investment_count = cursor.fetchone()[0]
        
        # Get referral count
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user_id,))
        referral_count = cursor.fetchone()[0]
        
        # Get recent activity
        cursor.execute('''
            SELECT 'investment' as type, amount, investment_date as date FROM investments 
            WHERE user_id = ? AND status = 'confirmed'
            UNION ALL
            SELECT 'withdrawal' as type, amount, withdrawal_date as date FROM withdrawals 
            WHERE user_id = ? AND status = 'confirmed'
            ORDER BY date DESC LIMIT 5
        ''', (user_id, user_id))
        recent_activity = cursor.fetchall()
    
    text = f"""
👤 **USER PROFILE**

📋 **Info:**
• ID: {user_id}
• Username: @{username or 'N/A'}
• Name: {full_name or 'N/A'}
• Email: {email or 'N/A'}
• Joined: {reg_date[:10] if reg_date else 'Unknown'}

💼 **Account:**
• Plan: {plan or 'None'}
• Invested: ${total_invested:,.2f}
• Balance: ${current_balance:,.2f}
• Profit: ${profit_earned:,.2f}
• Referral: {referral_code}
    """
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data=f"admin_edit_profile_{user_id}")],
        [InlineKeyboardButton("✏️ Edit Stocks", callback_data=f"admin_edit_stocks_{user_id}")],
        [InlineKeyboardButton("💳 Edit Balance", callback_data=f"admin_edit_user_balance_{user_id}")],
        [InlineKeyboardButton("✏️ Edit Investment", callback_data=f"admin_edit_investments_{user_id}")],
        [InlineKeyboardButton("🔙 User List", callback_data="admin_user_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_edit_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show profile editing menu"""
    keyboard = [
        [InlineKeyboardButton("👤 Edit Name", callback_data=f"admin_edit_name_{user_id}"),
         InlineKeyboardButton("📧 Edit Email", callback_data=f"admin_edit_email_{user_id}")],
        [InlineKeyboardButton("🎯 Edit Plan", callback_data=f"admin_edit_plan_{user_id}"),
         InlineKeyboardButton("🔄 Reset Referral", callback_data=f"admin_reset_refcode_{user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"admin_user_profile_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text("✏️ **EDIT PROFILE**\n\nSelect field to edit:", reply_markup=reply_markup, parse_mode='Markdown')


async def setup_name_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Setup name editing"""
    user_data = db.get_user(user_id)
    current_name = user_data[3] if user_data else 'N/A'
    
    context.user_data['edit_user_id'] = user_id
    context.user_data['edit_field'] = 'name'
    context.user_data['awaiting_user_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_profile_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"✏️ **EDIT USER NAME**\n\n"
        f"**Current:** {current_name}\n\n"
        f"Enter new full name:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
async def setup_email_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Setup email editing"""
    user_data = db.get_user(user_id)
    current_email = user_data[4] if user_data else 'N/A'
    
    context.user_data['edit_user_id'] = user_id
    context.user_data['edit_field'] = 'email'
    context.user_data['awaiting_user_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_profile_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"📧 **EDIT EMAIL**\n\n**Current:** {current_email}\n\nEnter new email:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_plan_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Show plan editing menu"""
    keyboard = [
        [InlineKeyboardButton("🥉 Core Plan", callback_data=f"admin_set_plan_{user_id}_CORE")],
        [InlineKeyboardButton("🥈 Growth Plan", callback_data=f"admin_set_plan_{user_id}_GROWTH")],
        [InlineKeyboardButton("🥇 Alpha Plan", callback_data=f"admin_set_plan_{user_id}_ALPHA")],
        [InlineKeyboardButton("❌ Remove Plan", callback_data=f"admin_set_plan_{user_id}_NONE")],
        [InlineKeyboardButton("🔙 Back", callback_data=f"admin_edit_profile_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text("🎯 **EDIT PLAN**\n\nSelect plan:", reply_markup=reply_markup, parse_mode='Markdown')


async def reset_referral_code(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Reset referral code"""
    new_code = f"AV{user_id}{random.randint(100, 999)}"
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET referral_code = ? WHERE user_id = ?', (new_code, user_id))
        conn.commit()
    
    log_admin_action(
        admin_id=update.callback_query.from_user.id,
        action_type="referral_reset",
        target_user_id=user_id,
        notes=f"New code: {new_code}"
    )
    
    await update.callback_query.message.edit_text(
        f"🔄 **REFERRAL RESET**\n\n✅ New code: `{new_code}`",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Profile", callback_data=f"admin_user_profile_{user_id}")]]),
        parse_mode='Markdown'
    )

async def setup_add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, page: int = 0):
    """Paged stock selection menu"""
    user = db.get_user(user_id)
    if not user:
        await update.callback_query.message.edit_text("❌ User not found.")
        return

    username = user[1] if user[1] else str(user_id)

    # Pagination
    per_page = 8  # Show more tickers per page
    start = page * per_page
    end = start + per_page
    page_stocks = ALL_STOCKS[start:end]

    keyboard = []
    for i in range(0, len(page_stocks), 2):
        row = []
        row.append(InlineKeyboardButton(
            page_stocks[i], 
            callback_data=f"admin_add_stock_ticker_{page_stocks[i]}_{user_id}"
        ))
        if i + 1 < len(page_stocks):
            row.append(InlineKeyboardButton(
                page_stocks[i + 1], 
                callback_data=f"admin_add_stock_ticker_{page_stocks[i + 1]}_{user_id}"
            ))
        keyboard.append(row)

    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_add_stock_page_{user_id}_{page-1}"))
    if end < len(ALL_STOCKS):
        nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"admin_add_stock_page_{user_id}_{page+1}"))
    if nav_buttons:
        keyboard.append(nav_buttons)

        # Cancel button
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data=f"admin_user_profile_{user_id}")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    total_pages = (len(ALL_STOCKS) + per_page - 1) // per_page
    await update.callback_query.message.edit_text(
        f"📈 **ADD MANUAL STOCK**\n\n"
        f"**User:** @{username}\n"
        f"**Page:** {page + 1} of {total_pages}\n"
        f"**Available Stocks:** {len(ALL_STOCKS)}\n\n"
        f"Select a stock ticker:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def setup_add_investment(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Setup manual crypto investment addition by an admin."""
    user = db.get_user(user_id)
    if not user:
        await update.callback_query.message.edit_text("❌ User not found.")
        return

    # Start the conversation to gather investment details
    context.user_data['manual_investment'] = {
        'user_id': user_id,
        'username': user[1],
        'step': 'amount'
    }
    context.user_data['awaiting_manual_investment'] = True

    keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data=f"admin_user_profile_{user_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"💰 **MANUAL CRYPTO INVESTMENT**\n\n"
        f"Adding investment for: @{user[1]} (ID: {user_id})\n\n"
        f"**Step 1 of 3: Amount**\n"
        f"Please enter the investment amount in USD (e.g., 500.75):",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def setup_investment_amount_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, inv_id: int):
    """Setup investment amount editing"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, amount FROM investments WHERE id = ?', (inv_id,))
        result = cursor.fetchone()
    
    if not result:
        await update.callback_query.message.edit_text("❌ Investment not found.")
        return
    
    user_id, current_amount = result
    
    context.user_data['investment_edit_data'] = {
        'investment_id': inv_id,
        'user_id': user_id,
        'field': 'amount'
    }
    context.user_data['awaiting_investment_edit'] = True
    
    keyboard = [[InlineKeyboardButton("🔙 Cancel", callback_data=f"admin_edit_inv_{inv_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"💰 **EDIT INVESTMENT AMOUNT**\n\n"
        f"**Current Amount:** ${current_amount:,.2f}\n\n"
        f"Enter the new investment amount:\n\n"
        f"**Examples:**\n"
        f"• 1000\n"
        f"• 5500.50\n"
        f"• 25000\n\n"
        f"Type the new amount below:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Command handlers for direct admin commands
async def confirm_investment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to confirm investment"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /confirm_investment <user_id> <amount>")
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        # Find the investment to confirm
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM investments 
                WHERE user_id = ? AND amount = ? AND status = 'pending'
                ORDER BY investment_date DESC LIMIT 1
            ''', (user_id, amount))
            result = cursor.fetchone()
            
            if not result:
                await update.message.reply_text(f"❌ No pending investment found for user {user_id} with amount ${amount}")
                return
            
            investment_id = result[0]
        
        success = db.confirm_investment(investment_id, update.effective_user.id)
        
        if success:
            await update.message.reply_text(f"✅ Investment confirmed for user {user_id}: ${amount:,.2f}")
        
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 **INVESTMENT CONFIRMED!**\n\n"
                         f"✅ Your investment of ${amount:,.2f} has been confirmed!\n"
                         f"💰 Your portfolio has been updated\n"
                         f"📈 Daily profits are now active\n\n"
                         f"Check your portfolio to see your updated balance!",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Failed to notify user {user_id}: {e}")
        else:
            await update.message.reply_text(f"❌ Failed to confirm investment for user {user_id}")
    
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid command format. Use: /confirm_investment <user_id> <amount>")

async def confirm_withdrawal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to confirm withdrawal"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /confirm_withdrawal <user_id>")
        return
    
    try:
        user_id = int(context.args[0])
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get latest pending withdrawal
            cursor.execute('''
                SELECT id, amount, wallet_address FROM withdrawals 
                WHERE user_id = ? AND status = 'pending' 
                ORDER BY withdrawal_date DESC LIMIT 1
            ''', (user_id,))
            withdrawal = cursor.fetchone()
            
            if not withdrawal:
                await update.message.reply_text(f"❌ No pending withdrawal found for user {user_id}")
                return
            
            withdrawal_id, amount, wallet_address = withdrawal
            
            # Confirm withdrawal
            cursor.execute('''
                UPDATE withdrawals 
                SET status = 'confirmed', processed_by = ? 
                WHERE id = ?
            ''', (update.effective_user.id, withdrawal_id))
            
            # Deduct from user balance
            cursor.execute('''
                SELECT current_balance FROM users WHERE user_id = ?
            ''', (user_id,))
            old_balance = cursor.fetchone()[0]
            new_balance = old_balance - amount
            
            cursor.execute('''
                UPDATE users SET current_balance = ? WHERE user_id = ?
            ''', (new_balance, user_id))
            
            conn.commit()
            
            # Log the action
            log_admin_action(
                admin_id=update.effective_user.id,
                action_type="withdrawal_confirmation",
                target_user_id=user_id,
                amount=amount,
                old_balance=old_balance,
                new_balance=new_balance,
                notes=f"Withdrawal ID {withdrawal_id} confirmed via command"
            )
        
        await update.message.reply_text(f"✅ Withdrawal confirmed for user {user_id}: ${amount:,.2f}")
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **WITHDRAWAL CONFIRMED!**\n\n"
                     f"💰 Amount: ${amount:,.2f}\n"
                     f"💳 To: `{wallet_address}`\n"
                     f"⏰ Processing: Within 24 hours\n\n"
                     f"Funds will be sent to your wallet shortly!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify user {user_id}: {e}")
    
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid command format. Use: /confirm_withdrawal <user_id>")

async def handle_manual_stock_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the admin's input during the manual stock creation process."""
    if not context.user_data.get('awaiting_manual_stock'):
        return

    data = context.user_data['manual_stock']
    user_id = data['user_id']
    step = data['step']
    text = update.message.text.strip()
    
    try:
        if step == 'amount':
            amount = float(text)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            data['amount'] = amount
            data['step'] = 'price'
            
            keyboard = [[InlineKeyboardButton("❌ Cancel", callback_data=f"admin_user_profile_{user_id}")]]
            await update.message.reply_text(
                f"✅ Amount set to ${amount:,.2f}\n\n"
                f"**Step 3 of 3: Purchase Price**\n"
                f"Enter the purchase price per share (e.g., 175.25):",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

        elif step == 'price':
            price = float(text)
            if price <= 0:
                raise ValueError("Price must be positive.")
            data['price'] = price
            
            # Calculate shares
            shares = data['amount'] / price
            data['shares'] = shares
            
            # Final confirmation step
            keyboard = [[
                InlineKeyboardButton("✅ Confirm & Add", callback_data="admin_confirm_manual_stock"),
                InlineKeyboardButton("❌ Cancel", callback_data=f"admin_user_profile_{user_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"**CONFIRM STOCK INVESTMENT**\n\n"
                f"**User:** @{data.get('username', 'N/A')} (ID: {user_id})\n"
                f"**Ticker:** {data['ticker']}\n"
                f"**Amount Invested:** ${data['amount']:,.2f}\n"
                f"**Purchase Price:** ${data['price']:,.2f}\n"
                f"**Shares:** {shares:.4f}\n\n"
                f"Please confirm to add this stock investment.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            context.user_data.pop('awaiting_manual_stock', None)

    except (ValueError, TypeError) as e:
        await update.message.reply_text(f"❌ Invalid input: {e}\nPlease try again.")       