import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    JobQueue
)
import requests
from datetime import datetime, timedelta, time  
import json
import random
import yfinance as yf
import asyncio
from typing import Dict, List, Optional
import uuid
import sqlite3
from dataclasses import dataclass
from enum import Enum
import os
from telegram.request import HTTPXRequest

# --- Configuration ---
# Replace with your actual values
BOT_TOKEN = "8295756385:AAHNVHS4zMXYKVylnLjiWbJ_4LtZiWcKhyI"  # Replace with your bot token
ADMIN_USER_IDS = [6417609151]  # Add your numerical admin user IDs here, e.g., [12345, 67890]

# --- Investment Plans ---
class InvestmentPlan(Enum):
    CORE = {"name": "Core (Starter)", "min_amount": 1000, "max_amount": 15000, "daily_return": 0.0143}
    GROWTH = {"name": "Growth (Balanced)", "min_amount": 20000, "max_amount": 80000, "daily_return": 0.0214}
    ALPHA = {"name": "Alpha (Premium)", "min_amount": 100000, "max_amount": float('inf'), "daily_return": 0.0286}

# --- Crypto Wallet Addresses ---
WALLET_ADDRESSES = {
    'btc': [
        'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
        'bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq',
        'bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4',
        'bc1qrp33g0q4c70qx3qlak6k8zj2fwf0j2qx6xlr',
        'bc1qxm7dx6xlr4j5qx3qlak6k8zj2fwf0j2qx8qt'
    ],
    'usdt': [
        'TQmJxnKRLwKgYL6Vqv0xK5gF2RKr7r8t9M',
        'TUP8L3VXFWKJB5gNk2tNJKaYwx8cGHrNeE',
        'TVJYBuJkHDSDK8KkMdP2vNdcxMLpHG5KkV',
        'TYASjP7gTVW8kKfHgL6ZKXSvN2x9JhK',
        'TNKBsP6KHgY8kKfNgN2tMKaYwx8cFGrNeE'
    ],
    'sol': [
        '9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM',
        'J3dxNj7nDRRqRRXuEMynDG57DkZK4jYRuv3Garmb1i99',
        'CWE8jPTUYhdCTZYWPiRhejQKCH98NvK8XjJG9W6F',
        '7xKXtg2CW9UL6o2TCuFShdHRjhGmuqmh2q6R',
        'BrDXA3u2Z8tqr7N6FkKqP8GW9nR4YhF6tL'
    ],
    'ton': [
        'UQD2NmD_lH5f5u1Vp8G0FKlsn_8t9M4h_KLp',
        'UQBfAN00CvhVz4B_rlCRLgP_K5h9RL-7JL',
        'UQD7Kt7sEG8-7s9IwqXz4B_rlCRL4h_KL',
        'UQC1kJ_Mn6ZVoF3rlCRLgP_K5h9RL-9T',
        'UQB2Mk4_Qr8sVz4B_rlCRLgP_K5h8-L7'
    ],
    'eth': [
        # Corrected: Replaced invalid addresses with validly formatted placeholders
        '0x742d35Cc6B88F86E8C7CB3C8B3D0F6C1C2E6a4b1',
        '0x1bde33327a27459C9237651871822895632231f2',
        '0x2c4D7962d385D23D3e8a4D42b584DBA3742d4834',
        '0x3eA6E5A8e21a22453e9a4f3C15c1bFa38437A99E',
        '0x4aB1E297A649f7eA23aA1192323f4aE8e3B4a2b6'
    ]
}

# --- Logging setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- Conversation States ---
REGISTER_NAME, REGISTER_EMAIL = range(2)
AWAITING_PAYMENT_DETAILS, AWAITING_STOCK_PAYMENT_DETAILS, AWAITING_WITHDRAW_AMOUNT, AWAITING_WITHDRAW_ADDRESS, AWAITING_BROADCAST_MESSAGE, AWAITING_STOCK_SHARES = range(2, 8)

# --- Stock Lists ---
TECH_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'INTC', 'AMD']
NON_TECH_STOCKS = ['V', 'JPM', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'UNH', 'VZ', 'DIS']

# --- All stocks combined for live prices ---
ALL_STOCKS_FOR_PRICES = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'INTC', 'AMD',
                        'V', 'JPM', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'UNH', 'VZ', 'DIS']

