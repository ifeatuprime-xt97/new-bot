"""
Admin command handlers - Complete functionality
"""
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from message_handlers import handle_balance_confirmation_callback
from message_handlers import handle_broadcast_confirmation_callback
from config import ADMIN_USER_IDS
from database import db

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command - Main admin panel"""
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ You do not have permission to access the admin panel.")
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
🛠️ **ADMIN CONTROL PANEL**

📊 **Quick Stats:**
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

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle admin callback queries"""
    user = update.callback_query.from_user
    if user.id not in ADMIN_USER_IDS:
        await update.callback_query.message.edit_text("❌ Access denied.")
        return
    
    # Parse callback data
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
    elif data == "admin_user_list":
        await show_user_list(update, context, 0)
    elif data.startswith("admin_user_list_"):
        page = int(data.split("_")[-1])
        await show_user_list(update, context, page)
    elif data.startswith("admin_user_profile_"):
        user_id = int(data.split("_")[-1])
        await show_user_profile(update, context, user_id)
    elif data == "admin_confirm_balance_change":
        await handle_balance_confirmation_callback(update, context)
    elif data == "admin_confirm_broadcast":
        await handle_broadcast_confirmation_callback(update, context)
    elif data.startswith("admin_confirm_"):
        await handle_admin_confirmation(update, context, data)
    elif data.startswith("admin_reject_"):
        await handle_admin_rejection(update, context, data)
    elif data.startswith("admin_balance_"):
        await handle_balance_edit_callback(update, context, data)
    elif data.startswith("admin_user_"):
        await handle_user_management_callback(update, context, data)
    else:
        await update.callback_query.message.edit_text(
            "❌ Unknown admin action.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]])
        )


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
    """Show recent admin activity logs"""
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
            LIMIT 10
        ''')
        logs = cursor.fetchall()
    
    if not logs:
        text = "📋 **ADMIN LOGS**\n\nNo admin activity logged yet."
    else:
        text = "📋 **RECENT ADMIN ACTIVITY**\n\n"
        
        for log in logs:
            timestamp, admin_id, admin_username, target_id, target_username, action, amount, old_bal, new_bal, notes = log
            
            text += f"**{timestamp[:16]}**\n"
            text += f"Admin: @{admin_username or admin_id}\n"
            text += f"Action: {action}\n"
            text += f"Target: @{target_username or target_id}\n"
            if amount:
                text += f"Amount: ${amount:,.2f}\n"
                text += f"Balance: ${old_bal:,.2f} → ${new_bal:,.2f}\n"
            if notes:
                text += f"Notes: {notes}\n"
            text += "─────────────\n"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_logs")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
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
👤 **USER PROFILE - {full_name or username}**

📋 **Personal Info:**
• ID: {user_id}
• Username: @{username or 'N/A'}
• Full Name: {full_name or 'N/A'}
• Email: {email or 'N/A'}
• Member Since: {reg_date[:10] if reg_date else 'Unknown'}

💼 **Account Summary:**
• Plan: {plan or 'No active plan'}
• Total Invested: ${total_invested:,.2f}
• Current Balance: ${current_balance:,.2f}
• Total Profit: ${profit_earned:,.2f}

📊 **Activity Stats:**
• Confirmed Investments: {investment_count}
• Referrals Made: {referral_count}
• Referral Code: {referral_code}

🔄 **Recent Activity:**
    """
    
    for activity in recent_activity:
        activity_type, amount, date = activity
        text += f"• {activity_type.title()}: ${amount:,.2f} ({date[:10]})\n"
    
    keyboard = [
        [InlineKeyboardButton("💳 Edit Balance", callback_data=f"admin_edit_user_balance_{user_id}"),
         InlineKeyboardButton("📊 Full History", callback_data=f"admin_user_history_{user_id}")],
        [InlineKeyboardButton("💬 Send Message", callback_data=f"admin_message_user_{user_id}"),
         InlineKeyboardButton("🚫 Ban User", callback_data=f"admin_ban_user_{user_id}")],
        [InlineKeyboardButton("🔙 User List", callback_data="admin_user_list")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

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
            
            # Log the action
            log_admin_action(
                admin_id=update.effective_user.id,
                action_type="investment_confirmation",
                target_user_id=user_id,
                amount=amount,
                notes=f"Investment ID {investment_id} confirmed via command"
            )
            
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

def log_admin_action(admin_id: int, action_type: str, target_user_id: int = None, 
                     amount: float = None, old_balance: float = None, 
                     new_balance: float = None, notes: str = None):
    """Log admin actions to database"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO admin_balance_logs 
                (admin_id, target_user_id, action_type, amount, old_balance, new_balance, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (admin_id, target_user_id, action_type, amount, old_balance, new_balance, notes))
            conn.commit()
    except Exception as e:
        logging.error(f"Failed to log admin action: {e}")