"""
Main bot application
"""
import logging
from datetime import time
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.request import HTTPXRequest

from config import BOT_TOKEN, ADMIN_USER_IDS
from handlers.user_handlers import start_command, portfolio_command, calculate_user_profits
from handlers.admin_handlers import admin_command, confirm_investment_command, confirm_withdrawal_command, handle_manual_stock_input
from handlers.callback_handlers import handle_callback_query
from handlers.message_handlers import handle_text_message

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def daily_profit_job(context):
    """Daily job to calculate user profits"""
    logger.info("Running daily profit calculation...")
    try:
        calculate_user_profits()
        logger.info("Daily profit calculation completed successfully")
    except Exception as e:
        logger.error(f"Error in daily profit calculation: {e}")

async def error_handler(update, context):
    """Log errors caused by updates"""
    logger.error(f"Exception while handling update: {context.error}")

async def unknown_command(update, context):
    """Handle unknown commands"""
    await update.message.reply_text(
        "❌ Unknown command. Use /start for the main menu or click a button from the keyboard."
    )

def main():
    """Start the bot"""
    # Create custom request with timeout settings
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0
    )
    
    # Build application
    application = Application.builder().token(BOT_TOKEN).request(request).build()
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("portfolio", portfolio_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("confirm_investment", confirm_investment_command))
    application.add_handler(CommandHandler("confirm_withdrawal", confirm_withdrawal_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_stock_input))
    # Add callback query handler - SINGLE HANDLER FOR ALL CALLBACKS
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Schedule daily profit calculation at midnight UTC
    job_queue = application.job_queue
    job_queue.run_daily(daily_profit_job, time=time(0, 0, 0))
    
    logger.info("Bot is starting...")
    logger.info(f"Admin IDs configured: {ADMIN_USER_IDS}")
    
    # Initialize database
    try:
        from database import db
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admin_balance_logs';")
        result = cursor.fetchone()
        print("Admin table exists:", result is not None)
        
    # Start bot
    application.run_polling(allowed_updates=["message", "callback_query"])

    print("🎉 Admin system integration complete!")
    print("📝 Follow the step-by-step guide above to integrate all components")
    print("🧪 Test each feature thoroughly before deploying to production")

if __name__ == '__main__':
    main()