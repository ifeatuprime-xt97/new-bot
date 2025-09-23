"""
Utility functions shared across handlers
"""

import logging
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def log_admin_action(
    admin_id: int,
    action_type: str,
    target_user_id: int = None,
    amount: float = None,
    notes: str = None,
    context: ContextTypes.DEFAULT_TYPE = None
):
    """
    Log and optionally notify an admin action.

    Args:
        admin_id (int): The Telegram ID of the admin performing the action.
        action_type (str): The type of action performed (e.g., 'investment_confirmation').
        target_user_id (int, optional): The affected user's Telegram ID.
        amount (float, optional): The transaction amount if applicable.
        notes (str, optional): Extra notes or description of the action.
        context: PTB context, required if you want to send a Telegram message.
    """

    # Build log message
    message = f"👮 Admin {admin_id} performed {action_type}"
    if target_user_id:
        message += f" on user {target_user_id}"
    if amount:
        message += f" with amount {amount}"
    if notes:
        message += f"\n📝 Notes: {notes}"

    # Log to console
    logger.info(message)

    # If context is passed, send Telegram message back to the admin
    if context:
        try:
            await context.bot.send_message(chat_id=admin_id, text=message)
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")
