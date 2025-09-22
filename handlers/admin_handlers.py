"""
Admin command handlers
"""
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_USER_IDS
from database import db

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ You do not have permission to access the admin panel.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🤑 Pending Investments", callback_data="admin_investments"),
         InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("📈 Pending Stock Investments", callback_data="admin_stock_investments"),
         InlineKeyboardButton("📉 Pending Stock Sales", callback_data="admin_stock_sales")],
        [InlineKeyboardButton("👥 User Stats", callback_data="admin_user_stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "🛠️ **ADMIN PANEL**\n\nSelect an option to manage the bot."
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle admin callback queries"""
    action = data.split("_")[1] if len(data.split("_")) > 1 else None
    
    if action == "investments":
        await show_pending_investments(update, context)
    elif action == "withdrawals":
        await show_pending_withdrawals(update, context)
    elif action == "user" and data.endswith("stats"):
        await show_user_stats(update, context)
    elif action == "broadcast":
        await handle_broadcast_setup(update, context)
    elif data.startswith("admin_confirm_"):
        await handle_admin_confirmation(update, context, data)
    elif data.startswith("admin_reject_"):
        await handle_admin_rejection(update, context, data)
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
    
    text = "💰 **PENDING INVESTMENTS**\n\n"
    keyboard = []
    
    for inv in pending_investments:
        inv_id, user_id, username, full_name, email, amount, crypto_type, tx_id, date, notes = inv
        
        text += f"**ID:** {inv_id}\n"
        text += f"**User:** @{username} [{user_id}]\n"
        text += f"**Name:** {full_name or 'N/A'}\n"
        text += f"**Email:** {email or 'N/A'}\n"
        text += f"**Amount:** ${amount:,.2f} ({crypto_type.upper()})\n"
        text += f"**TX ID:** `{tx_id[:20]}...`\n"
        text += f"**Date:** {date}\n"
        if notes:
            text += f"**Notes:** {notes}\n"
        text += f"**Command:** `/confirm_investment {user_id} {amount}`\n"
        text += "─────────────────────\n"
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_investment_{inv_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_investment_{inv_id}")
        ])
    
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
    
    for wd in pending_withdrawals:
        wd_id, user_id, username, full_name, email, amount, wallet_address, date = wd
        
        text += f"**ID:** {wd_id}\n"
        text += f"**User:** @{username} [{user_id}]\n"
        text += f"**Name:** {full_name or 'N/A'}\n"
        text += f"**Email:** {email or 'N/A'}\n"
        text += f"**Amount:** ${amount:,.2f}\n"
        text += f"**Wallet:** `{wallet_address}`\n"
        text += f"**Date:** {date}\n"
        text += f"**Command:** `/confirm_withdrawal {user_id}`\n"
        text += "─────────────────────\n"
        
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_withdrawal_{wd_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_withdrawal_{wd_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics"""
    stats = db.get_user_stats()
    
    text = f"""
📊 **BOT USER STATISTICS**

• **Total Users:** {stats['total_users']:,}
• **Active Investors:** {stats['active_investors']:,}
• **Total Crypto Invested:** ${stats['total_crypto_invested']:,.2f}
• **Total Stock Invested:** ${stats['total_stock_invested']:,.2f}
• **Total User Balances:** ${stats['total_balances']:,.2f}

**Pending Items:**
• **Investments:** {stats['pending_investments']}
• **Withdrawals:** {stats['pending_withdrawals']}
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_user_stats")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_broadcast_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Setup broadcast message"""
    keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
📢 **BROADCAST MESSAGE**

Please reply with the message you want to broadcast to all users.

⚠️ **Important:**
• Maximum 2000 characters
• Supports Markdown formatting
• Will be sent to all registered users

Type your message below:
    """
    
    await update.callback_query.message.edit_text(text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    context.user_data['awaiting_broadcast_message'] = True

async def handle_admin_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle admin confirmations"""
    parts = data.split("_")
    if len(parts) < 4:
        return
    
    action_type = parts[2]  # investment, withdrawal, etc.
    item_id = int(parts[3])
    admin_id = update.callback_query.from_user.id
    
    if action_type == "investment":
        success = db.confirm_investment(item_id, admin_id)
        if success:
            await update.callback_query.message.edit_text(f"✅ Investment {item_id} confirmed successfully.")
            # Notify user
            # TODO: Add user notification
        else:
            await update.callback_query.message.edit_text(f"❌ Failed to confirm investment {item_id}.")
    
    elif action_type == "withdrawal":
        # TODO: Implement withdrawal confirmation
        await update.callback_query.message.edit_text(f"✅ Withdrawal {item_id} confirmed.")
    
    # Add more confirmation types as needed

async def handle_admin_rejection(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle admin rejections"""
    parts = data.split("_")
    if len(parts) < 4:
        return
    
    action_type = parts[2]
    item_id = int(parts[3])
    
    # TODO: Implement rejection logic for different types
    await update.callback_query.message.edit_text(f"❌ {action_type.title()} {item_id} rejected.")

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
                UPDATE users SET current_balance = current_balance - ? WHERE user_id = ?
            ''', (amount, user_id))
            
            conn.commit()
        
        await update.message.reply_text(f"✅ Withdrawal confirmed for user {user_id}: ${amount:,.2f}")
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ **WITHDRAWAL CONFIRMED!**\n\n"
                     f"💰 Amount: ${amount:,.2f}\n"
                     f"💸 To: `{wallet_address}`\n"
                     f"⏰ Processing: Within 24 hours\n\n"
                     f"Funds will be sent to your wallet shortly!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to notify user {user_id}: {e}")
    
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid command format. Use: /confirm_withdrawal <user_id>")