# --- Database setup ---
def init_database():
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        full_name TEXT,
        email TEXT,
        registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        plan TEXT,
        total_invested REAL DEFAULT 0,
        current_balance REAL DEFAULT 0,
        profit_earned REAL DEFAULT 0,
        last_profit_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        referral_code TEXT UNIQUE,
        referred_by INTEGER
    )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            crypto_type TEXT,
            wallet_address TEXT,
            transaction_id TEXT,
            investment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            plan TEXT,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount_invested_usd REAL,
            stock_ticker TEXT,
            purchase_price REAL,
            investment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            wallet_address TEXT,
            withdrawal_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            processed_by INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER,
            referred_id INTEGER,
            referral_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            bonus_amount REAL DEFAULT 0,
            FOREIGN KEY (referrer_id) REFERENCES users (referrer_id),
            FOREIGN KEY (referred_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database
init_database()


# Add missing columns if they don't exist
def migrate_database():
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()

    # Check if notes column exists in investments table
    cursor.execute("PRAGMA table_info(investments)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'notes' not in columns:
        cursor.execute('ALTER TABLE investments ADD COLUMN notes TEXT')
        logging.info("Added notes column to investments table")

    # Check if full_name and email columns exist in users table
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]

    if 'full_name' not in user_columns:
        cursor.execute('ALTER TABLE users ADD COLUMN full_name TEXT')
        logging.info("Added full_name column to users table")

    if 'email' not in user_columns:
        cursor.execute('ALTER TABLE users ADD COLUMN email TEXT')
        logging.info("Added email column to users table")

    conn.commit()
    conn.close()
# Run migration
migrate_database()
def migrate_stock_tables():
    """Ensure stock tables have all required columns"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    # Add processed_date to stock_sales if missing
    cursor.execute("PRAGMA table_info(stock_sales)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'processed_date' not in columns:
        cursor.execute('ALTER TABLE stock_sales ADD COLUMN processed_date TIMESTAMP')
        logging.info("Added processed_date to stock_sales table")
    
    # Add confirmed_date to stock_investments if missing
    cursor.execute("PRAGMA table_info(stock_investments)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'confirmed_date' not in columns:
        cursor.execute('ALTER TABLE stock_investments ADD COLUMN confirmed_date TIMESTAMP')
        logging.info("Added confirmed_date to stock_investments table")
    
    # Add confirmed_by to stock_investments if missing
    if 'confirmed_by' not in columns:
        cursor.execute('ALTER TABLE stock_investments ADD COLUMN confirmed_by INTEGER')
        logging.info("Added confirmed_by to stock_investments table")
    
    conn.commit()
    conn.close()

# Add this new function after migrate_database():
def create_dummy_leaderboard():
    """Create sample leaderboard data with impressive numbers"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard_dummy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            rank_position INTEGER,
            total_earnings REAL,
            weekly_earnings REAL,
            success_rate REAL,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data if table is empty
    cursor.execute('SELECT COUNT(*) FROM leaderboard_dummy')
    if cursor.fetchone()[0] == 0:
        sample_data = [
            # Top tier whales
            ('AlphaWhale_Pro', 1, 125670.50, 23420.30, 98.7),
            ('CryptoQueen_X', 2, 98750.25, 18930.80, 97.2),
            ('DiamondHands88', 3, 78450.90, 15640.20, 96.1),
            ('MoonMission_X', 4, 65430.75, 13450.40, 95.4),
            ('BullRunLegend', 5, 52340.40, 11230.60, 94.8),
            
            # Mid-tier success stories
            ('TradeMaster_7', 6, 41280.15, 9230.25, 93.2),
            ('ProfitPilot', 7, 34560.80, 7840.90, 92.5),
            ('SmartMoney_X', 8, 29870.45, 6540.30, 91.8),
            ('GrowthGuru', 9, 25640.20, 5230.70, 91.1),
            ('WealthWizard', 10, 21430.95, 4320.15, 90.4),
            
            # Emerging stars
            ('RisingStar_3', 11, 18760.30, 3870.40, 89.7),
            ('NewMoney_Mogul', 12, 15640.75, 3340.80, 89.0),
            ('TradeTiger', 13, 13420.60, 2890.20, 88.3),
            ('ProfitPhoenix', 14, 11230.40, 2340.50, 87.6),
            ('MarketMaestro', 15, 9230.85, 1870.30, 86.9),
            
            # Recent joiners with good performance
            ('FreshCapital', 16, 7540.20, 1560.70, 86.2),
            ('SmartStarter', 17, 6230.15, 1230.40, 85.5),
            ('NewTrader_N1', 18, 5120.80, 980.60, 84.8),
            ('GrowthBeginner', 19, 4230.45, 760.20, 84.1),
            ('WealthSeed', 20, 3340.30, 560.80, 83.4)
        ]
        
        cursor.executemany('''
            INSERT INTO leaderboard_dummy (username, rank_position, total_earnings, weekly_earnings, success_rate)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_data)
    
    conn.commit()
    conn.close()

def create_stock_sales_table():
    """Create stock sales tracking table"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stock_investment_id INTEGER,
            shares_sold REAL,
            sale_price REAL,
            total_value REAL,
            wallet_address TEXT,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            processed_by INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (stock_investment_id) REFERENCES stock_investments (id)
        )
    ''')
    conn.commit()
    conn.close()

def create_admin_logs_table():
    """Create table to log admin balance modifications"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_balance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            target_user_id INTEGER,
            action_type TEXT,
            amount REAL,
            old_balance REAL,
            new_balance REAL,
            timestamp TIMESTAMP,
            notes TEXT,
            FOREIGN KEY (admin_id) REFERENCES users (user_id),
            FOREIGN KEY (target_user_id) REFERENCES users (user_id)
        )
    ''')
    conn.commit()
    conn.close()   
# --- Database Functions ---
def get_user_from_db(user_id):
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_or_update_user(user_id, username, first_name, full_name=None, email=None, referred_by_id=None):
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()

    user_exists = get_user_from_db(user_id)

    if user_exists:
        cursor.execute('''
            UPDATE users SET username = ?, first_name = ?, full_name = ?, email = ? WHERE user_id = ?
        ''', (username, first_name, full_name, email, user_id))
    else:
        referral_code = f"AV{user_id}{random.randint(100, 999)}"
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, full_name, email, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, full_name, email, referral_code, referred_by_id))

        if referred_by_id:
            cursor.execute('''
                INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)
            ''', (referred_by_id, user_id))

    conn.commit()
    conn.close()

def calculate_stock_pnl(stock_ticker, amount_invested, purchase_price):
    """
    Calculates the real-time profit and loss for a single stock.
    """
    try:
        stock = yf.Ticker(stock_ticker)
        current_price = stock.info.get('regularMarketPrice')

        if current_price:
            total_shares = amount_invested / purchase_price
            current_value = total_shares * current_price
            profit_loss = current_value - amount_invested
            return profit_loss
        else:
            logging.error(f"Could not fetch real-time price for {stock_ticker}. Price data is not available.")
            return 0.0

    except Exception as e:
        logging.error(f"Error fetching data for {stock_ticker}: {e}")
        return 0.0

def calculate_user_profits():
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()

    # --- Step 1: Calculate Crypto Profits ---
    cursor.execute('''
        SELECT u.user_id, u.total_invested, u.current_balance, u.plan, u.last_profit_update
        FROM users u
        WHERE u.total_invested > 0 AND u.plan IS NOT NULL
    ''')
    crypto_users = cursor.fetchall()

    for user_data in crypto_users:
        user_id, total_invested, current_balance, plan, last_update = user_data

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

    # --- Step 2: Calculate Stock Profits ---
    cursor.execute('''
        SELECT user_id, amount_invested_usd, stock_ticker, purchase_price
        FROM stock_investments WHERE status = 'confirmed'
    ''')
    stock_investments = cursor.fetchall()

    for user_id, amount_invested, ticker, purchase_price in stock_investments:
        pnl = calculate_stock_pnl(ticker, amount_invested, purchase_price)
        logging.info(f"User {user_id} stock {ticker} current P&L: ${pnl:.2f} (not added to balance - shown in portfolio)")

    conn.commit()
    conn.close()

def get_random_wallet(crypto_type):
    if crypto_type.lower() in WALLET_ADDRESSES:
        return random.choice(WALLET_ADDRESSES[crypto_type.lower()])
    return None

def get_stocks_info(stock_list):
    """
    Improved: Fetches data for multiple stocks in a single API call for efficiency.
    """
    stocks_info = []
    if not stock_list:
        return stocks_info

    try:
        data = yf.Tickers(' '.join(stock_list))

        for ticker in stock_list:
            # Access individual ticker data from the batch result
            info = data.tickers[ticker.upper()].info
            current_price = info.get('regularMarketPrice')

            if info.get('previousClose') and current_price:
                price_change_percent = ((current_price - info['previousClose']) / info['previousClose']) * 100
                change_emoji = '▲' if price_change_percent >= 0 else '▼'
                price_change_text = f"{change_emoji} {price_change_percent:.2f}%"
            else:
                price_change_text = "N/A"

            stocks_info.append({
                'ticker': ticker,
                'name': info.get('shortName', ticker),
                'price': f"${current_price:,.2f}" if isinstance(current_price, (int, float)) else "N/A",
                'change': price_change_text
            })
    except Exception as e:
        logging.error(f"Error fetching batch stock data: {e}")
        # Fallback in case of error
        for ticker in stock_list:
            stocks_info.append({
                'ticker': ticker, 
                'name': ticker, 
                'price': "Error", 
                'change': "N/A"
            })
    
    return stocks_info

def get_top_20_crypto_prices():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 20,
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '24h'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        crypto_info = []
        for item in data:
            price_change = item.get('price_change_percentage_24h_in_currency', 'N/A')
            change_emoji = '▲' if price_change and price_change >= 0 else '▼'

            crypto_info.append({
                'name': item.get('name', 'N/A'),
                'symbol': item.get('symbol', 'N/A').upper(),
                'price': f"${item.get('current_price', 'N/A'):,.2f}",
                'change': f"{change_emoji} {price_change:.2f}%" if isinstance(price_change, (int, float)) else "N/A"
            })
        return crypto_info
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching crypto prices from CoinGecko: {e}")
        return None

async def notify_admin_investment_flagged(context, user_id, amount, reason):
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT full_name, email, username FROM users WHERE user_id = ?', (user_id,))
    user_info = cursor.fetchone()
    full_name = user_info[0] if user_info else 'N/A'
    email = user_info[1] if user_info else 'N/A'
    username = user_info[2] if user_info else 'N/A'
    conn.close()
    """
    Sends a notification to the admin about a flagged investment.
    """
    admin_notification = (
        f"⚠️ URGENT: INVESTMENT NEEDS FIXING ⚠️\n\n"
        f"User: [{user_id}](tg://user?id={user_id})\n"
        f"Name: {full_name}\nEmail: {email}\n"
        f"Amount: ${amount:,.2f}\n"
        f"Reason: {reason}\n\n"
        "Please review this investment and update it manually."
    )
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Failed to send flag notification to admin {admin_id}: {e}")

# --- New functions for improved live prices ---
async def display_live_prices_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display live prices menu to choose between crypto and stocks"""
    keyboard = [
        [InlineKeyboardButton("💎 Crypto Prices", callback_data="live_crypto_prices_0")],
        [InlineKeyboardButton("📊 Stock Prices", callback_data="live_stock_prices_0")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    prices_menu_text = """
📈 LIVE MARKET PRICES

Choose the market you want to view:

💎 Crypto Prices - Top 20 cryptocurrencies by market cap
📊 Stock Prices - Top 20 stocks from major indices

All prices are updated in real-time for accurate trading decisions.

Select an option below: 👇
    """

    if update.callback_query:
        await update.callback_query.message.edit_text(
            prices_menu_text.strip(),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            prices_menu_text.strip(),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def display_crypto_prices(update: Update, context: ContextTypes.DEFAULT_TYPE, start_index: int = 0):
    """Display crypto prices with pagination (10 per page)"""
    query = update.callback_query
    await query.answer()

    # Show loading message
    await query.edit_message_text("⏳ Fetching real-time crypto prices...")

    crypto_prices = get_top_20_crypto_prices()

    if not crypto_prices:
        keyboard = [[InlineKeyboardButton("🔙 Live Prices Menu", callback_data="show_prices")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "❌ Failed to fetch crypto prices. Please try again later.",
            reply_markup=reply_markup
        )
        return

    # Get 10 cryptos for current page
    end_index = min(start_index + 10, len(crypto_prices))
    page_cryptos = crypto_prices[start_index:end_index]
    current_page = (start_index // 10) + 1
    total_pages = (len(crypto_prices) + 9) // 10  # Ceiling division

    crypto_text = f"💎 CRYPTO PRICES (Page {current_page}/{total_pages})\n\n"

    for i, crypto in enumerate(page_cryptos, start=start_index + 1):
        name = crypto['name'].replace('_', ' ').replace('*', '')
        symbol = crypto['symbol'].replace('_', ' ').replace('*', '')
        price = crypto['price'].replace('_', ' ').replace('*', '')
        change = crypto['change'].replace('_', ' ').replace('*', '')

        crypto_text += f"{i}. {name} ({symbol})\n"
        crypto_text += f"   💵 {price} | {change}\n\n"

    # Navigation buttons
    keyboard = []
    nav_buttons = []

    if start_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"live_crypto_prices_{start_index - 10}"))

    nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"live_crypto_prices_{start_index}"))

    if end_index < len(crypto_prices):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"live_crypto_prices_{start_index + 10}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("📊 View Stocks Instead", callback_data="live_stock_prices_0")])
    keyboard.append([InlineKeyboardButton("🔙 Live Prices Menu", callback_data="show_prices")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(
        crypto_text.strip(),
        reply_markup=reply_markup
    )

async def display_stock_prices(update: Update, context: ContextTypes.DEFAULT_TYPE, start_index: int = 0):
    """Display stock prices with pagination (10 per page)"""
    query = update.callback_query
    await query.answer()

    # Show loading message
    await query.edit_message_text("⏳ Fetching real-time stock prices...")

    stock_prices = get_stocks_info(ALL_STOCKS_FOR_PRICES)

    if not stock_prices:
        keyboard = [[InlineKeyboardButton("🔙 Live Prices Menu", callback_data="show_prices")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            "❌ Failed to fetch stock prices. Please try again later.",
            reply_markup=reply_markup
        )
        return

    # Get 10 stocks for current page
    end_index = min(start_index + 10, len(stock_prices))
    page_stocks = stock_prices[start_index:end_index]
    current_page = (start_index // 10) + 1
    total_pages = (len(stock_prices) + 9) // 10

    stock_text = f"📊 STOCK PRICES (Page {current_page}/{total_pages})\n\n"

    for i, stock in enumerate(page_stocks, start=start_index + 1):
        name = stock['name'].replace('_', ' ').replace('*', '')
        ticker = stock['ticker'].replace('_', ' ').replace('*', '')
        price = stock['price'].replace('_', ' ').replace('*', '')
        change = stock['change'].replace('_', ' ').replace('*', '')

        stock_text += f"{i}. {name} ({ticker})\n"
        stock_text += f"   💵 {price} | {change}\n\n"

    # Navigation buttons
    keyboard = []
    nav_buttons = []

    if start_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"live_stock_prices_{start_index - 10}"))

    nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"live_stock_prices_{start_index}"))

    if end_index < len(stock_prices):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"live_stock_prices_{start_index + 10}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("💎 View Crypto Instead", callback_data="live_crypto_prices_0")])
    keyboard.append([InlineKeyboardButton("🔙 Live Prices Menu", callback_data="show_prices")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(
        stock_text.strip(),
        reply_markup=reply_markup
    )
    
async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the motivating dummy leaderboard"""
    query = update.callback_query if update.callback_query else None
    
    # Get dummy leaderboard data
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, rank_position, total_earnings, weekly_earnings, success_rate 
        FROM leaderboard_dummy 
        ORDER BY rank_position ASC 
        LIMIT 10
    ''')
    leaderboard_data = cursor.fetchall()
    conn.close()
    
    if not leaderboard_data:
        text = "🏆 LEADERBOARD\n\nNo leaderboard data available yet.\nStart investing to climb the ranks!"
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.message.edit_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return
    
    # Create engaging leaderboard display
    leaderboard_text = "🏆 TOP TRADERS LEADERBOARD\n\n"
    leaderboard_text += "🚀 *See what top investors are earning!*\n\n"
    
    rank_emojis = ["🥇", "🥈", "🥉", "👨‍💼", "👩‍💼", "💎", "🔥", "⚡", "🌟", "🎯"]
    
    for i, (username, rank_pos, total_earnings, weekly_earnings, success_rate) in enumerate(leaderboard_data[:8], 1):
        # Clean and format username
        display_name = username.replace('_', ' ')[:18]
        if len(username) > 18:
            display_name += "..."
        
        emoji = rank_emojis[i-1] if i <= len(rank_emojis) else f"{i}."
        
        # Add some motivational flair
        profit_emoji = "📈" if weekly_earnings > 5000 else "📊"
        
        leaderboard_text += f"{emoji} *{display_name}*\n"
        leaderboard_text += f"   💰 Total: ${total_earnings:,.0f}\n"
        leaderboard_text += f"   {profit_emoji} This Week: +${weekly_earnings:,.0f}\n"
        leaderboard_text += f"   🎯 Success Rate: {success_rate:.1f}%\n\n"
    
    # Add motivational message
    leaderboard_text += "💡 *Join the ranks of successful traders!*\n"
    leaderboard_text += "Start investing today and watch your profits grow! 🚀"
    
    # Create engaging keyboard
    keyboard = [
        [InlineKeyboardButton("💰 Start Investing", callback_data="invest_menu")],
        [InlineKeyboardButton("👥 View Full Leaderboard", callback_data="leaderboard_full")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.message.edit_text(leaderboard_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(leaderboard_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user.username:
        if update.message:
            await update.message.reply_text(
                "⚠️ Username Required!\n\n"
                "Please set a Telegram username first:\n"
                "1. Go to Settings -> Edit Profile\n"
                "2. Create a username\n"
                "3. Come back and use /start again\n\n"
                "A username is required for investment tracking and security."
            )
        return

    # Check if user is already registered with full details
    user_data = get_user_from_db(user.id)
    if user_data and user_data[3] and user_data[4]:  # full_name and email exist
        # User is fully registered, show main menu
        await show_main_menu(update, context, user)
        return

    # User needs to complete registration
    referred_by_id = None
    if context.args and len(context.args[0]) > 3:
        referral_code = context.args[0]
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (referral_code,))
        referrer = cursor.fetchone()
        conn.close()
        if referrer:
            referred_by_id = referrer[0]

    # Store referral info for later
    context.user_data['referred_by_id'] = referred_by_id

    # Start registration process
    await update.message.reply_text(
        "🚀 Welcome to The Alpha Vault Investment Platform!\n\n"
        "To get started, please provide your full name:"
    )
    
    context.user_data['registration_step'] = REGISTER_NAME

async def show_main_menu(update, context, user):
    """Show the main menu with leaderboard prominently featured"""
    keyboard = [
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard"),
         InlineKeyboardButton("💰 Invest", callback_data="invest_menu")],
        [InlineKeyboardButton("📊 Portfolio", callback_data="view_portfolio")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw_funds"),
         InlineKeyboardButton("📈 Live Prices", callback_data="show_prices")],
        [InlineKeyboardButton("👤 My Profile", callback_data="show_profile"),
        InlineKeyboardButton("📖 Get Help", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    start_text = f"""
🚀 Welcome to The Alpha Vault Investment Platform!

Hello {user.first_name}! Welcome to your AI-powered crypto investment hub.

🏆 *See What Top Traders Are Earning!*

💎 Investment Plans Available:
• 🥉 Core (Starter): $1K - $15K (1.43% daily)
• 🥈 Growth (Balanced): $20K - $80K (2.14% daily) 
• 🥇 Alpha (Premium): $100K+ (2.86% daily)

🎯 Key Features:
• Automated daily profit generation
• Secure multi-crypto wallet system  
• Real-time portfolio tracking
• Instant withdrawals (24h processing)
• Referral bonuses

⚡ *Check the leaderboard first - then start your journey to the top!* 👇
    """
    
    if update.message:
        await update.message.reply_text(
            start_text.strip(),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif update.callback_query:
        await update.callback_query.message.edit_text(
            start_text.strip(),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
async def invest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user.username:
        if update.message:
            await update.message.reply_text("❌ Please set a Telegram username first before investing!")
        return

    keyboard = [
        [InlineKeyboardButton("💰 Crypto Plans", callback_data="crypto_plans")],
        [InlineKeyboardButton("📈 Stocks", callback_data="show_stocks_page_0")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    invest_text = """
💰 INVESTMENT OPTIONS

Select your preferred investment vehicle:

• Crypto Plans: Choose from our tiered investment plans for automated daily crypto profits.
• Stocks: Invest in top tech stocks and grow your portfolio with market leaders.

Your investment journey starts here! 👇
    """

    if update.callback_query:
        await update.callback_query.message.edit_text(
            invest_text.strip(),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            invest_text.strip(),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def portfolio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    try:
        user_data = get_user_from_db(user.id)

        if not user_data:
            error_msg = "❌ You're not registered yet. Use /start first!"
            if update.message:
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.message.edit_text(error_msg)
            return

        # Add logging to debug data structure
        logging.info(f"User data length: {len(user_data) if user_data else 'None'}")
        
        # Ensure we have all required fields
        if len(user_data) < 13:
            logging.error(f"Incomplete user data for user {user.id}: {len(user_data)} fields")
            error_msg = "❌ Account data incomplete. Please contact support."
            if update.message:
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.message.edit_text(error_msg)
            return

        calculate_user_profits()
        user_data = get_user_from_db(user.id)

        # Safely unpack user data
        (user_id, username, first_name, full_name, email, reg_date, 
         plan, total_invested, current_balance, profit_earned, 
         last_update, referral_code, referred_by) = user_data

        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()

        # Get crypto investment history
        cursor.execute('''
            SELECT crypto_type, amount, investment_date
            FROM investments
            WHERE user_id = ? AND status = 'confirmed'
            ORDER BY investment_date DESC
            LIMIT 5
        ''', (user.id,))
        crypto_history = cursor.fetchall()

        # Get stock investment history
        cursor.execute('''
            SELECT stock_ticker, amount_invested_usd, purchase_price, investment_date
            FROM stock_investments
            WHERE user_id = ? AND status = 'confirmed'
            ORDER BY investment_date DESC
            LIMIT 5
        ''', (user.id,))
        stock_history = cursor.fetchall()

        # Calculate total stock P&L
        total_stock_pnl = 0
        stock_details = []
        for ticker, amount_invested, purchase_price, date in stock_history:
            try:
                pnl = calculate_stock_pnl(ticker, amount_invested, purchase_price)
                total_stock_pnl += pnl
                stock_details.append((ticker, amount_invested, pnl))
            except Exception as e:
                logging.error(f"Error calculating P&L for {ticker}: {e}")
                stock_details.append((ticker, amount_invested, 0))

        # Get withdrawal history
        cursor.execute('''
            SELECT amount, withdrawal_date
            FROM withdrawals
            WHERE user_id = ? AND status = 'confirmed'
            ORDER BY withdrawal_date DESC
            LIMIT 5
        ''', (user.id,))
        withdrawal_history = cursor.fetchall()
        conn.close()

        # Fixed keyboard structure - properly nested arrays
        keyboard = [
            [InlineKeyboardButton("💰 Invest More", callback_data="invest_menu"),
             InlineKeyboardButton("💸 Withdraw Funds", callback_data="withdraw_funds")],
            [InlineKeyboardButton("👥 Referral Info", callback_data="referral_info"),
             InlineKeyboardButton("🔄 Refresh Portfolio", callback_data="refresh_portfolio")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu"),
             InlineKeyboardButton("📜 Transaction History", callback_data="show_history")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

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

        # Calculate and display ROI
        if total_invested > 0:
            roi = ((current_balance / total_invested - 1) * 100)
            portfolio_text += f"\n• Crypto ROI: {roi:.2f}%"
        else:
            portfolio_text += "\n• Crypto ROI: 0.00%"

        # Add stock information if available
        if stock_details:
            total_stock_invested = sum(amount for _, amount, _ in stock_details)
            portfolio_text += f"\n\n📈 Stock Portfolio:"
            portfolio_text += f"\n• Total Stock Invested: ${total_stock_invested:,.2f}"
            portfolio_text += f"\n• Current Stock P&L: ${total_stock_pnl:,.2f}"
            if total_stock_pnl >= 0:
                portfolio_text += f"\n• Stock Performance: +${total_stock_pnl:,.2f} 📈"
            else:
                portfolio_text += f"\n• Stock Performance: {total_stock_pnl:,.2f} 📉"


        # Add daily earnings information
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

        # Add referral information
        portfolio_text += f"\n\n🎁 Referral Code: `{referral_code}`"
        portfolio_text += "\nShare your code and earn 5% commission!"

        # Send the response
        if update.message:
            await update.message.reply_text(
                portfolio_text.strip(),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif update.callback_query:
            await update.callback_query.message.edit_text(
                portfolio_text.strip(),
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logging.error(f"Error in portfolio_command: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        error_text = "❌ Error loading portfolio. Please try again later."
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(error_text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.message.edit_text(error_text, reply_markup=reply_markup)
        return
    
async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced withdrawal with clear options"""
    user = update.effective_user
    user_data = get_user_from_db(user.id)

    if not user_data:
        error_msg = "❌ You're not registered yet. Use /start first!"
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.message.reply_text(error_msg)
        return

    current_balance = user_data[8]
    
    # Check for stocks
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*), COALESCE(SUM(amount_invested_usd), 0) 
        FROM stock_investments 
        WHERE user_id = ? AND status = "confirmed"
    ''', (user.id,))
    stock_count, total_stock_value = cursor.fetchone()
    conn.close()

    if current_balance <= 0:
        withdraw_text = (
            f"❌ Insufficient Balance\n\n"
            f"Your current AI Trader balance: ${current_balance:.2f}\n"
            f"Stock Portfolio Value: ${total_stock_value:.2f}\n\n"
            f"Options:\n"
            f"• Invest more to build AI Trader balance\n"
            f"• Sell stocks first if you have any\n\n"
            f"Use the Invest button to start earning!"
        )
        keyboard = [
            [InlineKeyboardButton("💰 Invest Now", callback_data="invest_menu")],
            [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
        ]
        if stock_count > 0:
            keyboard.insert(0, [InlineKeyboardButton("📈 Sell Stocks", callback_data="sell_stocks")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(withdraw_text, reply_markup=reply_markup)
        else:
            await update.callback_query.message.edit_text(withdraw_text, reply_markup=reply_markup)
        return

    context.user_data['withdraw_options'] = {
        '25%': current_balance * 0.25,
        '50%': current_balance * 0.50,
        '100%': current_balance,
    }

    keyboard = [
        [InlineKeyboardButton("💸 Withdraw 25%", callback_data="withdraw_25"),
         InlineKeyboardButton("💸 Withdraw 50%", callback_data="withdraw_50")],
        [InlineKeyboardButton("💸 Withdraw 100%", callback_data="withdraw_100"),
         InlineKeyboardButton("💰 Custom Amount", callback_data="withdraw_custom")],
    ]

    if stock_count > 0:
        keyboard.insert(0, [InlineKeyboardButton("📈 Sell Stocks First", callback_data="sell_stocks")])

    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    withdraw_text = f"""
💸 WITHDRAWAL CENTER

💰 Available Balances:
- AI Trader Balance: ${current_balance:,.2f}
- Stock Portfolio: ${total_stock_value:.2f} ({stock_count} holdings)

Quick Withdraw Options:
- 25%: ${context.user_data['withdraw_options']['25%']:,.2f}
- 50%: ${context.user_data['withdraw_options']['50%']:,.2f}  
- 100%: ${context.user_data['withdraw_options']['100%']:,.2f}

⚡ Process:
1. Select amount or sell stocks first
2. Provide USDT wallet address (TRC20)
3. Admin processes within 24 hours

🔒 All withdrawals verified for security.
Minimum: $10 USDT | Network: TRC20

Select option below:
    """

    if update.message:
        await update.message.reply_text(withdraw_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(withdraw_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

async def handle_sell_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, stock_ticker, amount_invested_usd, purchase_price, investment_date
        FROM stock_investments
        WHERE user_id = ? AND status = "confirmed"
        ORDER BY investment_date DESC
    ''', (user.id,))
    user_stocks = cursor.fetchall()
    conn.close()

    if not user_stocks:
        keyboard = [[InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw_funds")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.message.edit_text(
            "❌ No stocks to sell.",
            reply_markup=reply_markup
        )
        return

    stocks_text = "📈 YOUR STOCKS FOR SALE\n\n"
    keyboard = []

    for stock_id, ticker, amount_invested, purchase_price, date in user_stocks:
        current_pnl = calculate_stock_pnl(ticker, amount_invested, purchase_price)
        pnl_text = f"(+${current_pnl:.2f})" if current_pnl >= 0 else f"(${current_pnl:.2f})"

        stocks_text += f"• {ticker.upper()}: ${amount_invested:,.2f} {pnl_text}\n"
        keyboard.append([InlineKeyboardButton(f"Sell {ticker.upper()}", callback_data=f"sell_stock_{stock_id}")])

    keyboard.append([InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw_funds")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.edit_text(
        stocks_text + "\nSelect a stock to sell:",
        reply_markup=reply_markup
    )

async def handle_individual_stock_sale(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_id: int):
    """Handle selling individual stocks with share selection"""
    user = update.effective_user
    
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stock_ticker, amount_invested_usd, purchase_price
        FROM stock_investments
        WHERE id = ? AND user_id = ? AND status = "confirmed"
    ''', (stock_id, user.id))
    stock_data = cursor.fetchone()
    conn.close()
    
    if not stock_data:
        await update.callback_query.message.edit_text("Error: Stock not found or already sold.")
        return
    
    ticker, amount_invested, purchase_price = stock_data
    total_shares = amount_invested / purchase_price
    current_price = get_current_stock_price(ticker)
    
    if current_price == 0:
        current_price = purchase_price  # Fallback to purchase price
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Stock Portfolio", callback_data="sell_stocks")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.message.edit_text(
        f"📈 SELL {ticker.upper()} SHARES\n\n"
        f"Your Holdings:\n"
        f"• Total Shares: {total_shares:.2f}\n"
        f"• Purchase Price: ${purchase_price:.2f}\n"
        f"• Current Price: ${current_price:.2f}\n"
        f"• Total Current Value: ${total_shares * current_price:.2f}\n\n"
        f"How many shares do you want to sell?\n"
        f"Reply with number (e.g., 10 or 15.5)\n"
        f"Maximum: {total_shares:.2f} shares",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    context.user_data['pending_stock_sale'] = {
        'stock_id': stock_id,
        'ticker': ticker,
        'total_shares': total_shares,
        'purchase_price': purchase_price,
        'current_price': current_price
    }

def get_current_stock_price(ticker):
    """Get current stock price"""
    try:
        stock = yf.Ticker(ticker)
        current_price = stock.info.get('regularMarketPrice')
        return current_price if current_price else 0
    except:
        return 0

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced profile with full user details"""
    user = update.effective_user
    user_data = get_user_from_db(user.id)

    if not user_data:
        error_msg = "❌ You're not registered yet. Use /start first!"
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.message.reply_text(error_msg)
        return
    
    # Unpack user data
    user_id, username, first_name, full_name, email, reg_date, plan, total_invested, current_balance, profit_earned, last_update, referral_code, referred_by = user_data
    
    # Get additional stats
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    # Get referral count
    cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user.id,))
    referral_count = cursor.fetchone()[0]
    
    # Get investment history count
    cursor.execute('SELECT COUNT(*) FROM investments WHERE user_id = ? AND status = "confirmed"', (user.id,))
    investment_count = cursor.fetchone()[0]
    
    # Get stock count
    cursor.execute('SELECT COUNT(*) FROM stock_investments WHERE user_id = ? AND status = "confirmed"', (user.id,))
    stock_count = cursor.fetchone()[0]
    
    conn.close()
    
    profile_text = f"""
👤 YOUR PROFILE

📋 Personal Information:
- Full Name: {full_name or 'Not provided'}
- Email: {email or 'Not provided'}
- Telegram: @{username}
- Member Since: {reg_date[:10]}
- User ID: {user_id}

💼 Account Summary:
- Investment Plan: {plan if plan else 'No active plan'}
- Total Crypto Invested: ${total_invested:,.2f}
- Current Balance: ${current_balance:,.2f}
- Total Profit Earned: ${profit_earned:,.2f}

📊 Activity Stats:
- Crypto Investments: {investment_count}
- Stock Holdings: {stock_count}
- Referrals Made: {referral_count}

🎯 Referral Code: `{referral_code}`
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 Portfolio", callback_data="view_portfolio")],
        [InlineKeyboardButton("👥 Referrals", callback_data="referral_info")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_enhanced_leaderboard")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(profile_text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_full_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE, start_index: int = 0):
    """Display full dummy leaderboard with pagination"""
    query = update.callback_query
    await query.answer()
    
    # Get all dummy leaderboard data
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, rank_position, total_earnings, weekly_earnings, success_rate 
        FROM leaderboard_dummy 
        ORDER BY rank_position ASC
    ''')
    leaderboard_data = cursor.fetchall()
    conn.close()
    
    if not leaderboard_data:
        await query.message.edit_text("🏆 No leaderboard data available.")
        return
    
    # Pagination - show 10 at a time
    end_index = min(start_index + 10, len(leaderboard_data))
    page_leaders = leaderboard_data[start_index:end_index]
    current_page = (start_index // 10) + 1
    total_pages = (len(leaderboard_data) + 9) // 10
    
    lb_text = f"🏆 FULL LEADERBOARD (Page {current_page}/{total_pages})\n\n"
    
    rank_emojis = ["🥇", "🥈", "🥉", "👨‍💼", "👩‍💼", "💎", "🔥", "⚡", "🌟", "🎯"]
    
    for i, (username, rank_pos, total_earnings, weekly_earnings, success_rate) in enumerate(page_leaders, start=start_index + 1):
        # Clean username
        display_name = username.replace('_', ' ')[:18]
        if len(username) > 18:
            display_name += "..."
        
        emoji = rank_emojis[i-1] if i <= len(rank_emojis) else f"{i}."
        
        # Add performance indicators
        performance = "🔥 HOT" if weekly_earnings > 7000 else "📈 UP" if weekly_earnings > 3000 else "📊 STEADY"
        
        lb_text += f"{emoji} *{display_name}*\n"
        lb_text += f"   💰 Total: ${total_earnings:,.0f}\n"
        lb_text += f"   {performance} +${weekly_earnings:,.0f} this week\n"
        lb_text += f"   🎯 {success_rate:.1f}% success rate\n\n"
    
    # Add motivational footer
    lb_text += f"💪 *{len(leaderboard_data)} elite traders and counting...*\n"
    lb_text += "Your success story starts with your first investment! 🚀"
    
    # Navigation buttons
    keyboard = []
    nav_buttons = []
    
    if start_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"leaderboard_full_{start_index - 10}"))
    
    nav_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"leaderboard_full_{start_index}"))
    
    if end_index < len(leaderboard_data):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"leaderboard_full_{start_index + 10}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("💰 Invest Now", callback_data="invest_menu")])
    keyboard.append([InlineKeyboardButton("🏆 Back to Top", callback_data="leaderboard")])
    keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(lb_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    
# --- Admin Commands ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        if update.message:
            await update.message.reply_text("❌ You do not have permission to access the admin panel.")
        else:
            await update.callback_query.answer("❌ You do not have permission to access the admin panel.", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("🤑 Pending Investments", callback_data="admin_investments"),
        InlineKeyboardButton("💸 Pending Withdrawals", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("📉 Pending Stock Sales", callback_data="admin_stock_sales"),
        InlineKeyboardButton("📈 Pending Stock Investments", callback_data="admin_stock_investments")],
        [InlineKeyboardButton("👥 User Stats", callback_data="admin_user_stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("🛠️ ADMIN PANEL\n\nSelect an option to manage the bot.", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("🛠️ ADMIN PANEL\n\nSelect an option to manage the bot.", reply_markup=reply_markup)

async def confirm_investment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        return

    if len(context.args) != 2:
        await update.message.reply_text("Usage: /confirm_investment <user_id> <amount>")
        return

    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid arguments. Please use numbers for user_id and amount.")
        return

    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM investments WHERE user_id = ? AND amount = ? AND status = "pending" ORDER BY investment_date DESC LIMIT 1', (user_id, amount))
    pending_investment = cursor.fetchone()

    if not pending_investment:
        await update.message.reply_text("No pending investment found with this user_id and amount.")
        conn.close()
        return

    plan = pending_investment[8]

    cursor.execute('''
        UPDATE users
        SET total_invested = total_invested + ?, current_balance = current_balance + ?, plan = ?
        WHERE user_id = ?
    ''', (amount, amount, plan, user_id))

    cursor.execute('UPDATE investments SET status = "confirmed" WHERE id = ?', (pending_investment[0],))

    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Confirmed crypto investment of ${amount:,.2f} for user {user_id}.")

    # Notify the user about the confirmed investment
    try:
        keyboard = [
            [InlineKeyboardButton("📊 View Portfolio", callback_data="view_portfolio")],
            [InlineKeyboardButton("👤 My Profile", callback_data="show_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 **INVESTMENT CONFIRMED!** 🎉\n\n"
                 f"✅ Your crypto investment of ${amount:,.2f} has been confirmed!\n"
                 f"💰 Your portfolio has been updated\n"
                 f"📈 Daily profits are now active\n\n"
                 f"Check your portfolio to see your updated balance and start earning!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Failed to send confirmation notification to user {user_id}: {e}")

    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,))
    referrer_data = cursor.fetchone()
    if referrer_data and referrer_data[0]:
        referrer_id = referrer_data[0]

        cursor.execute('SELECT COUNT(*) FROM investments WHERE user_id = ? AND status = "confirmed"', (user_id,))
        confirmed_investments = cursor.fetchone()[0]

        if confirmed_investments == 1:
            bonus = 100.00

            cursor.execute('''
                UPDATE users
                SET current_balance = current_balance + ?
                WHERE user_id = ?
            ''', (bonus, referrer_id))

            cursor.execute('''
                UPDATE referrals
                SET bonus_amount = bonus_amount + ?
                WHERE referrer_id = ? AND referred_id = ?
            ''', (bonus, referrer_id, user_id))

            conn.commit()

            try:
                keyboard = [
                    [InlineKeyboardButton("📊 View Portfolio", callback_data="view_portfolio")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=referrer_id,
                    text=f"🎁 **REFERRAL BONUS!** 🎁\n\n"
                         f"Your referred friend has made their first investment!\n"
                         f"💰 You received a ${bonus:,.2f} bonus!\n"
                         f"📊 Check your portfolio to see the update",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Failed to send referral bonus message to {referrer_id}: {e}")

    conn.close()

async def confirm_stock_investment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm a pending stock investment"""
    user = update.effective_user
    
    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Access denied. Admin only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /confirm_stock <user_id> <amount>\n"
            "Example: /confirm_stock 12345 5000"
        )
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid format. Use: /confirm_stock <user_id> <amount>")
        return
    
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    # Get the latest pending stock investment for this user with matching amount
    cursor.execute('''
        SELECT id, stock_ticker, purchase_price, amount_invested_usd
        FROM stock_investments 
        WHERE user_id = ? AND amount_invested_usd = ? AND status = 'pending'
        ORDER BY investment_date DESC LIMIT 1
    ''', (user_id, amount))
    
    investment = cursor.fetchone()
    
    if not investment:
        await update.message.reply_text(
            f"❌ No pending stock investment found for User ID {user_id} with amount ${amount:,.2f}"
        )
        conn.close()
        return
    
    inv_id, ticker, purchase_price, invested_amount = investment
    
    # Confirm the investment
    cursor.execute('''
        UPDATE stock_investments 
        SET status = 'confirmed', confirmed_date = CURRENT_TIMESTAMP, confirmed_by = ?
        WHERE id = ?
    ''', (user.id, inv_id))
    
    # Update user stats
    cursor.execute('''
        UPDATE users 
        SET total_invested = total_invested + ?
        WHERE user_id = ?
    ''', (amount, user_id))
    
    conn.commit()
    conn.close()
    
    # Send confirmation to user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ STOCK INVESTMENT CONFIRMED!\n\n"
                 f"📈 Stock: {ticker.upper()}\n"
                 f"💰 Amount Invested: ${amount:,.2f}\n"
                 f"📊 Purchase Price: ${purchase_price:,.2f}\n"
                 f"📅 Investment Date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                 f"🎯 Your portfolio has been updated!\n"
                 f"📱 View your portfolio with /portfolio"
        )
    except Exception as e:
        logging.error(f"Failed to notify user {user_id} about stock investment: {e}")
    
    # Send confirmation to admin
    await update.message.reply_text(
        f"✅ STOCK INVESTMENT CONFIRMED!\n\n"
        f"👤 User: {user_id}\n"
        f"📈 Stock: {ticker.upper()}\n"
        f"💰 Amount: ${amount:,.2f}\n"
        f"📊 Price: ${purchase_price:,.2f}\n"
        f"📅 Confirmed: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"⚡ Portfolio updated successfully."
    )
    
    logging.info(f"Admin {user.id} confirmed stock investment {inv_id} for user {user_id}: ${amount} in {ticker}")
    # --- Helper function for stock display ---
async def _display_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_list: List[str], title: str, start_index: int = 0):
    query = update.callback_query
    await query.answer()

    stocks_to_show = stock_list[start_index:start_index + 5]
    stocks_info = get_stocks_info(stocks_to_show)
    
    if not stocks_info:
        await query.message.edit_text("❌ Could not fetch stock data at the moment. Please try again later.")
        return
        
    stock_text = f"📊 {title}\n\n"
    
    keyboard = []
    
    for stock in stocks_info:
        stock_text += f"• {stock['name']} ({stock['ticker']}): {stock['price']} {stock['change']}\n\n"
        keyboard.append([InlineKeyboardButton(f"Buy {stock['ticker']}", callback_data=f"buy_stock_{stock['ticker']}")])
    
    navigation_buttons = []
    callback_base = title.replace(' ', '_').lower()
    
    if start_index > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"prev_{callback_base}_{start_index-5}"))
    
    navigation_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{callback_base}_{start_index}"))

    if start_index + 5 < len(stock_list):
        navigation_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"next_{callback_base}_{start_index+5}"))
    
    keyboard.append(navigation_buttons)
    
    # Add a button to switch between tech and non-tech
    if "Tech" in title:
        keyboard.append([InlineKeyboardButton("Non-Tech Stocks", callback_data="show_non_tech_stocks_page_0")])
    else:
        keyboard.append([InlineKeyboardButton("Tech Stocks", callback_data="show_stocks_page_0")])

    keyboard.append([InlineKeyboardButton("🔙 Invest Options", callback_data="invest_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        stock_text.strip(),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def confirm_stock_sale_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm a pending stock sale request"""
    user = update.effective_user
    
    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Access denied. Admin only.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /confirm_stock_sale <user_id> <stock_investment_id>\n"
            "Example: /confirm_stock_sale 12345 67"
        )
        return
    
    try:
        user_id = int(context.args[0])
        stock_investment_id = int(context.args[1])
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid format. Use: /confirm_stock_sale <user_id> <stock_investment_id>")
        return
    
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    # Get the stock sale details
    cursor.execute('''
        SELECT ss.id, ss.shares_sold, ss.sale_price, ss.total_value, ss.wallet_address, ss.user_id,
               si.stock_ticker, si.amount_invested_usd, si.purchase_price
        FROM stock_sales ss
        JOIN stock_investments si ON ss.stock_investment_id = si.id
        WHERE ss.user_id = ? AND ss.stock_investment_id = ? AND ss.status = 'pending'
    ''', (user_id, stock_investment_id))
    
    sale_data = cursor.fetchone()
    
    if not sale_data:
        await update.message.reply_text(
            f"❌ No pending stock sale found for User ID {user_id} and Stock Investment ID {stock_investment_id}"
        )
        conn.close()
        return
    
    sale_id, shares_sold, sale_price, total_value, wallet_address, sale_user_id, ticker, amount_invested, purchase_price = sale_data
    
    # Calculate remaining shares and update stock investment
    original_shares = amount_invested / purchase_price
    remaining_shares = original_shares - shares_sold
    
    if remaining_shares > 0:
        # Update remaining investment with new amount
        remaining_value = remaining_shares * purchase_price
        cursor.execute('''
            UPDATE stock_investments 
            SET amount_invested_usd = ?, status = 'confirmed'
            WHERE id = ?
        ''', (remaining_value, stock_investment_id))
    else:
        # Delete the investment if all shares sold
        cursor.execute('DELETE FROM stock_investments WHERE id = ?', (stock_investment_id,))
    
    # Confirm the stock sale
    cursor.execute('''
        UPDATE stock_sales 
        SET status = 'confirmed', processed_by = ?, processed_date = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (user.id, sale_id))
    
    # Update user's balance (add sale proceeds)
    cursor.execute('''
        UPDATE users 
        SET current_balance = current_balance + ?, profit_earned = profit_earned + ?
        WHERE user_id = ?
    ''', (total_value, total_value, user_id))
    
    conn.commit()
    conn.close()
    
    # Send confirmation to user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ STOCK SALE CONFIRMED!\n\n"
                 f"📈 Stock: {ticker.upper()}\n"
                 f"📊 Shares Sold: {shares_sold:.2f}\n"
                 f"💰 Sale Price: ${sale_price:,.2f} per share\n"
                 f"💸 Total Received: ${total_value:,.2f}\n\n"
                 f"💳 Funds have been credited to your account balance.\n"
                 f"📱 Check your portfolio for updated balance.\n\n"
                 f"⏰ Processed: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        )
    except Exception as e:
        logging.error(f"Failed to notify user {user_id} about stock sale: {e}")
    
    # Send confirmation to admin
    await update.message.reply_text(
        f"✅ STOCK SALE CONFIRMED!\n\n"
        f"👤 User: {user_id}\n"
        f"📈 Stock: {ticker.upper()}\n"
        f"📊 Shares Sold: {shares_sold:.2f}\n"
        f"💰 Sale Price: ${sale_price:,.2f}\n"
        f"💸 Total Value: ${total_value:,.2f}\n"
        f"💳 Wallet: `{wallet_address}`\n"
        f"📅 Processed: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"⚡ Funds credited to user balance.\n"
        f"📊 Stock investment updated with remaining shares."
        , parse_mode='Markdown'
    )
    
    # Log the transaction
    logging.info(f"Admin {user.id} confirmed stock sale {sale_id} for user {user_id}: {shares_sold} shares of {ticker} for ${total_value:.2f}")

async def confirm_withdrawal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /confirm_withdrawal <user_id>")
        return

    try:
        user_id = int(context.args[0])
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid arguments. Please use a number for user_id.")
        return

    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM withdrawals WHERE user_id = ? AND status = "pending" ORDER BY withdrawal_date DESC LIMIT 1', (user_id,))
    pending_withdrawal = cursor.fetchone()

    if not pending_withdrawal:
        await update.message.reply_text("No pending withdrawal found for this user_id.")
        conn.close()
        return

    amount = pending_withdrawal[2]
    wallet_address = pending_withdrawal[3]
    
    # Update withdrawal status
    cursor.execute('UPDATE withdrawals SET status = "confirmed", processed_by = ? WHERE id = ?', (user.id, pending_withdrawal[0],))

    # Deduct from user's balance
    cursor.execute('UPDATE users SET current_balance = current_balance - ? WHERE user_id = ?', (amount, user_id))

    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Confirmed withdrawal of ${amount:,.2f} for user {user_id}.")

    # Notify the user about the confirmed withdrawal
    try:
        keyboard = [
            [InlineKeyboardButton("📊 View Portfolio", callback_data="view_portfolio")],
            [InlineKeyboardButton("👤 My Profile", callback_data="show_profile")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"🎉 **WITHDRAWAL CONFIRMED!** 🎉\n\n"
                 f"✅ Your withdrawal of ${amount:,.2f} has been confirmed!\n"
                 f"💰 Funds have been sent to: `{wallet_address}`\n"
                 f"📈 Your portfolio balance has been updated\n\n"
                 f"Check your portfolio to see your updated balance!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Failed to send withdrawal confirmation notification to user {user_id}: {e}")
    
    
# --- Helper function for stock display ---
async def _display_stocks(update: Update, context: ContextTypes.DEFAULT_TYPE, stock_list: List[str], title: str, start_index: int = 0):
    query = update.callback_query
    await query.answer()

    stocks_to_show = stock_list[start_index:start_index + 5]
    stocks_info = get_stocks_info(stocks_to_show)

    if not stocks_info:
        await query.message.edit_text("❌ Could not fetch stock data at the moment. Please try again later.")
        return

    stock_text = f"📊 {title}\n\n"

    keyboard = []

    for stock in stocks_info:
        stock_text += f"• {stock['name']} ({stock['ticker']}): {stock['price']} {stock['change']}\n\n"
        keyboard.append([InlineKeyboardButton(f"Buy {stock['ticker']}", callback_data=f"buy_stock_{stock['ticker']}")])

    navigation_buttons = []
    callback_base = title.replace(' ', '_').lower()

    if start_index > 0:
        navigation_buttons.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"prev_{callback_base}_{start_index - 5}"))

    navigation_buttons.append(InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{callback_base}_{start_index}"))

    if start_index + 5 < len(stock_list):
        navigation_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"next_{callback_base}_{start_index + 5}"))

    keyboard.append(navigation_buttons)

    # Add a button to switch between tech and non-tech
    if "Tech" in title:
        keyboard.append([InlineKeyboardButton("Non-Tech Stocks", callback_data="show_non_tech_stocks_page_0")])
    else:
        keyboard.append([InlineKeyboardButton("Tech Stocks", callback_data="show_stocks_page_0")])

    keyboard.append([InlineKeyboardButton("🔙 Invest Options", callback_data="invest_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(
        stock_text.strip(),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
# --- LEADERBOARD FUNCTIONS ---
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the leaderboard to users"""
    await show_leaderboard(update, context)

async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the motivating dummy leaderboard"""
    query = update.callback_query if update.callback_query else None
    
    # Get dummy leaderboard data
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, rank_position, total_earnings, weekly_earnings, success_rate 
        FROM leaderboard_dummy 
        ORDER BY rank_position ASC 
        LIMIT 10
    ''')
    leaderboard_data = cursor.fetchall()
    conn.close()
    
    if not leaderboard_data:
        text = "🏆 LEADERBOARD\n\nNo leaderboard data available yet.\nStart investing to climb the ranks!"
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await query.message.edit_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return
    
    # Create engaging leaderboard display
    leaderboard_text = "🏆 TOP TRADERS LEADERBOARD\n\n"
    leaderboard_text += "🚀 *See what top investors are earning!*\n\n"
    
    rank_emojis = ["🥇", "🥈", "🥉", "👨‍💼", "👩‍💼", "💎", "🔥", "⚡", "🌟", "🎯"]
    
    for i, (username, rank_pos, total_earnings, weekly_earnings, success_rate) in enumerate(leaderboard_data[:8], 1):
        # Clean and format username
        display_name = username.replace('_', ' ')[:18]
        if len(username) > 18:
            display_name += "..."
        
        emoji = rank_emojis[i-1] if i <= len(rank_emojis) else f"{i}."
        
        # Add some motivational flair
        profit_emoji = "📈" if weekly_earnings > 5000 else "📊"
        
        leaderboard_text += f"{emoji} *{display_name}*\n"
        leaderboard_text += f"   💰 Total: ${total_earnings:,.0f}\n"
        leaderboard_text += f"   {profit_emoji} This Week: +${weekly_earnings:,.0f}\n"
        leaderboard_text += f"   🎯 Success Rate: {success_rate:.1f}%\n\n"
    
    # Add motivational message
    leaderboard_text += "💡 *Join the ranks of successful traders!*\n"
    leaderboard_text += "Start investing today and watch your profits grow! 🚀"
    
    # Create engaging keyboard
    keyboard = [
        [InlineKeyboardButton("💰 Start Investing", callback_data="invest_menu")],
        [InlineKeyboardButton("👥 View Full Leaderboard", callback_data="leaderboard_full")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.message.edit_text(leaderboard_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(leaderboard_text.strip(), reply_markup=reply_markup, parse_mode='Markdown')

# --- ADMIN CONFIRMATION FUNCTIONS ---
async def confirm_investment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to confirm crypto investment"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /confirm_investment <user_id> <amount>")
            return
        
        user_id = int(args[0])
        amount = float(args[1])
        
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        # Get latest pending investment for this user
        cursor.execute('''
            SELECT id, crypto_type, plan FROM investments 
            WHERE user_id = ? AND status = 'pending' 
            ORDER BY investment_date DESC LIMIT 1
        ''', (user_id,))
        investment = cursor.fetchone()
        
        if not investment:
            await update.message.reply_text(f"❌ No pending investment found for user {user_id}")
            conn.close()
            return
        
        investment_id, crypto_type, plan = investment
        
        # Update investment status
        cursor.execute('''
            UPDATE investments SET status = 'confirmed' WHERE id = ?
        ''', (investment_id,))
        
        # Update user investment and balance
        cursor.execute('''
            UPDATE users 
            SET total_invested = total_invested + ?, 
                current_balance = current_balance + ?,
                plan = ?
            WHERE user_id = ?
        ''', (amount, amount, plan, user_id))
        
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Investment Confirmed!*\n\n"
                     f"💰 Amount: ${amount:,.2f}\n"
                     f"💎 Plan: {plan}\n"
                     f"📊 Your portfolio has been updated!\n\n"
                     f"Check your portfolio with /portfolio",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Could not notify user {user_id}: {e}")
        
        await update.message.reply_text(
            f"✅ Investment confirmed for user {user_id}\n"
            f"💰 Amount: ${amount:,.2f}\n"
            f"💎 Plan: {plan}"
        )
        
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid command format. Use: /confirm_investment <user_id> <amount>")

async def confirm_stock_investment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to confirm stock investment"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /confirm_stock <user_id> <amount>")
            return
        
        user_id = int(args[0])
        amount = float(args[1])
        
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        # Get latest pending stock investment
        cursor.execute('''
            SELECT id, stock_ticker FROM stock_investments 
            WHERE user_id = ? AND status = 'pending' 
            ORDER BY investment_date DESC LIMIT 1
        ''', (user_id,))
        stock_investment = cursor.fetchone()
        
        if not stock_investment:
            await update.message.reply_text(f"❌ No pending stock investment found for user {user_id}")
            conn.close()
            return
        
        stock_id, ticker = stock_investment
        
        # Update stock investment status
        cursor.execute('''
            UPDATE stock_investments SET status = 'confirmed' WHERE id = ?
        ''', (stock_id,))
        
        # Update user balance (for stocks, we just mark as confirmed, no balance change)
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Stock Investment Confirmed!*\n\n"
                     f"📈 Stock: {ticker}\n"
                     f"💰 Amount: ${amount:,.2f}\n"
                     f"📊 Your portfolio has been updated!\n\n"
                     f"Check your portfolio with /portfolio",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Could not notify user {user_id}: {e}")
        
        await update.message.reply_text(
            f"✅ Stock investment confirmed for user {user_id}\n"
            f"📈 Stock: {ticker}\n"
            f"💰 Amount: ${amount:,.2f}"
        )
        
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid command format. Use: /confirm_stock <user_id> <amount>")

async def confirm_withdrawal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to confirm withdrawal"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        args = context.args
        if len(args) != 1:
            await update.message.reply_text("Usage: /confirm_withdrawal <user_id>")
            return
        
        user_id = int(args[0])
        
        conn = sqlite3.connect('trading_bot.db')
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
            conn.close()
            return
        
        withdrawal_id, amount, wallet_address = withdrawal
        
        # Update withdrawal status and mark as processed by admin
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
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Withdrawal Confirmed!*\n\n"
                     f"💰 Amount: ${amount:,.2f}\n"
                     f"💸 To: `{wallet_address}`\n"
                     f"⏰ Processing: Within 24 hours\n\n"
                     f"Funds will be sent to your wallet shortly!",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Could not notify user {user_id}: {e}")
        
        await update.message.reply_text(
            f"✅ Withdrawal confirmed for user {user_id}\n"
            f"💰 Amount: ${amount:,.2f}\n"
            f"💸 Wallet: `{wallet_address}`"
        )
        
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid command format. Use: /confirm_withdrawal <user_id>")

async def confirm_stock_sale_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to confirm stock sale"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return
    
    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text("Usage: /confirm_stock_sale <user_id> <stock_investment_id>")
            return
        
        user_id = int(args[0])
        stock_investment_id = int(args[1])
        
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        # Get the stock sale
        cursor.execute('''
            SELECT ss.id, ss.shares_sold, ss.total_value, si.stock_ticker 
            FROM stock_sales ss
            JOIN stock_investments si ON ss.stock_investment_id = si.id
            WHERE ss.user_id = ? AND ss.stock_investment_id = ? AND ss.status = 'pending'
        ''', (user_id, stock_investment_id))
        stock_sale = cursor.fetchone()
        
        if not stock_sale:
            await update.message.reply_text(f"❌ No pending stock sale found for user {user_id}")
            conn.close()
            return
        
        sale_id, shares_sold, total_value, ticker = stock_sale
        
        # Update sale status
        cursor.execute('''
            UPDATE stock_sales 
            SET status = 'confirmed', processed_by = ? 
            WHERE id = ?
        ''', (update.effective_user.id, sale_id))
        
        # Update stock investment - reduce shares (simplified)
        cursor.execute('''
            UPDATE stock_investments 
            SET amount_invested_usd = amount_invested_usd - ?
            WHERE id = ?
        ''', (total_value, stock_investment_id))
        
        # Add to user balance
        cursor.execute('''
            UPDATE users SET current_balance = current_balance + ? WHERE user_id = ?
        ''', (total_value, user_id))
        
        conn.commit()
        conn.close()
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *Stock Sale Confirmed!*\n\n"
                     f"📈 Stock: {ticker}\n"
                     f"💰 Sold: {shares_sold} shares\n"
                     f"💸 Received: ${total_value:,.2f}\n\n"
                     f"Funds have been added to your balance!\n"
                     f"Check your portfolio with /portfolio",
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Could not notify user {user_id}: {e}")
        
        await update.message.reply_text(
            f"✅ Stock sale confirmed for user {user_id}\n"
            f"📈 Stock: {ticker}\n"
            f"💰 Value: ${total_value:,.2f}\n"
            f"👤 Shares: {shares_sold}"
        )
        
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Invalid command format. Use: /confirm_stock_sale <user_id> <stock_investment_id>")

# --- REFRESH DUMMY LEADERBOARD ---
def refresh_dummy_leaderboard():
    """Periodically refresh dummy leaderboard with slight variations"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    # Get current data
    cursor.execute('SELECT username, total_earnings, weekly_earnings FROM leaderboard_dummy ORDER BY rank_position ASC')
    current_data = cursor.fetchall()
    
    # Add small random growth to motivate users
    for i, (username, total, weekly) in enumerate(current_data[:5]):  # Top 5 get bigger gains
        growth = random.uniform(0.02, 0.08)  # 2-8% growth
        new_total = total * (1 + growth)
        new_weekly = weekly * (1 + random.uniform(0.1, 0.3))  # 10-30% weekly variation
        
        cursor.execute('''
            UPDATE leaderboard_dummy 
            SET total_earnings = ?, weekly_earnings = ?
            WHERE username = ?
        ''', (new_total, new_weekly, username))
    
    conn.commit()
    conn.close()

# --- Callback Handlers ---
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # ADMIN PANEL HANDLING
    if data == "admin_investments":
        await show_pending_investments(update, context)
        return
    elif data == "admin_withdrawals":
        await show_pending_withdrawals(update, context)
        return
    elif data == "admin_stock_sales":
        await show_pending_stock_sales(update, context)
        return
    elif data == "admin_stock_investments":
        await show_pending_stock_investments(update, context)
        return
    elif data == "admin_user_stats":
        await show_user_stats(update, context)
        return
    elif data == "admin_broadcast":
        await query.edit_message_text(
            "📢 Enter the message to broadcast to all users:\n\n"
            "Reply with your message, then use /broadcast to send."
        )
        context.user_data['awaiting_broadcast_message'] = True
        return
    
    # ... rest of your existing button_callback code
    user = query.from_user

    if query.data == "main_menu":
        await show_main_menu(update, context, user)

    elif query.data == "invest_menu":
        await invest_command(update, context)

    elif query.data == "show_prices":
        await display_live_prices_menu(update, context)

    elif query.data == "sell_stocks":
        # This callback correctly shows the sell menu.
        await handle_sell_stocks(update, context)

    elif query.data.startswith("sell_stock_"):
        stock_id = int(query.data.split("_")[-1])
        await handle_individual_stock_sale(update, context, stock_id)
        
    # --- Live Prices Handlers ---
    elif query.data.startswith("live_crypto_prices_"):
        start_index = int(query.data.split("_")[-1])
        await display_crypto_prices(update, context, start_index)

    elif query.data.startswith("live_stock_prices_"):
        start_index = int(query.data.split("_")[-1])
        await display_stock_prices(update, context, start_index)

    elif query.data == "crypto_plans":
        keyboard = [
            [InlineKeyboardButton("🥉 Core Plan ($1K-$15K)", callback_data="plan_core")],
            [InlineKeyboardButton("🥈 Growth Plan ($20K-$80K)", callback_data="plan_growth")],
            [InlineKeyboardButton("🥇 Alpha Plan ($100K+)", callback_data="plan_alpha")],
            [InlineKeyboardButton("🔙 Invest Options", callback_data="invest_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        plans_text = """
💰 SELECT YOUR INVESTMENT PLAN

🥉 CORE PLAN - Perfect for Beginners
• Range: $1,000 - $15,000
• Weekly Return: 10%
• Annual ROI: ~520%

🥈 GROWTH PLAN - Balanced Approach
• Range: $20,000 - $80,000
• Weekly Return: 15%
• Annual ROI: ~780%

🥇 ALPHA PLAN - Maximum Returns
• Range: $100,000+
• Weekly Return: 20%
• Annual ROI: ~1040%

💎 All plans include:
✅ Automated daily compounding
✅ Anytime withdrawals
✅ Multi-crypto support
✅ Professional management
        """
        await query.message.edit_text(plans_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data.startswith("plan_"):
        plan_type = query.data.split("_")[1]

        if plan_type == "core":
            plan_info = InvestmentPlan.CORE.value
        elif plan_type == "growth":
            plan_info = InvestmentPlan.GROWTH.value
        else:
            plan_info = InvestmentPlan.ALPHA.value

        keyboard = [
            [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data=f"crypto_btc_{plan_type}")],
            [InlineKeyboardButton("💎 Ethereum (ETH)", callback_data=f"crypto_eth_{plan_type}")],
            [InlineKeyboardButton("💵 USDT (TRC20)", callback_data=f"crypto_usdt_{plan_type}")],
            [InlineKeyboardButton("☀️ Solana (SOL)", callback_data=f"crypto_sol_{plan_type}")],
            [InlineKeyboardButton("💙 TON", callback_data=f"crypto_ton_{plan_type}")],
            [InlineKeyboardButton("🔙 Crypto Plans", callback_data="crypto_plans")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        plan_text = f"""
🎯 {plan_info['name'].upper()} SELECTED

💰 Investment Range: ${plan_info['min_amount']:,} - ${plan_info['max_amount']:,}
📈 Daily Return: {plan_info['daily_return'] * 100:.2f}%
📊 Expected Annual ROI: ~{plan_info['daily_return'] * 365 * 100:.0f}%

Choose your preferred cryptocurrency:

Each crypto has 5 rotating wallet addresses for security.
After selection, you'll receive:
• Unique wallet address
• Exact amount to send
• Investment tracking

⚠️ Important:
• Minimum investment applies
• Profits start once minimum reached
• Send exact amount to avoid delays

Select cryptocurrency below: 👇
        """
        await query.message.edit_text(plan_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data.startswith("crypto_"):
        parts = query.data.split("_")
        crypto = parts[1]
        plan_type = parts[2]

        if plan_type == "core":
            plan_info = InvestmentPlan.CORE.value
        elif plan_type == "growth":
            plan_info = InvestmentPlan.GROWTH.value
        else:
            plan_info = InvestmentPlan.ALPHA.value

        wallet_address = get_random_wallet(crypto)
        if not wallet_address:
            await query.message.edit_text("❌ Invalid cryptocurrency selected.")
            return

        context.user_data['awaiting_tx_details'] = {
            'plan_type': plan_type,
            'plan_info': plan_info,
            'crypto': crypto,
            'wallet_address': wallet_address,
            'user_id': user.id
        }

        keyboard = [
            [InlineKeyboardButton("✅ I've Sent Payment", callback_data="confirm_payment")],
            [InlineKeyboardButton("🔙 Back to Plans", callback_data="crypto_plans")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        crypto_text = f"""
💰 INVESTMENT DEPOSIT - {crypto.upper()}

🎯 Plan: {plan_info['name']}
💎 Cryptocurrency: {crypto.upper()}
📈 Daily Return: {plan_info['daily_return'] * 100:.2f}%

🔑 PAYMENT DETAILS:

Wallet Address:
`{wallet_address}`
Tap address to copy

💰 Investment Range:
• Minimum: ${plan_info['min_amount']:,} USD
• Maximum: ${plan_info['max_amount']:,} USD

⚠️ IMPORTANT INSTRUCTIONS:

1️⃣ Send your desired investment amount to the wallet above
2️⃣ Send the EXACT USD equivalent in {crypto.upper()}
3️⃣ Click "✅ I've Sent Payment" after sending
4️⃣ Admin will verify and activate your plan

🎯 Example:
• Want to invest $5,000?
• Send $5,000 worth of {crypto.upper()} to the address above

⚡ Your profits start counting once admin confirms your payment!

Click the button below after sending your payment: 👇
        """
        await query.message.edit_text(crypto_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "confirm_payment":
        investment_data = context.user_data.get('awaiting_tx_details')
        if not investment_data:
            await query.message.edit_text("❌ Investment session expired. Please start again.")
            return

        keyboard = [
            [InlineKeyboardButton("🔙 Back", callback_data="crypto_plans")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            "💸 PAYMENT CONFIRMATION\n\n"
            "Please reply with the following information:\n\n"
            "Format:\n"
            "`Amount: $X,XXX`\n"
            "`Transaction ID: [your_tx_hash]`\n"
            "`Network: [network_name]`\n\n"
            "Example:\n"
            "`Amount: $5,000`\n"
            "`Transaction ID: 0x1234...abcd`\n"
            "`Network: Bitcoin`\n\n"
            "This helps our admin verify your payment quickly!",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        context.user_data['awaiting_payment_details'] = True

    # --- Stock Investment Handlers ---
    elif query.data.startswith("show_stocks_page_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, TECH_STOCKS, "Top Tech Stocks", start_index)

    elif query.data.startswith("show_non_tech_stocks_page_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, NON_TECH_STOCKS, "Non-Tech Stocks", start_index)

    elif query.data.startswith("next_top_tech_stocks_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, TECH_STOCKS, "Top Tech Stocks", start_index)

    elif query.data.startswith("next_non_tech_stocks_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, NON_TECH_STOCKS, "Non-Tech Stocks", start_index)

    elif query.data.startswith("prev_top_tech_stocks_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, TECH_STOCKS, "Top Tech Stocks", start_index)

    elif query.data.startswith("prev_non_tech_stocks_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, NON_TECH_STOCKS, "Non-Tech Stocks", start_index)

    elif query.data.startswith("refresh_top_tech_stocks_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, TECH_STOCKS, "Top Tech Stocks", start_index)

    elif query.data.startswith("refresh_non_tech_stocks_"):
        start_index = int(query.data.split("_")[-1])
        await _display_stocks(update, context, NON_TECH_STOCKS, "Non-Tech Stocks", start_index)

    elif query.data.startswith("buy_stock_"):
        ticker = query.data.split("_")[2]

        context.user_data['awaiting_stock_shares'] = {
            'ticker': ticker,
            'user_id': user.id
        }

        keyboard = [[InlineKeyboardButton("🔙 Back to Stocks", callback_data="show_stocks_page_0")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            f"📈 BUY {ticker.upper()} - STOCK INVESTMENT\n\n"
            "Please reply with the number of shares you want to buy.\n\n"
            "Example: `10`\n\n"
            "⚠️ Requirements:\n"
            "• Must be a whole number greater than 0",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        context.user_data['awaiting_stock_shares'] = True
        context.user_data['stock_to_buy'] = ticker

    elif query.data == "confirm_stock_payment":
        if context.user_data.get('awaiting_stock_investment'):
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="show_stocks_page_0")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                "💸 PAYMENT CONFIRMATION\n\n"
                "Please reply with the following information:\n"
                "`Amount: $X,XXX`\n"
                "`Transaction ID: [your_tx_hash]`\n\n"
                "This helps our admin verify your payment and purchase the stock for you!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            context.user_data['awaiting_stock_payment_details'] = True

    elif query.data == "withdraw_funds":
        await withdraw_command(update, context)

    elif query.data.startswith("withdraw_"):
        if query.data == "withdraw_custom":
            keyboard = [[InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw_funds")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                "💰 CUSTOM WITHDRAWAL AMOUNT\n\n"
                "Please reply with your desired withdrawal amount.\n\n"
                "Format: `$1000` or `1000`\n\n"
                "⚠️ Requirements:\n"
                "• Minimum: $10\n"
                "• Maximum: Your available balance\n"
                "• Must be whole numbers",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            context.user_data['awaiting_withdraw_amount'] = True
        else:
            percent_str = query.data.split("_")[1]
            amount = context.user_data['withdraw_options'].get(f"{percent_str}%")
            if amount is None:
                await query.message.edit_text("❌ Invalid withdrawal option. Please try again.")
                return

            keyboard = [[InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw_funds")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                f"💸 WITHDRAWAL REQUEST: ${amount:,.2f}\n\n"
                "Please reply with your USDT wallet address (TRC20)\n\n"
                "⚠️ Important:\n"
                "• Only TRC20 USDT addresses\n"
                "• Double-check your address\n"
                "• Wrong address = lost funds\n\n"
                "Send your wallet address below: 👇",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            context.user_data['pending_withdrawal'] = {
                'amount': amount,
                'user_id': user.id
            }

    elif query.data == "referral_info":
        user_data = get_user_from_db(user.id)
        if user_data:
            referral_code = user_data[11]

            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(bonus_amount), 0)
                FROM referrals WHERE referrer_id = ?
            ''', (user.id,))
            referral_count, total_bonus = cursor.fetchone()
            conn.close()

            referral_text = f"""
👥 REFERRAL PROGRAM - EARN 5% COMMISSION

🎁 Your Referral Code: `{referral_code}`

📊 Your Referral Stats:
• Total Referrals: {referral_count}
• Total Earned: ${total_bonus:.2f}

💰 How It Works:
1. Share your referral code with friends
2. They use code when registering: `/start {referral_code}`
3. When they invest, you earn 5% commission
4. Commission paid instantly to your balance

🚀 Example:
• Friend invests $1,000
• You earn $50 commission
• They start earning daily profits too!

📢 Share Your Code:
"Join Alpha Vault and start earning daily crypto profits! Use my code: `{referral_code}`"

💎 Benefits for Your Referrals:
• Professional portfolio management
• Daily automated profits
• Instant withdrawals
• Multi-crypto support
            """
            keyboard = [
                [InlineKeyboardButton("📢 Share Referral Link", switch_inline_query=f"Join Alpha Vault and start earning daily crypto profits! Use my code: {referral_code}")],
                [InlineKeyboardButton("🏆 See Leaderboard", callback_data="show_enhanced_leaderboard")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.edit_text(referral_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "view_portfolio":
        await portfolio_command(update, context)

    elif query.data == "refresh_portfolio":
        calculate_user_profits()
        await portfolio_command(update, context)
    
    elif query.data == "show_portfolio":  # ADD THIS LINE
        await portfolio_command(update, context)  # AND THIS LINE

    elif query.data == "help":
        help_text = """
📖 HELP & SUPPORT

Welcome to The Alpha Vault! We're here to help.

Common Questions:
• How to Invest?
  Use the Invest button, choose a plan, and send funds to the provided wallet address.

• How to Withdraw?
  Use the Withdraw button. You can withdraw your current balance anytime.

• How are Profits Calculated?
  Your profits are calculated daily based on your total invested amount and your plan's daily return rate.

• Is it Safe?
  Yes. All transactions are securely handled. Your funds are professionally managed.

Contact Support:
For any issues, please message our support team.
"""
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "show_profile":
        await profile_command(update, context)

    elif query.data == "show_enhanced_leaderboard":
        await leaderboard_command(update, context)
    
    elif query.data == "show_leaderboard" or query.data == "show_enhanced_leaderboard":
        await leaderboard_command(update, context)

    elif query.data.startswith("admin_"):
        if user.id not in ADMIN_USER_IDS:
            await query.answer("❌ Unauthorized access.", show_alert=True)
            return

        action = query.data.split("_")[1]

        if action == "investments":
            try:
                conn = sqlite3.connect('trading_bot.db')
                cursor = conn.cursor()

                # Check if notes column exists
                cursor.execute("PRAGMA table_info(investments)")
                columns = [column[1] for column in cursor.fetchall()]
                has_notes = 'notes' in columns

                if has_notes:
                    cursor.execute('SELECT user_id, amount, crypto_type, investment_date, notes FROM investments WHERE status = "pending" ORDER BY investment_date DESC')
                else:
                    cursor.execute('SELECT user_id, amount, crypto_type, investment_date FROM investments WHERE status = "pending" ORDER BY investment_date DESC')
                pending_crypto = cursor.fetchall()

                cursor.execute('SELECT user_id, amount_invested_usd, stock_ticker, investment_date FROM stock_investments WHERE status = "pending" ORDER BY investment_date DESC')
                pending_stocks = cursor.fetchall()
                conn.close()

                message_text = "💰 PENDING INVESTMENTS\n\n"
                if pending_crypto or pending_stocks:
                    if pending_crypto:
                        message_text += "📸 Crypto:\n"
                        for row in pending_crypto:
                            if has_notes and len(row) == 5:
                                uid, amt, c, date, notes = row
                                message_text += f"- User: {uid}, Amount: ${amt:,.2f}, Type: {c.upper()}\n"
                                if notes:
                                    message_text += f"  Note: {notes}\n"
                            else:
                                uid, amt, c, date = row
                                message_text += f"- User: {uid}, Amount: ${amt:,.2f}, Type: {c.upper()}\n"
                            message_text += f"  `/confirm_investment {uid} {amt}`\n"
                    if pending_stocks:
                        message_text += "\n📸 Stocks:\n"
                        for uid, amt, t, date in pending_stocks:
                            message_text += f"- User: {uid}, Amount: ${amt:,.2f}, Ticker: {t.upper()}\n  `/confirm_stock {uid} {amt}`\n"
                else:
                    message_text += "No pending investments."

                keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Error in investments admin function: {e}")
                await query.message.edit_text("❌ Error loading investments. Please try again.")

        elif action == "withdrawals":
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount, wallet_address FROM withdrawals WHERE status = "pending" ORDER BY withdrawal_date DESC')
            pending_withdrawals = cursor.fetchall()
            conn.close()

            message_text = "💸 PENDING WITHDRAWALS\n\n"
            if pending_withdrawals:
                for uid, amt, addr in pending_withdrawals:
                    message_text += f"- User: {uid}, Amount: ${amt:,.2f}\n  Address: `{addr}`\n  `/confirm_withdrawal {uid}`\n"
            else:
                message_text += "No pending withdrawals."

            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

        elif action == "user_stats":
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(user_id) FROM users')
            total_users = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(user_id) FROM users WHERE total_invested > 0')
            active_investors = cursor.fetchone()[0]
            conn.close()

            stats_text = (
                f"📊 USER STATISTICS\n\n"
                f"• Total Users: {total_users}\n"
                f"• Active Investors: {active_investors}\n"
            )
            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(stats_text, reply_markup=reply_markup)
        
        elif action == "stock_sales":
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ss.user_id, ss.shares_sold, ss.sale_price, ss.total_value, 
                    ss.wallet_address, si.stock_ticker, ss.stock_investment_id
                FROM stock_sales ss
                JOIN stock_investments si ON ss.stock_investment_id = si.id
                WHERE ss.status = "pending" 
                ORDER BY ss.sale_date DESC
            ''')
            pending_sales = cursor.fetchall()
            conn.close()

            message_text = "📈 PENDING STOCK SALES\n\n"
            if pending_sales:
                for uid, shares, price, value, addr, ticker, stock_id in pending_sales:
                    message_text += f"- User: {uid}, Stock: {ticker.upper()}\n"
                    message_text += f"  Shares: {shares}, Value: ${value:.2f}\n"
                    message_text += f"  Address: `{addr}`\n"
                    message_text += f"  `/confirm_stock_sale {uid} {stock_id}`\n\n"
            else:
                message_text += "No pending stock sales."

            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        elif action == "admin_stock_investments":
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT si.user_id, si.amount_invested_usd, si.stock_ticker, si.id
                FROM stock_investments si
                WHERE si.status = 'pending'
                ORDER BY si.investment_date DESC
            ''')
            pending_stocks = cursor.fetchall()
            conn.close()

            message_text = "📈 PENDING STOCK INVESTMENTS\n\n"
            if pending_stocks:
                for uid, amount, ticker, stock_id in pending_stocks:
                    message_text += f"- User: {uid}, Stock: {ticker}\n"
                    message_text += f"  Amount: ${amount:.2f}\n"
                    message_text += f"  `/confirm_stock {uid} {amount}`\n\n"
            else:
                message_text += "No pending stock investments."

            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

        elif action == "broadcast":
            context.user_data['awaiting_broadcast_message'] = True
            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text("📣 Please reply with the message you want to broadcast to all users.", reply_markup=reply_markup)
        elif action == "broadcast":
            context.user_data['awaiting_broadcast_message'] = True
            keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text("📣 Please reply with the message you want to broadcast to all users.", reply_markup=reply_markup)
        
        elif action == "leaderboard":
            await show_leaderboard(update, context)
            
        elif action == "leaderboard_full":
            await show_full_leaderboard(update, context, 0)
            
        elif action.startswith("leaderboard_full_"):
            try:
                start_index = int(action.split("_")[2])
                await show_full_leaderboard(update, context, start_index)
            except (ValueError, IndexError):
                await show_full_leaderboard(update, context, 0)
        elif data == 'show_history':
            await show_transaction_history(update, context)
            
        elif action == "panel":
            await admin_command(update, context)
        

# --- Message Handlers for user replies ---
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message_text = update.message.text
    if user.id in ADMIN_USER_IDS:
        if message_text == "📉 Pending Stock Sales":
            await show_pending_stock_sales(update, context)
            return
        elif message_text == "📈 Pending Stock Investments":
            await show_pending_stock_investments(update, context)
            return
        elif message_text == "👥 User Stats":
            await show_user_stats(update, context)
            return
        elif message_text == "📢 Broadcast Message":
            await update.message.reply_text(
                "📢 Enter the message to broadcast to all users:",
                reply_markup=InlineKeyboardMarkup()  # Optional: Hide keyboard during input
            )
            context.user_data['awaiting_broadcast_message'] = True
            return
        elif message_text == "⬅️ Close Panel":
            await update.message.reply_text("Admin panel closed.", reply_markup=InlineKeyboardMarkup())
            return
        if user.id in ADMIN_USER_IDS:
         if await handle_admin_balance_operations(update, context, message_text):
            return
        # Add similar elifs for "🤑 Pending Investments" and "💸 Pending Withdrawals" if they are also not working
        # Example for Pending Investments (crypto):
        # elif message_text == "🤑 Pending Investments":
        #     await show_pending_investments(update, context)  # Define this function similarly if missing

    # REGISTRATION HANDLING
    if context.user_data.get('registration_step') == REGISTER_NAME:
        full_name = message_text.strip()
        context.user_data['full_name'] = full_name
        context.user_data['registration_step'] = REGISTER_EMAIL
        await update.message.reply_text("Great! Now please provide your email address:")
        return

    elif context.user_data.get('registration_step') == REGISTER_EMAIL:
        email = message_text.strip()
        if '@' not in email:
            await update.message.reply_text("Please provide a valid email address:")
            return

        referred_by_id = context.user_data.get('referred_by_id')
        create_or_update_user(
            user.id, user.username, user.first_name,
            context.user_data['full_name'], email, referred_by_id
        )

        context.user_data.pop('registration_step', None)
        context.user_data.pop('full_name', None)
        context.user_data.pop('referred_by_id', None)

        await update.message.reply_text(
            "Registration completed! Welcome to Alpha Vault!\n\n"
            "🏆 *Pro Tip:* Check the leaderboard to see what top traders are earning!"
        )
        await show_main_menu(update, context, user)
        return

    # CRYPTO PAYMENT DETAILS HANDLING
    if context.user_data.get('awaiting_payment_details') and message_text:
        investment_data = context.user_data.get('awaiting_tx_details')
        if not investment_data:
            await update.message.reply_text("❌ Investment session expired. Please start again.")
            return

        lines = message_text.split('\n')
        amount_line = next((line for line in lines if line.strip().lower().startswith('amount:')), None)
        txid_line = next((line for line in lines if line.strip().lower().startswith('transaction id:')), None)
        network_line = next((line for line in lines if line.strip().lower().startswith('network:')), None)

        if not all([amount_line, txid_line, network_line]):
            await update.message.reply_text(
                "❌ Invalid Format.\n"
                "Please make sure you follow the format exactly.\n"
                "`Amount: $X,XXX`\n"
                "`Transaction ID: [your_tx_hash]`\n"
                "`Network: [network_name]`"
            )
            return

        try:
            amount_str = amount_line.split(':')[1].strip().replace('$', '').replace(',', '')
            amount = float(amount_str)
            tx_id = txid_line.split(':')[1].strip()
            network = network_line.split(':')[1].strip()
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Invalid Format. Please check your input and try again.")
            return

        notes = None
        plan_info = investment_data['plan_info']
        if amount < plan_info['min_amount']:
            notes = f"Amount (${amount}) is less than the minimum plan amount (${plan_info['min_amount']}). Needs manual review."
            await notify_admin_investment_flagged(context, user.id, amount, notes)

        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO investments (user_id, amount, crypto_type, transaction_id, wallet_address, plan, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user.id, amount, investment_data['crypto'], tx_id, investment_data['wallet_address'], investment_data['plan_type'], notes))

        conn.commit()
        conn.close()

        await update.message.reply_text(
            "✅ Payment Submitted!\n\n"
            "Your investment request is pending admin confirmation. Please be patient, your portfolio will be updated once verified."
        )

        # Get user details for enhanced notification
        user_data = get_user_from_db(user.id)
        full_name = user_data[3] if user_data and len(user_data) > 3 else 'Not provided'
        email = user_data[4] if user_data and len(user_data) > 4 else 'Not provided'
        
        admin_notification = (
            f"🚨 NEW CRYPTO INVESTMENT 🚨\n\n"
            f"👤 USER VERIFICATION:\n"
            f"• Full Name: {full_name}\n"
            f"• Email: {email}\n"
            f"• Username: @{user.username}\n"
            f"• User ID: [{user.id}](tg://user?id={user.id})\n\n"
            f"💰 INVESTMENT DETAILS:\n"
            f"• Amount: ${amount:,.2f}\n"
            f"• Crypto: {investment_data['crypto'].upper()}\n"
            f"• Transaction ID: `{tx_id}`\n"
            f"• Network: {network}\n"
            f"• Plan: {investment_data['plan_type'].upper()}\n"
            f"• Request Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"⚠️ VERIFY: Transaction details before confirming."
        )
        keyboard.append([
        InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_stock_{investment_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_investment_{investment_id}")
        ])
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        for admin_id in ADMIN_USER_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_notification,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logging.error(f"Failed to send notification to admin {admin_id}: {e}")

        context.user_data.pop('awaiting_payment_details', None)
        context.user_data.pop('awaiting_tx_details', None)
    # STOCK SALE HANDLING
    elif context.user_data.get('pending_stock_sale') and message_text:
        try:
            shares_to_sell = float(message_text.strip())
            sale_data = context.user_data['pending_stock_sale']
            
            if shares_to_sell <= 0 or shares_to_sell > sale_data['total_shares']:
                await update.message.reply_text(
                    f"❌ Invalid amount. Please enter between 0.1 and {sale_data['total_shares']:.2f} shares."
                )
                return
            
            sale_value = shares_to_sell * sale_data['current_price']
            context.user_data['stock_sale_confirmed'] = {
                **sale_data,
                'shares_to_sell': shares_to_sell,
                'sale_value': sale_value
            }
            
            await update.message.reply_text(
                f"💸 STOCK SALE: {sale_data['ticker'].upper()}\n\n"
                f"Shares to Sell: {shares_to_sell}\n"
                f"Current Price: ${sale_data['current_price']:.2f}\n"
                f"Total Sale Value: ${sale_value:.2f}\n\n"
                f"Please provide your USDT wallet address (TRC20):\n\n"
                f"⚠️ Important:\n"
                f"• Only TRC20 USDT addresses\n"
                f"• Double-check your address\n"
                f"• Wrong address = lost funds"
            )
            context.user_data.pop('pending_stock_sale', None)
            
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number of shares.")

    # STOCK SALE WALLET ADDRESS HANDLING  
    elif context.user_data.get('stock_sale_confirmed') and message_text:
        wallet_address = message_text.strip()
        sale_data = context.user_data['stock_sale_confirmed']
        # STOCK SHARES HANDLING
    # STOCK SHARES HANDLING - Make sure this section stores the data correctly
    elif context.user_data.get('awaiting_stock_shares'):
        try:
            num_shares = int(message_text.strip())
            if num_shares <= 0:
                await update.message.reply_text("❌ Please enter a positive whole number for the number of shares.")
                return

            ticker = context.user_data['stock_to_buy']
            stock = yf.Ticker(ticker)
            current_price = stock.info.get('regularMarketPrice')

            if not current_price:
                await update.message.reply_text("❌ Could not get real-time price. Please try another stock.")
                context.user_data.pop('awaiting_stock_shares', None)
                context.user_data.pop('stock_to_buy', None)
                return

            total_cost = num_shares * current_price

            # Store the data with the correct key name
            context.user_data['awaiting_stock_investment'] = {  # This matches the get() above
                'ticker': ticker,
                'purchase_price': current_price,
                'total_cost': total_cost,
                'user_id': user.id
            }
            usdt_address = random.choice(WALLET_ADDRESSES['usdt'])

            keyboard = [
                [InlineKeyboardButton("✅ I've Sent Payment", callback_data="confirm_stock_payment")],
                [InlineKeyboardButton("🔙 Back to Stocks", callback_data="show_stocks_page_0")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"📈 BUY {ticker.upper()} - STOCK INVESTMENT\n\n"
                f"Shares to buy: {num_shares}\n"
                f"Current Price per share: ${current_price:,.2f}\n"
                f"Total Cost: ${total_cost:,.2f}\n\n"
                "Please send the crypto equivalent of the total cost to our USDT (TRC20) wallet address.\n\n"
                "Wallet Address:\n"
                f"`{usdt_address}`\n\n"
                "Tap address to copy, then click 'I've Sent Payment' to provide transaction details.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            context.user_data['awaiting_stock_payment_details'] = True
            context.user_data.pop('awaiting_stock_shares', None)
            context.user_data.pop('stock_to_buy', None)

        except ValueError:
            await update.message.reply_text("❌ That's not a valid number. Please enter a whole number.")
    
    # STOCK PAYMENT DETAILS HANDLING - CORRECTED VERSION
    elif context.user_data.get('awaiting_stock_payment_details') and message_text:
        stock_data = context.user_data.get('awaiting_stock_investment')  # FIXED: Correct variable name

        lines = message_text.split('\n')
        amount_line = next((line for line in lines if line.strip().lower().startswith('amount:')), None)
        txid_line = next((line for line in lines if line.strip().lower().startswith('transaction id:')), None)

        if not all([amount_line, txid_line]):
            await update.message.reply_text("❌ Invalid Format. Please follow the format.")
            return

        try:
            amount_str = amount_line.split(':')[1].strip().replace('$', '').replace(',', '')
            amount = float(amount_str)
            tx_id = txid_line.split(':')[1].strip()
        except (IndexError, ValueError):
            await update.message.reply_text("❌ Invalid Format. Check your input and try again.")
            return

        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO stock_investments (user_id, amount_invested_usd, stock_ticker, purchase_price, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (user.id, amount, stock_data['ticker'], stock_data['purchase_price'], 'pending'))

        investment_id = cursor.lastrowid  # Get the ID for deletion
        conn.commit()
        conn.close()

        # Portfolio button keyboard
        keyboard = [
            [InlineKeyboardButton("💼 View Portfolio", callback_data="view_portfolio")],
            [InlineKeyboardButton("📜 Transaction History", callback_data="show_history")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send confirmation message
        confirmation_message = await update.message.reply_text(
            "✅ Stock Investment Request Submitted!\n\n"
            f"📊 Stock: {stock_data['ticker'].upper()}\n"  # FIXED: Use stock_data
            f"💰 Amount: ${amount:,.2f}\n"
            f"📈 Price: ${stock_data['purchase_price']:.2f}\n"  # FIXED: Use stock_data
            f"📄 Transaction ID: `{tx_id}`\n\n"
            f"⏰ Your portfolio will be updated once confirmed by admin.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Schedule deletion after 40 seconds
        context.job_queue.run_once(
            delete_message,
            40,
            data={
                'chat_id': update.effective_chat.id,
                'message_id': confirmation_message.message_id
            }
        )

        # Admin notification
        admin_notification = (
            f"📈 NEW PENDING STOCK INVESTMENT 📈\n\n"
            f"👤 USER VERIFICATION:\n"
            f"User: [{user.first_name}](tg://user?id={user.id})\n"
            f"• Full Name: {full_name}\n"
            f"• Email: {email}\n"
            f"• Username: @{username}\n"
            f"• User ID: [{user.id}](tg://user?id={user.id})\n\n"
            f"Investment Amount: ${amount:,.2f}\n"
            f"Stock: {stock_data['ticker'].upper()}\n"  # FIXED: Use stock_data
            f"Transaction ID: `{tx_id}`\n\n"
        )
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_stock_'{investment_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_stock_{investment_id}")
        ])
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Add back button after the loop ends
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        for admin_id in ADMIN_USER_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_notification, parse_mode='Markdown')
            except Exception as e:
                logging.error(f"Failed to send notification to admin {admin_id}: {e}")

        context.user_data.pop('awaiting_stock_payment_details', None)
        context.user_data.pop('awaiting_stock_investment', None)  # FIXED: Correct key name
    # WITHDRAWAL AMOUNT HANDLING
    elif context.user_data.get('awaiting_withdraw_amount'):
        try:
            amount = float(message_text.strip().replace('$', '').replace(',', ''))
            user_data = get_user_from_db(user.id)
            # Corrected: Use index 8 for current_balance, not 6
            current_balance = user_data[8]

            if amount < 10 or amount > current_balance:
                await update.message.reply_text(f"❌ Invalid amount. Please enter a number between $10 and your balance of ${current_balance:,.2f}.")
                return

            context.user_data['pending_withdrawal'] = {
                'amount': amount,
                'user_id': user.id
            }
            context.user_data['awaiting_withdraw_amount'] = False

            keyboard = [[InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw_funds")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"💸 WITHDRAWAL REQUEST: ${amount:,.2f}\n\n"
                "Please reply with your USDT wallet address (TRC20).\n\n"
                "⚠️ Important:\n"
                "• Only TRC20 USDT addresses\n"
                "• Double-check your address\n"
                "• Wrong address = lost funds\n\n"
                "Send your wallet address below: 👇",
                reply_markup=reply_markup
            )
        except (ValueError, TypeError):
            await update.message.reply_text("❌ That's not a valid number. Please enter the amount to withdraw.")
# Replace the existing WITHDRAWAL ADDRESS HANDLING section with this:

    # Replace the existing withdrawal address handling:
    elif context.user_data.get('pending_withdrawal'):
        wallet_address = message_text.strip()
        withdrawal_data = context.user_data['pending_withdrawal']
        amount = withdrawal_data['amount']
        user_id = user.id  # Add this line

        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO withdrawals (user_id, amount, wallet_address)
        VALUES (?, ?, ?)
    ''', (user_id, amount, wallet_address))  
        withdrawal_id = cursor.lastrowid  # Get the ID for deletion
        conn.commit()
        conn.close()

        # Portfolio button keyboard
        keyboard = [
            [InlineKeyboardButton("💼 View Portfolio", callback_data="show_portfolio")],
            [InlineKeyboardButton("📜 Transaction History", callback_data="show_history")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send confirmation message
        confirmation_message = await update.message.reply_text(
            "✅ Withdrawal Request Submitted\n\n"
            f"💰 Amount: ${amount:,.2f}\n"
            f"💳 Address: `{wallet_address}`\n\n"
            f"⏰ Funds will be sent to your wallet within 24 hours.\n"
            f"📊 Check your portfolio for balance updates.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Schedule deletion after 40 seconds
        context.job_queue.run_once(
            delete_message,
            40,
            data={
                'chat_id': update.effective_chat.id,
                'message_id': confirmation_message.message_id
            }
        )

        # Get user info from database (use user_id from pending_withdrawal, not message user)
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT full_name, email, username FROM users WHERE user_id = ?', (user.id,))
        user_info = cursor.fetchone()
        full_name = user_info[0] if user_info else 'N/A'
        email = user_info[1] if user_info else 'N/A'
        username = user_info[2] if user_info else 'N/A'
        conn.close()

        admin_notification = (
            f"🚨 WITHDRAWAL REQUEST 🚨\n\n"
            f"👤 USER VERIFICATION:\n"
            f"• Full Name: {full_name}\n"
            f"• Email: {email}\n"
            f"• Username: @{username}\n"
            f"• User ID: [{user.id}](tg://user?id={user.id})\n\n"
            f"💰 WITHDRAWAL DETAILS:\n"
            f"• Amount: ${amount:,.2f}\n"
            f"• Wallet Address: `{wallet_address}`\n"
            f"• Request Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"⚠️ VERIFY: Name and email match user records before confirming."
        )

        keyboard = [[
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_withdrawal_{withdrawal_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_withdrawal_{withdrawal_id}")
        ]]
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        for admin_id in ADMIN_USER_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_notification,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            except Exception as e:
                logging.error(f"Failed to send notification to admin {admin_id}: {e}")
                
    # BROADCAST MESSAGE HANDLING
    elif context.user_data.get('awaiting_broadcast_message'):
        if user.id not in ADMIN_USER_IDS:
            await update.message.reply_text("❌ You do not have permission to send broadcasts.")
            context.user_data.pop('awaiting_broadcast_message', None)
            return

        broadcast_text = message_text
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users')
        users = cursor.fetchall()
        conn.close()

        success_count = 0
        for user_tuple in users:
            try:
                await context.bot.send_message(chat_id=user_tuple[0], text=broadcast_text)
                success_count += 1
                await asyncio.sleep(0.1) # Avoid rate limiting
            except Exception as e:
                logging.error(f"Failed to send broadcast to {user_tuple[0]}: {e}")

        await update.message.reply_text(f"✅ Broadcast sent to {success_count}/{len(users)} users.")
        context.user_data.pop('awaiting_broadcast_message', None)

# --- MAIN FUNCTION ---
async def daily_profit_job(context: ContextTypes.DEFAULT_TYPE):
    """Job to be run daily to calculate and update user profits."""
    logging.info("Running daily profit calculation job...")
    calculate_user_profits()
    
    # Refresh dummy leaderboard occasionally
    if random.random() < 0.3:  # 30% chance daily
        refresh_dummy_leaderboard()
        logging.info("Dummy leaderboard refreshed with new growth numbers")
    
    logging.info("Daily profit calculation job completed.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates or callbacks."""
    logging.error(f"Exception while handling an update: {context.error}")

async def show_pending_stock_investments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT si.id, si.user_id, u.username, u.full_name, u.email, si.amount_invested_usd, si.stock_ticker, si.investment_date
        FROM stock_investments si
        JOIN users u ON si.user_id = u.user_id
        WHERE si.status = 'pending'
        ORDER BY si.investment_date DESC
    ''')
    pendings = cursor.fetchall()
    conn.close()

    if not pendings:
        if update.message:
            await update.message.reply_text("✅ No pending stock investments at the moment.")
        else:
            await update.callback_query.edit_message_text("✅ No pending stock investments at the moment.")
        return

    message = "📈 PENDING STOCK INVESTMENTS 📈\n\n"
    keyboard = []
    for inv in pendings:
        inv_id, user_id, username, full_name, email, amount, ticker, date = inv
        message += (
            f"• ID: {inv_id}\n"
            f"Name: {full_name or 'N/A'}\nEmail: {email or 'N/A'}\n"
            f"• User: @{username} [{user_id}](tg://user?id={user_id})\n"
            f"• Amount: ${amount:,.2f}\n"
            f"• Stock: {ticker.upper()}\n"
            f"• Date: {date}\n"
            f"• Confirm: /confirm_stock {user_id} {amount}\n"
            "─────────────────────\n"
        )
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_stock_{inv_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_stock_{inv_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        
async def show_pending_stock_sales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ss.id, ss.user_id, u.username, u.first_name, u.full_name, u.email, ss.shares_sold, ss.sale_price, 
               ss.total_value, ss.wallet_address, ss.sale_date, ss.stock_investment_id,
               si.stock_ticker, si.amount_invested_usd, si.purchase_price
        FROM stock_sales ss
        JOIN users u ON ss.user_id = u.user_id
        JOIN stock_investments si ON ss.stock_investment_id = si.id
        WHERE ss.status = 'pending'
        ORDER BY ss.sale_date DESC
    ''')
    pendings = cursor.fetchall()
    conn.close()

    if not pendings:
        if update.message:
            await update.message.reply_text("✅ No pending stock sales at the moment.")
        else:
            await update.callback_query.edit_message_text("✅ No pending stock sales at the moment.")
        return
    
    message = f"📊 PENDING STOCK SALES ({len(pendings)})\n\n"
    keyboard = []
    for sale in pendings:
        sale_id, user_id, username, first_name, full_name, email, shares, price, total, wallet, date, stock_id, ticker, invested, purchase_price = sale
        original_shares = invested / purchase_price
        message += (
            f"🆔 ID: {sale_id}\n"
            f"👤 {first_name} (@{username}) [{user_id}](tg://user?id={user_id})\n"
            f"Name: {full_name or 'N/A'}\nEmail: {email or 'N/A'}\n"
            f"📈 {ticker.upper()}\n"
            f"📊 Selling {shares:.2f}/{original_shares:.2f} shares\n"
            f"💰 Price: ${price:,.2f} | Total: ${total:,.2f}\n"
            f"💳 `{wallet[:20]}...`\n"
            f"📅 {date}\n"
            "─────────────────────\n"
        )
        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_stock_sale_{sale_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_stock_sale_{sale_id}")
        ])

    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)


# Enhanced show_user_stats function with balance management
async def show_user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced user stats with balance management options"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT SUM(total_invested) FROM users')
    total_invested_crypto = cursor.fetchone()[0] or 0.0

    cursor.execute('SELECT SUM(amount_invested_usd) FROM stock_investments WHERE status = "confirmed"')
    total_invested_stocks = cursor.fetchone()[0] or 0.0

    cursor.execute('SELECT SUM(current_balance) FROM users')
    total_balances = cursor.fetchone()[0] or 0.0

    cursor.execute('SELECT SUM(profit_earned) FROM users')
    total_profits = cursor.fetchone()[0] or 0.0

    cursor.execute('SELECT COUNT(*) FROM investments WHERE status = "pending"')
    pending_investments = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "pending"')
    pending_withdrawals = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stock_investments WHERE status = "pending"')
    pending_stock_invest = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM stock_sales WHERE status = "pending"')
    pending_stock_sales = cursor.fetchone()[0]

    # Get top 5 users by balance for quick access
    cursor.execute('''
        SELECT user_id, username, full_name, current_balance, total_invested
        FROM users 
        WHERE current_balance > 0 OR total_invested > 0
        ORDER BY current_balance DESC 
        LIMIT 5
    ''')
    top_users = cursor.fetchall()

    conn.close()

    message = "📊 BOT USER STATS 📊\n\n"
    message += f"• Total Users: {total_users:,}\n"
    message += f"• Total Crypto Invested: ${total_invested_crypto:,.2f}\n"
    message += f"• Total Stocks Invested: ${total_invested_stocks:,.2f}\n"
    message += f"• Total User Balances: ${total_balances:,.2f}\n"
    message += f"• Total Profits Earned: ${total_profits:,.2f}\n\n"
    
    message += "Pending Items:\n"
    message += f"• Investments: {pending_investments}\n"
    message += f"• Withdrawals: {pending_withdrawals}\n"
    message += f"• Stock Investments: {pending_stock_invest}\n"
    message += f"• Stock Sales: {pending_stock_sales}\n\n"
    
    if top_users:
        message += "💰 Top Users by Balance:\n"
        for user_id, username, full_name, balance, invested in top_users:
            display_name = full_name or username or f"User_{user_id}"
            message += f"• {display_name}: ${balance:,.2f}\n"

    # Enhanced keyboard with balance management options
    keyboard = [
        [
            InlineKeyboardButton("💰 Add User Balance", callback_data="admin_add_balance"),
            InlineKeyboardButton("💸 Deduct Balance", callback_data="admin_deduct_balance")
        ],
        [
            InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user"),
            InlineKeyboardButton("📋 User List", callback_data="admin_user_list")
        ],
        [
            InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_detailed_stats"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_user_stats")
        ],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

# New function to handle balance addition
async def admin_add_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin function to add balance to user account"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Stats", callback_data="admin_user_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💰 ADD USER BALANCE\n\n"
        "Please reply with the following format:\n"
        "`USER_ID AMOUNT`\n\n"
        "Example:\n"
        "`123456789 500.50`\n\n"
        "This will add $500.50 to user 123456789's balance.\n\n"
        "⚠️ Important:\n"
        "• Use the exact User ID number\n"
        "• Amount must be positive\n"
        "• Double-check before sending",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    context.user_data['awaiting_balance_add'] = True

# New function to handle balance deduction
async def admin_deduct_user_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin function to deduct balance from user account"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Stats", callback_data="admin_user_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💸 DEDUCT USER BALANCE\n\n"
        "Please reply with the following format:\n"
        "`USER_ID AMOUNT`\n\n"
        "Example:\n"
        "`123456789 100.00`\n\n"
        "This will deduct $100.00 from user 123456789's balance.\n\n"
        "⚠️ Important:\n"
        "• Use the exact User ID number\n"
        "• Amount must be positive\n"
        "• Cannot deduct more than current balance\n"
        "• Double-check before sending",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    context.user_data['awaiting_balance_deduct'] = True

# New function to search for specific users
async def admin_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin function to search for users"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Stats", callback_data="admin_user_stats")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔍 SEARCH USER\n\n"
        "Reply with any of the following:\n"
        "• User ID (e.g., 123456789)\n"
        "• Username (e.g., @username)\n"
        "• Full name or partial name\n"
        "• Email address\n\n"
        "I'll show you matching user details and balance information.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    context.user_data['awaiting_user_search'] = True

# Enhanced text message handler additions
async def handle_admin_balance_operations(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle admin balance operations from text messages"""
    user = update.effective_user
    
    # Handle balance addition
    if context.user_data.get('awaiting_balance_add'):
        try:
            parts = message_text.strip().split()
            if len(parts) != 2:
                await update.message.reply_text(
                    "❌ Invalid format. Use: USER_ID AMOUNT\n"
                    "Example: 123456789 500.50"
                )
                return
            
            user_id = int(parts[0])
            amount = float(parts[1])
            
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be positive.")
                return
            
            # Check if user exists
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT username, full_name, current_balance FROM users WHERE user_id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                await update.message.reply_text(f"❌ User {user_id} not found.")
                conn.close()
                return
            
            username, full_name, current_balance = user_data
            
            # Add balance
            cursor.execute(
                'UPDATE users SET current_balance = current_balance + ? WHERE user_id = ?',
                (amount, user_id)
            )
            
            # Log the transaction for audit trail
            cursor.execute('''
                INSERT INTO admin_balance_logs (admin_id, target_user_id, action_type, amount, old_balance, new_balance, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user.id, user_id, 'ADD', amount, current_balance, current_balance + amount, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # Confirmation message
            display_name = full_name or username or f"User_{user_id}"
            confirmation_msg = await update.message.reply_text(
                f"✅ BALANCE ADDED SUCCESSFULLY\n\n"
                f"👤 User: {display_name} [{user_id}]\n"
                f"💰 Amount Added: ${amount:,.2f}\n"
                f"📊 Old Balance: ${current_balance:,.2f}\n"
                f"📊 New Balance: ${current_balance + amount:,.2f}\n"
                f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"✨ User has been notified of the balance update."
            )
            
            # Notify the user
            try:
                keyboard = [
                    [InlineKeyboardButton("📊 View Portfolio", callback_data="view_portfolio")],
                    [InlineKeyboardButton("💸 Withdraw Funds", callback_data="withdraw_funds")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🎉 BALANCE UPDATE!\n\n"
                         f"💰 ${amount:,.2f} has been added to your account!\n"
                         f"📊 New Balance: ${current_balance + amount:,.2f}\n\n"
                         f"Check your portfolio to see the update!",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.error(f"Failed to notify user {user_id} about balance addition: {e}")
            
            # Schedule deletion after 30 seconds
            context.job_queue.run_once(
                delete_message,
                30,
                data={
                    'chat_id': update.effective_chat.id,
                    'message_id': confirmation_msg.message_id
                }
            )
            
        except ValueError:
            await update.message.reply_text("❌ Invalid format. User ID and amount must be numbers.")
        except Exception as e:
            logging.error(f"Error in admin balance addition: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
        
        context.user_data.pop('awaiting_balance_add', None)
        return True
    
    # Handle balance deduction
    elif context.user_data.get('awaiting_balance_deduct'):
        try:
            parts = message_text.strip().split()
            if len(parts) != 2:
                await update.message.reply_text(
                    "❌ Invalid format. Use: USER_ID AMOUNT\n"
                    "Example: 123456789 100.00"
                )
                return
            
            user_id = int(parts[0])
            amount = float(parts[1])
            
            if amount <= 0:
                await update.message.reply_text("❌ Amount must be positive.")
                return
            
            # Check if user exists and has sufficient balance
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT username, full_name, current_balance FROM users WHERE user_id = ?', (user_id,))
            user_data = cursor.fetchone()
            
            if not user_data:
                await update.message.reply_text(f"❌ User {user_id} not found.")
                conn.close()
                return
            
            username, full_name, current_balance = user_data
            
            if current_balance < amount:
                await update.message.reply_text(
                    f"❌ Insufficient balance.\n"
                    f"Current Balance: ${current_balance:,.2f}\n"
                    f"Requested Deduction: ${amount:,.2f}"
                )
                conn.close()
                return
            
            # Deduct balance
            cursor.execute(
                'UPDATE users SET current_balance = current_balance - ? WHERE user_id = ?',
                (amount, user_id)
            )
            
            # Log the transaction
            cursor.execute('''
                INSERT INTO admin_balance_logs (admin_id, target_user_id, action_type, amount, old_balance, new_balance, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user.id, user_id, 'DEDUCT', amount, current_balance, current_balance - amount, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            # Confirmation message
            display_name = full_name or username or f"User_{user_id}"
            confirmation_msg = await update.message.reply_text(
                f"✅ BALANCE DEDUCTED SUCCESSFULLY\n\n"
                f"👤 User: {display_name} [{user_id}]\n"
                f"💸 Amount Deducted: ${amount:,.2f}\n"
                f"📊 Old Balance: ${current_balance:,.2f}\n"
                f"📊 New Balance: ${current_balance - amount:,.2f}\n"
                f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"✨ User has been notified of the balance update."
            )
            
            # Notify the user
            try:
                keyboard = [[InlineKeyboardButton("📊 View Portfolio", callback_data="view_portfolio")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📊 BALANCE UPDATE\n\n"
                         f"💸 ${amount:,.2f} has been deducted from your account.\n"
                         f"📊 New Balance: ${current_balance - amount:,.2f}\n\n"
                         f"If you have questions, please contact support.",
                    reply_markup=reply_markup
                )
            except Exception as e:
                logging.error(f"Failed to notify user {user_id} about balance deduction: {e}")
            
            # Schedule deletion after 30 seconds
            context.job_queue.run_once(
                delete_message,
                30,
                data={
                    'chat_id': update.effective_chat.id,
                    'message_id': confirmation_msg.message_id
                }
            )
            
        except ValueError:
            await update.message.reply_text("❌ Invalid format. User ID and amount must be numbers.")
        except Exception as e:
            logging.error(f"Error in admin balance deduction: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
        
        context.user_data.pop('awaiting_balance_deduct', None)
        return True
    
    # Handle user search
    elif context.user_data.get('awaiting_user_search'):
        try:
            search_term = message_text.strip()
            
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            
            # Try different search methods
            if search_term.isdigit():
                # Search by user ID
                cursor.execute('''
                    SELECT user_id, username, full_name, email, current_balance, total_invested, profit_earned
                    FROM users WHERE user_id = ?
                ''', (int(search_term),))
            elif search_term.startswith('@'):
                # Search by username
                username = search_term[1:]  # Remove @
                cursor.execute('''
                    SELECT user_id, username, full_name, email, current_balance, total_invested, profit_earned
                    FROM users WHERE username LIKE ?
                ''', (f'%{username}%',))
            elif '@' in search_term:
                # Search by email
                cursor.execute('''
                    SELECT user_id, username, full_name, email, current_balance, total_invested, profit_earned
                    FROM users WHERE email LIKE ?
                ''', (f'%{search_term}%',))
            else:
                # Search by name
                cursor.execute('''
                    SELECT user_id, username, full_name, email, current_balance, total_invested, profit_earned
                    FROM users WHERE full_name LIKE ? OR username LIKE ?
                ''', (f'%{search_term}%', f'%{search_term}%'))
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                await update.message.reply_text(f"❌ No users found matching: {search_term}")
                return
            
            if len(results) > 10:
                await update.message.reply_text(f"🔍 Found {len(results)} users. Showing first 10 results:")
                results = results[:10]
            
            response_text = f"🔍 SEARCH RESULTS ({len(results)} found)\n\n"
            for user_id, username, full_name, email, balance, invested, profit in results:
                display_name = full_name or username or f"User_{user_id}"
                response_text += f"👤 {display_name}\n"
                response_text += f"   ID: {user_id}\n"
                response_text += f"   Username: @{username or 'None'}\n"
                response_text += f"   Email: {email or 'None'}\n"
                response_text += f"   💰 Balance: ${balance:,.2f}\n"
                response_text += f"   📊 Invested: ${invested:,.2f}\n"
                response_text += f"   💎 Profit: ${profit:,.2f}\n"
                response_text += "   ─────────────────\n"
            
            # Add quick action buttons for single result
            if len(results) == 1:
                user_id = results[0][0]
                keyboard = [
                    [
                        InlineKeyboardButton("💰 Add Balance", callback_data=f"admin_quick_add_{user_id}"),
                        InlineKeyboardButton("💸 Deduct Balance", callback_data=f"admin_quick_deduct_{user_id}")
                    ],
                    [InlineKeyboardButton("🔙 Back to Stats", callback_data="admin_user_stats")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Back to Stats", callback_data="admin_user_stats")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response_text, reply_markup=reply_markup)
            
        except Exception as e:
            logging.error(f"Error in user search: {e}")
            await update.message.reply_text("❌ An error occurred during search.")
        
        context.user_data.pop('awaiting_user_search', None)
        return True
    
    return False

# Updated button callback handler additions
async def handle_admin_balance_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Handle admin balance-related callbacks"""
    if data == "admin_add_balance":
        await admin_add_user_balance(update, context)
        return True
    elif data == "admin_deduct_balance":
        await admin_deduct_user_balance(update, context)
        return True
    elif data == "admin_search_user":
        await admin_search_user(update, context)
        return True
    elif data.startswith("admin_quick_add_"):
        user_id = int(data.split("_")[3])
        query = update.callback_query
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_user_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"💰 QUICK ADD BALANCE\n\n"
            f"User ID: {user_id}\n\n"
            f"Reply with the amount to add:\n"
            f"Example: 500.50",
            reply_markup=reply_markup
        )
        context.user_data['awaiting_balance_add'] = True
        context.user_data['quick_add_user_id'] = user_id
        return True
    elif data.startswith("admin_quick_deduct_"):
        user_id = int(data.split("_")[3])
        query = update.callback_query
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_user_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"💸 QUICK DEDUCT BALANCE\n\n"
            f"User ID: {user_id}\n\n"
            f"Reply with the amount to deduct:\n"
            f"Example: 100.00",
            reply_markup=reply_markup
        )
        context.user_data['awaiting_balance_deduct'] = True
        context.user_data['quick_deduct_user_id'] = user_id
        return True
    
    return False

async def show_pending_investments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending crypto investments"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.id, u.username, i.amount, i.crypto_type, i.wallet_address, i.investment_date
        FROM investments i
        JOIN users u ON i.user_id = u.user_id
        WHERE i.status = 'pending'
        ORDER BY i.investment_date DESC
    ''')
    pendings = cursor.fetchall()
    conn.close()

    if not pendings:
        if update.message:
            await update.message.reply_text("✅ No pending investments at the moment.")
        else:
            await update.callback_query.edit_message_text("✅ No pending investments at the moment.")
        return

    message = "🤑 PENDING INVESTMENTS 🤑\n\n"
    keyboard = []
    for inv in pendings:
        inv_id, username, amount, crypto, wallet, date = inv
        message += (
            f"• ID: {inv_id}\n"
            f"• User: @{username}\n"
            f"• Amount: ${amount:,.2f} ({crypto})\n"
            f"• Wallet: `{wallet[:10]}...`\n"
            f"• Date: {date}\n"
            f"• Confirm: /confirm_investment {inv_id}\n"
            "─────────────────────\n"
        )
        keyboard.append([
        InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_investment_{inv_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_investment_{inv_id}")
    ])
    
    if update.message:
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')

async def show_pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending withdrawals"""
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
    SELECT w.id, u.username, w.amount, w.wallet_address, w.withdrawal_date, u.full_name, u.email
    FROM withdrawals w
    JOIN users u ON w.user_id = u.user_id
    WHERE w.status = 'pending'
    ORDER BY w.withdrawal_date DESC
    ''')
    pendings = cursor.fetchall()
    conn.close()

    if not pendings:
        if update.message:
            await update.message.reply_text("✅ No pending withdrawals at the moment.")
        else:
            await update.callback_query.edit_message_text("✅ No pending withdrawals at the moment.")
        return

    message = "💸 PENDING WITHDRAWALS 💸\n\n"
    keyboard = []
    for wd in pendings:
        wd_id, username,full_name, email, amount, wallet, date = wd
        message += (
            f"• ID: {wd_id}\n"
            f"• User: @{username}\n"
            f"• Name: {full_name or 'N/A'}\n"
            f"• Email: {email or 'N/A'}\n"
            f"• Amount: ${amount:,.2f}\n"
            f"• Wallet: `{wallet[:10]}...`\n"
            f"• Date: {date}\n"
            "─────────────────────\n"
        )

        keyboard.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"admin_confirm_withdrawal_{wd_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_withdrawal_{wd_id}")
        ])
    
    if update.message:
        await update.message.reply_text(message, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(message, parse_mode='Markdown')

async def show_transaction_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's complete transaction history with error handling"""
    query = update.callback_query
    user = query.from_user
    
    try:
        user_id = user.id
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        history_text = "📜 TRANSACTION HISTORY\n\n"
        
        # Crypto Investments
        cursor.execute('''
            SELECT amount, crypto_type, investment_date, status, plan
            FROM investments WHERE user_id = ? ORDER BY investment_date DESC LIMIT 10
        ''', (user_id,))
        investments = cursor.fetchall()
        
        if investments:
            history_text += "💰 Crypto Investments:\n"
            for inv in investments:
                amount, crypto, date, status, plan = inv
                status_emoji = "✅" if status == "confirmed" else "⏳"
                history_text += f"• ${amount:,.2f} {crypto.upper()} | {plan} | {status_emoji} | {date[:10]}\n"
            history_text += "\n"
        
        # Stock Purchases
        cursor.execute('''
            SELECT stock_ticker, amount_invested_usd, purchase_price, investment_date, status
            FROM stock_investments WHERE user_id = ? ORDER BY investment_date DESC LIMIT 10
        ''', (user_id,))
        stocks = cursor.fetchall()
        
        if stocks:
            history_text += "📈 Stock Purchases:\n"
            for stock in stocks:
                ticker, amount, price, date, status = stock
                status_emoji = "✅" if status == "confirmed" else "⏳"
                shares = amount / price if price and price > 0 else 0
                history_text += f"• {ticker.upper()} | {shares:.1f} shares | ${amount:,.2f} | {status_emoji} | {date[:10]}\n"
            history_text += "\n"
        
        # Withdrawals
        cursor.execute('''
            SELECT amount, withdrawal_date, status
            FROM withdrawals WHERE user_id = ? ORDER BY withdrawal_date DESC LIMIT 10
        ''', (user_id,))
        withdrawals = cursor.fetchall()
        
        if withdrawals:
            history_text += "💸 Withdrawals:\n"
            for wd in withdrawals:
                amount, date, status = wd
                status_emoji = "✅" if status == "confirmed" else "⏳"
                history_text += f"• ${amount:,.2f} | {status_emoji} | {date[:10]}\n"
            history_text += "\n"
        
        # Stock Sales
        cursor.execute('''
            SELECT si.stock_ticker, ss.shares_sold, ss.total_value, ss.sale_date, ss.status
            FROM stock_sales ss
            JOIN stock_investments si ON ss.stock_investment_id = si.id
            WHERE ss.user_id = ? ORDER BY ss.sale_date DESC LIMIT 10
        ''', (user_id,))
        sales = cursor.fetchall()
        
        if sales:
            history_text += "📉 Stock Sales:\n"
            for sale in sales:
                ticker, shares, value, date, status = sale
                status_emoji = "✅" if status == "confirmed" else "⏳"
                history_text += f"• {ticker.upper()} | {shares:.1f} shares | ${value:,.2f} | {status_emoji} | {date[:10]}\n"
            history_text += "\n"
        
        if not (investments or stocks or withdrawals or sales):
            history_text += "No transactions yet. Start investing to build your history! 🚀"
        
        keyboard = [
            [InlineKeyboardButton("💼 View Portfolio", callback_data="view_portfolio")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Remove parse_mode to avoid Markdown errors
        await query.edit_message_text(
            history_text,
            reply_markup=reply_markup
        )
        
        conn.close()
        
    except Exception as e:
        logging.error(f"Error in show_transaction_history: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Show user-friendly error
        error_text = "❌ Error loading transaction history. Please try again later."
        keyboard = [
            [InlineKeyboardButton("💼 View Portfolio", callback_data="view_portfolio")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            error_text,
            reply_markup=reply_markup
        )    
    conn.close()

async def reject_stock_sale_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a pending stock sale"""
    if update.effective_user.id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Admin access required.")
        return

    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /reject_stock_sale <user_id> <stock_sale_id>\n"
            "Example: /reject_stock_sale 123456789 42"
        )
        return

    try:
        user_id = int(context.args[0])
        sale_id = int(context.args[1])
        
        conn = sqlite3.connect('trading_bot.db')
        cursor = conn.cursor()
        
        # Update sale status to rejected
        cursor.execute(
            'UPDATE stock_sales SET status = "rejected" WHERE id = ? AND user_id = ?',
            (sale_id, user_id)
        )
        
        if cursor.rowcount > 0:
            # Notify user
            await context.bot.send_message(
                chat_id=user_id,
                text="❌ Your stock sale request has been rejected. Please contact support for more details."
            )
            await update.message.reply_text(f"✅ Stock sale {sale_id} for user {user_id} has been rejected.")
        else:
            await update.message.reply_text(f"❌ No pending stock sale found with ID {sale_id} for user {user_id}.")
        
        conn.commit()
        conn.close()
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID or sale ID. Both must be numbers.")
    except Exception as e:
        logging.error(f"Error rejecting stock sale: {e}")
        await update.message.reply_text("❌ An error occurred while processing the request.")

async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    try:
        await context.bot.delete_message(
            chat_id=job_data['chat_id'],
            message_id=job_data['message_id']
        )
    except Exception as e:
        logging.info(f"Failed to delete message {job_data['message_id']}: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callback queries"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    try:
        # PORTFOLIO & HISTORY
        if data == 'show_portfolio' or data == 'view_portfolio':
            await portfolio_command(update, context)
        elif data == 'refresh_portfolio':
            try:
                calculate_user_profits()
                await portfolio_command(update, context)
            except Exception as e:
                logging.error(f"Error in refresh_portfolio: {e}")
                user = update.effective_user
                user_data = get_user_from_db(user.id)
                
                if user_data:
                    # Show portfolio without recalculating if there's an error
                    await portfolio_command(update, context)
                else:
                    error_text = "❌ Error refreshing portfolio. Please try again."
                    keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.edit_text(error_text, reply_markup=reply_markup)
        elif data == 'show_history':
            try:
                await show_transaction_history(update, context)
            except Exception as e:
                logging.error(f"Error handling show_history callback: {e}")
                query = update.callback_query
                await query.answer("Error loading history", show_alert=True)
        
        # NAVIGATION
        elif data == 'main_menu' or data == 'back_to_main':
            user = update.effective_user
            await show_main_menu(update, context, user)
        elif data == 'invest_menu':
            await invest_command(update, context)
        elif data == 'withdraw_menu' or data == 'withdraw_funds':
            await withdraw_command(update, context)
        elif data == 'profile_menu' or data == 'show_profile':
            await profile_command(update, context)
        
        # LEADERBOARD
        elif data == 'show_leaderboard':
            await show_leaderboard(update, context)
        elif data == 'leaderboard_full':
            await show_full_leaderboard(update, context, 0)
        elif data.startswith('leaderboard_full_'):
            try:
                start_index = int(data.split('_')[2])
                await show_full_leaderboard(update, context, start_index)
            except (ValueError, IndexError):
                await show_full_leaderboard(update, context, 0)
        
        # LIVE PRICES
        elif data == 'show_prices':
            await display_live_prices_menu(update, context)
        elif data.startswith('live_crypto_prices_'):
            try:
                start_index = int(data.split('_')[3])
                await display_crypto_prices(update, context, start_index)
            except (ValueError, IndexError):
                await display_crypto_prices(update, context, 0)
        elif data.startswith('live_stock_prices_'):
            try:
                start_index = int(data.split('_')[3])
                await display_stock_prices(update, context, start_index)
            except (ValueError, IndexError):
                await display_stock_prices(update, context, 0)
        
        # WITHDRAWAL OPTIONS
        elif data.startswith('withdraw_'):
            user = update.effective_user
            if data == 'withdraw_custom':
                user_data = get_user_from_db(user.id)
                current_balance = user_data[8] if user_data and len(user_data) > 8 else 0
                keyboard = [[InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw_funds")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text(
                    f"💸 Custom Withdrawal Amount\n\n"
                    f"Please reply with the amount you want to withdraw (minimum $10):\n\n"
                    f"💰 Your current balance: ${current_balance:,.2f}",
                    reply_markup=reply_markup
                )
                context.user_data['awaiting_withdraw_amount'] = True
            else:
                # Handle percentage withdrawals (25, 50, 100)
                try:
                    percent_str = data.split('_')[1]
                    amount = context.user_data['withdraw_options'].get(f"{percent_str}%")
                    if amount is None:
                        await query.message.edit_text("❌ Invalid withdrawal option. Please try again.")
                        return
                    
                    keyboard = [[InlineKeyboardButton("🔙 Withdraw Menu", callback_data="withdraw_funds")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.message.edit_text(
                        f"💸 WITHDRAWAL REQUEST: ${amount:,.2f}\n\n"
                        "Please reply with your USDT wallet address (TRC20)\n\n"
                        "⚠️ Important:\n"
                        "• Only TRC20 USDT addresses\n"
                        "• Double-check your address\n"
                        "• Wrong address = lost funds\n\n"
                        "Send your wallet address below: 👇",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    context.user_data['pending_withdrawal'] = {
                        'amount': amount,
                        'user_id': user.id
                    }
                except Exception as e:
                    logging.error(f"Error handling withdrawal: {e}")
                    await query.message.edit_text("❌ Error processing withdrawal. Please try again.")
        
        # STOCK TRADING
        elif data == 'sell_stocks':
            await handle_sell_stocks(update, context)
        elif data.startswith('sell_stock_'):
            try:
                stock_id = int(data.split('_')[2])
                await handle_individual_stock_sale(update, context, stock_id)
            except (ValueError, IndexError):
                await query.message.edit_text(
                    "❌ Invalid stock selection.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Withdraw", callback_data="withdraw_funds")]])
                )

        elif data.startswith('display_stocks_page_'):
            try:
                page_num = int(data.split('_')[3])
                
                # Separate stocks by category
                if page_num < len(TECH_STOCKS) // 5 + 1:
                    # Tech stocks page
                    stocks_list = TECH_STOCKS
                    category_title = "💻 TECH STOCKS"
                else:
                    # Non-tech stocks page  
                    stocks_list = NON_TECH_STOCKS
                    category_title = "🏢 NON-TECH STOCKS"
                    page_num = page_num - (len(TECH_STOCKS) // 5 + 1)  # Adjust page number
                
                stocks_per_page = 5
                start_idx = page_num * stocks_per_page
                end_idx = start_idx + stocks_per_page
                page_stocks = stocks_list[start_idx:end_idx]
                
                if not page_stocks:
                    await query.edit_message_text(
                        "❌ No more stocks to display.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Invest Menu", callback_data="invest_menu")]])
                    )
                    return
                
                # Build stock display message
                message_text = f"📈 {category_title} (Page {page_num + 1})\n\n"
                for i, stock in enumerate(page_stocks, start=start_idx + 1):
                    try:
                        stock_info = yf.Ticker(stock)
                        price = stock_info.info.get('regularMarketPrice', 'N/A')
                        change = stock_info.info.get('regularMarketChangePercent', 0)
                        change_text = "📈" if change > 0 else "📉"
                        message_text += f"{i}. {stock} {change_text} ${price}\n"
                    except:
                        message_text += f"{i}. {stock} 💲 Price: Loading...\n"
                
                # Build navigation keyboard
                keyboard = []
                
                # Add navigation buttons
                nav_buttons = []
                if start_idx > 0:
                    if page_num == 0 and category_title == "🏢 NON-TECH STOCKS":
                        nav_buttons.append(InlineKeyboardButton("⬅️ Tech Stocks", callback_data="display_stocks_page_0"))
                    else:
                        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"display_stocks_page_{page_num - 1}"))
                
                if end_idx < len(stocks_list):
                    nav_buttons.append(InlineKeyboardButton("➡️ Next", callback_data=f"display_stocks_page_{page_num + 1}"))
                elif category_title == "💻 TECH STOCKS":
                    nav_buttons.append(InlineKeyboardButton("➡️ Non-Tech Stocks", callback_data=f"display_stocks_page_{len(TECH_STOCKS) // 5 + 1}"))
                
                if nav_buttons:
                    keyboard.append(nav_buttons)
                
                # Add stock buy buttons
                for stock in page_stocks:
                    keyboard.append([InlineKeyboardButton(f"💰 Buy {stock}", callback_data=f"buy_stock_{stock}")])
                
                # Add back button
                keyboard.append([InlineKeyboardButton("🔙 Invest Menu", callback_data="invest_menu")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message_text, reply_markup=reply_markup)
                
            except (ValueError, IndexError):
                await query.edit_message_text(
                    "❌ Error loading stocks.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Invest Menu", callback_data="invest_menu")]])
                )
        
        # REFERRALS
        elif data == 'referral_info':
            await show_referral_info(update, context)
        
        # HELP
        elif data == 'help':
            help_text = """
📖 HELP & SUPPORT

🚀 Getting Started:
• Use /start to register and access main menu
• Complete your profile with name and email
• Check the leaderboard for inspiration!

💰 Investing:
• Choose from Crypto Plans or Individual Stocks
• Send payment to provided wallet addresses
• All transactions require admin confirmation

💸 Withdrawing:
• Minimum $10 USDT (TRC20 network only)
• Provide correct wallet address carefully
• Processed within 24 hours

📊 Tracking:
• Portfolio shows all investments and balances
• Live Prices for real-time market data
• Transaction History for complete activity

👥 Referrals:
• Share your unique code to earn 5% commission
• Use: /start YOURREFERRALCODE

⚠️ Security:
• Always double-check wallet addresses
• Never share private keys or passwords
• Use only TRC20 network for USDT withdrawals

Need more help? Contact support!
            """
            keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # ADMIN PANEL
        elif data.startswith('admin_'):
            if query.from_user.id not in ADMIN_USER_IDS:
                await query.answer("❌ Unauthorized access.", show_alert=True)
                return
            
            parts = data.split('_')
            action = parts[1] if len(parts) > 1 else None
            
            if action == 'panel':
                await admin_command(update, context)
            elif action == 'investments':
                await show_pending_investments(update, context)
            elif action == 'withdrawals':
                await show_pending_withdrawals(update, context)
            elif action == 'stockinvestments':  # Renamed for consistency (update button callback_data accordingly)
                await show_pending_stock_investments(update, context)
            elif action == 'stocksales':  # Renamed for consistency
                await show_pending_stock_sales(update, context)
            elif action == 'userstats':  # Renamed for consistency
                await show_user_stats(update, context)
            elif action == 'broadcast':
                context.user_data['awaiting_broadcast_message'] = True
                keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.edit_text(
                    "📢 Please reply with the message you want to broadcast to all users.\n\n"
                    "⚠️ Max 2000 characters. Supports Markdown.",
                    reply_markup=reply_markup
                )
            # Add more actions as we build (e.g., logs in later steps)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
                await query.message.edit_text("❌ Unknown admin action.", reply_markup=InlineKeyboardMarkup(keyboard))     

        elif data == 'stock_categories':
            keyboard = [
                [InlineKeyboardButton("💻 Tech Stocks", callback_data="tech_stocks")],
                [InlineKeyboardButton("🏢 Non-Tech Stocks", callback_data="non_tech_stocks")],
                [InlineKeyboardButton("🔙 Back", callback_data="invest_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📈 STOCK INVESTMENT OPTIONS\n\nChoose a stock category:",
                reply_markup=reply_markup
            )
        elif data == 'tech_stocks':
            keyboard = []
            for stock in TECH_STOCKS:
                keyboard.append([InlineKeyboardButton(stock, callback_data=f"buy_stock_{stock}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="stock_categories")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "💻 TECH STOCKS\n\nSelect a stock to invest in:",
                reply_markup=reply_markup
            )
        elif data == 'non_tech_stocks':
            keyboard = []
            for stock in NON_TECH_STOCKS:
                keyboard.append([InlineKeyboardButton(stock, callback_data=f"buy_stock_{stock}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="stock_categories")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "🏢 NON-TECH STOCKS\n\nSelect a stock to invest in:",
                reply_markup=reply_markup
            )
        elif data == 'confirm_payment':
            if 'awaiting_tx_details' not in context.user_data:
                await query.edit_message_text("❌ Session expired. Please start investment again.")
                return
            context.user_data['awaiting_payment_details'] = True
            await query.edit_message_text(
                "📝 Provide payment details in this format:\n\n"
                "Amount: [USD amount]\n"
                "Transaction ID: [transaction ID]\n\n"
                "Network: [network_name]\n\n"
                "Example:\n"
                "Amount: 1500\n"
                "Transaction ID: 123abc...def\n\n"
                "Network: bitcoin\n\n"
                "Send as one message."
            )
        elif data.startswith('admin_confirm_withdrawal_'):
            wd_id = int(data.split('_')[3])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount FROM withdrawals WHERE id = ? AND status = "pending"', (wd_id,))
            wd = cursor.fetchone()
            if not wd:
                await query.edit_message_text("❌ No pending withdrawal found.")
                conn.close()
                return
            user_id, amount = wd
            cursor.execute('UPDATE withdrawals SET status = "confirmed", processed_by = ? WHERE id = ?', (admin_id, wd_id))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "✅ Your withdrawal has been confirmed and processed.")
            await query.edit_message_text(f"✅ Withdrawal {wd_id} confirmed.")

        elif data.startswith('admin_reject_withdrawal_'):
            wd_id = int(data.split('_')[3])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount FROM withdrawals WHERE id = ? AND status = "pending"', (wd_id,))
            wd = cursor.fetchone()
            if not wd:
                await query.edit_message_text("❌ No pending withdrawal found.")
                conn.close()
                return
            user_id, amount = wd
            cursor.execute('UPDATE withdrawals SET status = "rejected", processed_by = ? WHERE id = ?', (admin_id, wd_id))
            cursor.execute('UPDATE users SET current_balance = current_balance + ? WHERE user_id = ?', (amount, user_id))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "❌ Your withdrawal has been rejected. Amount added back to balance.")
            await query.edit_message_text(f"❌ Withdrawal {wd_id} rejected.")

        elif data.startswith('admin_confirm_investment_'):
            inv_id = int(data.split('_')[3])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, amount, plan FROM investments WHERE id = ? AND status = "pending"', (inv_id,))
            inv = cursor.fetchone()
            if not inv:
                await query.edit_message_text("❌ No pending investment found.")
                conn.close()
                return
            user_id, amount, plan = inv
            cursor.execute('UPDATE investments SET status = "confirmed" WHERE id = ?', (inv_id,))
            cursor.execute('UPDATE users SET total_invested = total_invested + ?, current_balance = current_balance + ?, plan = ?, last_profit_update = ? WHERE user_id = ?', (amount, amount, plan.upper(), datetime.now().isoformat(), user_id))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "✅ Your investment has been confirmed.")
            await query.edit_message_text(f"✅ Investment {inv_id} confirmed.")

        elif data.startswith('admin_reject_investment_'):
            inv_id = int(data.split('_')[3])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM investments WHERE id = ? AND status = "pending"', (inv_id,))
            inv = cursor.fetchone()
            if not inv:
                await query.edit_message_text("❌ No pending investment found.")
                conn.close()
                return
            user_id = inv[0]
            cursor.execute('UPDATE investments SET status = "rejected" WHERE id = ?', (inv_id,))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "❌ Your investment has been rejected. Contact support for refund.")
            await query.edit_message_text(f"❌ Investment {inv_id} rejected.")

        elif data.startswith('admin_confirm_stock_'):
            stock_id = int(data.split('_')[3])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM stock_investments WHERE id = ? AND status = "pending"', (stock_id,))
            stock = cursor.fetchone()
            if not stock:
                await query.edit_message_text("❌ No pending stock investment found.")
                conn.close()
                return
            user_id = stock[0]
            cursor.execute('UPDATE stock_investments SET status = "confirmed", confirmed_date = ?, confirmed_by = ? WHERE id = ?', (datetime.now().isoformat(), admin_id, stock_id))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "✅ Your stock investment has been confirmed.")
            await query.edit_message_text(f"✅ Stock investment {stock_id} confirmed.")

        elif data.startswith('admin_reject_stock_'):
            stock_id = int(data.split('_')[3])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM stock_investments WHERE id = ? AND status = "pending"', (stock_id,))
            stock = cursor.fetchone()
            if not stock:
                await query.edit_message_text("❌ No pending stock investment found.")
                conn.close()
                return
            user_id = stock[0]
            cursor.execute('UPDATE stock_investments SET status = "rejected" WHERE id = ?', (stock_id,))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "❌ Your stock investment has been rejected. Contact support for refund.")
            await query.edit_message_text(f"❌ Stock investment {stock_id} rejected.")
        
        elif data.startswith('admin_confirm_stock_sale_'):
            sale_id = int(data.split('_')[4])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, total_value FROM stock_sales WHERE id = ? AND status = "pending"', (sale_id,))
            sale = cursor.fetchone()
            if not sale:
                await query.edit_message_text("❌ No pending stock sale found.")
                conn.close()
                return
            user_id, total_value = sale
            cursor.execute('UPDATE stock_sales SET status = "confirmed", processed_by = ?, processed_date = ? WHERE id = ?', (admin_id, datetime.now().isoformat(), sale_id))
            cursor.execute('UPDATE users SET current_balance = current_balance + ? WHERE user_id = ?', (total_value, user_id))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "✅ Your stock sale has been confirmed. Proceeds added to balance.")
            await query.edit_message_text(f"✅ Stock sale {sale_id} confirmed.")

        elif data.startswith('admin_reject_stock_sale_'):
            sale_id = int(data.split('_')[4])
            admin_id = query.from_user.id
            conn = sqlite3.connect('trading_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM stock_sales WHERE id = ? AND status = "pending"', (sale_id,))
            sale = cursor.fetchone()
            if not sale:
                await query.edit_message_text("❌ No pending stock sale found.")
                conn.close()
                return
            user_id = sale[0]
            cursor.execute('UPDATE stock_sales SET status = "rejected", processed_by = ? WHERE id = ?', (admin_id, sale_id))
            conn.commit()
            conn.close()
            await context.bot.send_message(user_id, "❌ Your stock sale has been rejected.")
            await query.edit_message_text(f"❌ Stock sale {sale_id} rejected.")
        elif data.startswith('admin_'):
            if query.from_user.id not in ADMIN_USER_IDS:
                await query.answer("❌ Unauthorized access.", show_alert=True)
                return
            if await handle_admin_balance_callbacks(update, context, data):
               return
        # CRYPTO INVESTMENT FLOW
        elif data == 'crypto_plans':
            # Show crypto investment plans
            keyboard = [
                [InlineKeyboardButton("🥉 Core Plan ($1K-$15K)", callback_data="crypto_plan_0")],
                [InlineKeyboardButton("🥈 Growth Plan ($20K-$80K)", callback_data="crypto_plan_1")],
                [InlineKeyboardButton("🥇 Alpha Plan ($100K+)", callback_data="crypto_plan_2")],
                [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                "💰 CRYPTO INVESTMENT PLANS\n\n"
                "Choose your investment tier:\n\n"
                "🥉 *Core (Starter)*: $1,000 - $15,000\n"
                "   • Daily Return: 1.43%\n"
                "   • Perfect for beginners\n\n"
                "🥈 *Growth (Balanced)*: $20,000 - $80,000\n"
                "   • Daily Return: 2.14%\n"
                "   • Balanced growth strategy\n\n"
                "🥇 *Alpha (Premium)*: $100,000+\n"
                "   • Daily Return: 2.86%\n"
                "   • Maximum returns for high rollers",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        elif data.startswith('crypto_type_'):
            try:
                parts = data.split('_')
                plan_index = int(parts[2])
                crypto_type = parts[3]
                
                plan_list = [InvestmentPlan.CORE.value, InvestmentPlan.GROWTH.value, InvestmentPlan.ALPHA.value]
                selected_plan = plan_list[plan_index]
                plan_names = ['CORE', 'GROWTH', 'ALPHA']
                
                wallet_address = get_random_wallet(crypto_type)
                if not wallet_address:
                    await query.message.edit_text("❌ Invalid cryptocurrency selected.")
                    return

                context.user_data['awaiting_tx_details'] = {
                    'plan_type': plan_names[plan_index],
                    'plan_info': selected_plan,
                    'crypto': crypto_type,
                    'wallet_address': wallet_address,
                    'user_id': query.from_user.id
                }

                keyboard = [
                    [InlineKeyboardButton("✅ I've Sent Payment", callback_data="confirm_payment")],
                    [InlineKeyboardButton("🔙 Back to Plans", callback_data="crypto_plans")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                crypto_text = f"""
        💰 INVESTMENT DEPOSIT - {crypto_type.upper()}

        🎯 Plan: {selected_plan['name']}
        💎 Cryptocurrency: {crypto_type.upper()}
        📈 Daily Return: {selected_plan['daily_return'] * 100:.2f}%

        🔒 PAYMENT DETAILS:

        Wallet Address:
        `{wallet_address}`

        💰 Investment Range:
        - Minimum: ${selected_plan['min_amount']:,} USD
        - Maximum: ${selected_plan['max_amount']:,} USD

        ⚠️ IMPORTANT: Send exact USD equivalent in {crypto_type.upper()}

        Click "✅ I've Sent Payment" after sending payment.
                """
                await query.message.edit_text(crypto_text, reply_markup=reply_markup, parse_mode='Markdown')
                
            except (ValueError, IndexError):
                await query.message.edit_text("❌ Error processing selection.", 
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Plans", callback_data="crypto_plans")]]))
        elif data.startswith('crypto_plan_'):
            try:
                plan_index = int(data.split('_')[2])
                # Show crypto type selection for the chosen plan
                keyboard = [
                    [InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data=f"crypto_type_{plan_index}_btc")],
                    [InlineKeyboardButton("Tether (USDT)", callback_data=f"crypto_type_{plan_index}_usdt")],
                    [InlineKeyboardButton("Ethereum (ETH)", callback_data=f"crypto_type_{plan_index}_eth")],
                    [InlineKeyboardButton("Solana (SOL)", callback_data=f"crypto_type_{plan_index}_sol")],
                    [InlineKeyboardButton("Toncoin (TON)", callback_data=f"crypto_type_{plan_index}_ton")],
                    [InlineKeyboardButton("🔙 Plans", callback_data="crypto_plans")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Fix the plan access
                plan_list = [InvestmentPlan.CORE.value, InvestmentPlan.GROWTH.value, InvestmentPlan.ALPHA.value]
                selected_plan = plan_list[plan_index]
                plan_names = ['Core (Starter)', 'Growth (Balanced)', 'Alpha (Premium)']
                
                await query.message.edit_text(
                    f"💎 {plan_names[plan_index]} PLAN\n\n"
                    f"Select your preferred cryptocurrency:\n\n"
                    f"💰 *Plan Details:*\n"
                    f"• Minimum: ${selected_plan['min_amount']:,.0f}\n"
                    f"• Daily Return: {selected_plan['daily_return']*100:.2f}%\n\n"
                    f"Choose your crypto below:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except (ValueError, IndexError, KeyError):
                await query.message.edit_text(
                    "❌ Error loading plan details.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Invest", callback_data="invest_menu")]])
                )
        else:
            # Unknown action fallback
            keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "❌ Unknown action. Returning to main menu.",
                reply_markup=reply_markup
            )
    
    except Exception as e:
        logging.error(f"Error in button_callback for data '{data}': {e}")
        keyboard = [[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "❌ An error occurred. Please try again or contact support.",
            reply_markup=reply_markup
        )
    
async def show_referral_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's referral information and program details"""
    query = update.callback_query
    user = query.from_user
    user_data = get_user_from_db(user.id)
    
    if not user_data:
        await query.message.edit_text(
            "❌ No user data found. Please register first.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]])
        )
        return
    
    referral_code = user_data[11] if len(user_data) > 11 else "Not generated"
    
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*), COALESCE(SUM(bonus_amount), 0)
        FROM referrals WHERE referrer_id = ?
    ''', (user.id,))
    referral_count, total_bonus = cursor.fetchone()
    conn.close()
    
    referral_text = f"""
👥 REFERRAL PROGRAM - EARN 5% COMMISSION

🎁 Your Referral Code: `{referral_code}`

📊 Your Stats:
• Total Referrals: {referral_count}
• Total Earned: ${total_bonus:,.2f}

💰 How It Works:
1. Share your code with friends
2. They register with: /start {referral_code}
3. Earn 5% on their investments
4. Bonus added to your balance instantly

🚀 Example: Friend invests $1,000 → You earn $50

📢 Share This:
"Join Alpha Vault for daily profits! Use code: {referral_code}"

Start referring to boost your earnings!
    """
    
    keyboard = [
        [InlineKeyboardButton("📢 Share Code", switch_inline_query=f"Join Alpha Vault! Use code: {referral_code}")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="show_leaderboard")],
        [InlineKeyboardButton("🔙 Profile", callback_data="show_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        referral_text.strip(),
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start for the main menu.")

def main():
    """Starts the bot."""
    # Create custom request with proxy
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
        # proxy_url="http://103.187.4.99:80",  # Uncomment if needed
    )
    
    # FIX: Use the request object
    application = Application.builder().token(BOT_TOKEN).request(request).build() 
    application.add_error_handler(error_handler)

    job_queue = application.job_queue
    create_stock_sales_table()
    create_dummy_leaderboard()
    migrate_stock_tables()  # Add this line
    
    # Add handlers ONCE (remove duplicates)

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("view_portfolio", portfolio_command))
    application.add_handler(CommandHandler("invest", invest_command))
    application.add_handler(CommandHandler("withdraw", withdraw_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))  # MAKE SURE THIS IS HERE
    application.add_handler(CommandHandler("reject_stock_sale", reject_stock_sale_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("confirm_investment", confirm_investment_command))
    application.add_handler(CommandHandler("confirm_stock", confirm_stock_investment_command))
    application.add_handler(CommandHandler("confirm_withdrawal", confirm_withdrawal_command))
    application.add_handler(CommandHandler("confirm_stock_sale", confirm_stock_sale_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    # Schedule the daily job at midnight UTC
    job_queue.run_daily(daily_profit_job, time=time(0, 0, 0))

    print("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
