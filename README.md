# Trading Bot - Rebuilt Version

A comprehensive Telegram trading bot for cryptocurrency and stock investments with automated profit calculations.

## Features

- **User Management**: Registration with referral system
- **Crypto Investments**: Tiered investment plans with daily returns
- **Stock Trading**: Individual stock purchases and sales
- **Portfolio Tracking**: Real-time profit/loss calculations
- **Live Market Data**: Crypto and stock price feeds
- **Admin Panel**: Complete management interface
- **Automated Profits**: Daily profit calculations and updates

## Architecture

The bot is now organized into modular components:

- `config.py` - Configuration settings and constants
- `database.py` - Database operations and management
- `market_data.py` - Market data fetching and processing
- `handlers/` - Organized command and callback handlers
- `main.py` - Main application entry point

## Key Improvements

1. **Modular Structure**: Separated concerns into logical modules
2. **Error Handling**: Comprehensive error handling throughout
3. **Database Management**: Context managers for safe database operations
4. **Type Safety**: Better type hints and validation
5. **Logging**: Improved logging for debugging and monitoring
6. **Code Organization**: Clean separation of user, admin, and callback handlers

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Update your bot token in `config.py`

3. Run the bot:
```bash
python main.py
```

## Database

The bot uses SQLite with the following main tables:
- `users` - User accounts and balances
- `investments` - Crypto investment records
- `stock_investments` - Stock purchase records
- `withdrawals` - Withdrawal requests
- `referrals` - Referral tracking

## Admin Commands

- `/admin` - Access admin panel
- `/confirm_investment <user_id> <amount>` - Confirm crypto investment
- `/confirm_withdrawal <user_id>` - Confirm withdrawal request

## Security Features

- Admin-only access controls
- Input validation and sanitization
- Secure wallet address generation
- Transaction verification requirements

## Error Handling

- Graceful error recovery
- User-friendly error messages
- Comprehensive logging
- Database transaction safety"# new-botdd" 
