"""
Database operations for the trading bot
"""
import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path: str = 'trading_bot.db'):
        self.db_path = db_path
        self.init_database()
        self.ensure_admin_tables()
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logging.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize all database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
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
            
            # Investments table
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
            
            # Stock investments table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_investments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount_invested_usd REAL,
                    stock_ticker TEXT,
                    purchase_price REAL,
                    investment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    confirmed_date TIMESTAMP,
                    confirmed_by INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Withdrawals table
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
            
            # Stock sales table
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
                    processed_date TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (stock_investment_id) REFERENCES stock_investments (id)
                )
            ''')
            
            # Referrals table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER,
                    referral_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bonus_amount REAL DEFAULT 0,
                    FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                    FOREIGN KEY (referred_id) REFERENCES users (user_id)
                )
            ''')
            
            # Admin logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_balance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    target_user_id INTEGER,
                    action_type TEXT,
                    amount REAL,
                    old_balance REAL,
                    new_balance REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT,
                    FOREIGN KEY (admin_id) REFERENCES users (user_id),
                    FOREIGN KEY (target_user_id) REFERENCES users (user_id)
                )
            ''')
            
            # Leaderboard dummy data
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
            
            conn.commit()
            self._populate_dummy_leaderboard()
    
    def _populate_dummy_leaderboard(self):
        """Populate dummy leaderboard data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM leaderboard_dummy')
            if cursor.fetchone()[0] == 0:
                sample_data = [
                    ('AlphaWhale_Pro', 1, 125670.50, 23420.30, 98.7),
                    ('CryptoQueen_X', 2, 98750.25, 18930.80, 97.2),
                    ('DiamondHands88', 3, 78450.90, 15640.20, 96.1),
                    ('MoonMission_X', 4, 65430.75, 13450.40, 95.4),
                    ('BullRunLegend', 5, 52340.40, 11230.60, 94.8),
                    ('TradeMaster_7', 6, 41280.15, 9230.25, 93.2),
                    ('ProfitPilot', 7, 34560.80, 7840.90, 92.5),
                    ('SmartMoney_X', 8, 29870.45, 6540.30, 91.8),
                    ('GrowthGuru', 9, 25640.20, 5230.70, 91.1),
                    ('WealthWizard', 10, 21430.95, 4320.15, 90.4),
                ]
                
                cursor.executemany('''
                    INSERT INTO leaderboard_dummy (username, rank_position, total_earnings, weekly_earnings, success_rate)
                    VALUES (?, ?, ?, ?, ?)
                ''', sample_data)
                conn.commit()
    
    def ensure_admin_tables(self):
        """Ensure admin-related tables exist"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
    def get_user(self, user_id: int) -> Optional[Tuple]:
        """Get user data by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            return cursor.fetchone()
    
    def create_or_update_user(self, user_id: int, username: str, first_name: str, 
                             full_name: str = None, email: str = None, referred_by_id: int = None) -> bool:
        """Create new user or update existing one"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if user exists
                cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
                user_exists = cursor.fetchone()
                
                if user_exists:
                    cursor.execute('''
                        UPDATE users SET username = ?, first_name = ?, full_name = ?, email = ? 
                        WHERE user_id = ?
                    ''', (username, first_name, full_name, email, user_id))
                else:
                    import random
                    referral_code = f"AV{user_id}{random.randint(100, 999)}"
                    cursor.execute('''
                        INSERT INTO users (user_id, username, first_name, full_name, email, referral_code, referred_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, username, first_name, full_name, email, referral_code, referred_by_id))
                    
                    # Add referral record if referred
                    if referred_by_id:
                        cursor.execute('''
                            INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)
                        ''', (referred_by_id, user_id))
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error creating/updating user {user_id}: {e}")
            return False
    
    def add_stock(self, user_id, ticker, amount, price):
        """Add stock investment to database"""
        try:
            shares = amount / price if price > 0 else 0
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO stock_investments 
                    (user_id, stock_ticker, amount_invested_usd, purchase_price, shares_owned, 
                    investment_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, ticker, amount, price, shares,
                    datetime.now().isoformat(), 'confirmed'
                ))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding stock: {e}")
            return False

    def add_investment(self, user_id: int, amount: float, crypto_type: str, 
                      wallet_address: str, transaction_id: str, plan: str, notes: str = None) -> bool:
        """Add new investment record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO investments (user_id, amount, crypto_type, wallet_address, transaction_id, plan, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, amount, crypto_type, wallet_address, transaction_id, plan, notes))
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error adding investment: {e}")
            return False
    
    def confirm_investment(self, investment_id: int, admin_id: int) -> bool:
        """Confirm a pending investment"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get investment details
                cursor.execute('''
                    SELECT user_id, amount, plan FROM investments 
                    WHERE id = ? AND status = 'pending'
                ''', (investment_id,))
                investment = cursor.fetchone()
                
                if not investment:
                    return False
                
                user_id, amount, plan = investment
                
                # Update investment status
                cursor.execute('''
                    UPDATE investments SET status = 'confirmed' WHERE id = ?
                ''', (investment_id,))
                
                # Update user balance and plan
                cursor.execute('''
                    UPDATE users 
                    SET total_invested = total_invested + ?, 
                        current_balance = current_balance + ?,
                        plan = ?,
                        last_profit_update = ?
                    WHERE user_id = ?
                ''', (amount, amount, plan, datetime.now().isoformat(), user_id))
                
                conn.commit()
                return True
        except Exception as e:
            logging.error(f"Error confirming investment {investment_id}: {e}")
            return False
    
    def get_pending_investments(self) -> List[Tuple]:
        """Get all pending investments"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT i.id, i.user_id, u.username, u.full_name, u.email, 
                       i.amount, i.crypto_type, i.transaction_id, i.investment_date, i.notes
                FROM investments i
                JOIN users u ON i.user_id = u.user_id
                WHERE i.status = 'pending'
                ORDER BY i.investment_date DESC
            ''')
            return cursor.fetchall()
    
    def get_pending_withdrawals(self) -> List[Tuple]:
        """Get all pending withdrawals"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT w.id, w.user_id, u.username, u.full_name, u.email,
                       w.amount, w.wallet_address, w.withdrawal_date
                FROM withdrawals w
                JOIN users u ON w.user_id = u.user_id
                WHERE w.status = 'pending'
                ORDER BY w.withdrawal_date DESC
            ''')
            return cursor.fetchall()
    
    def get_user_stats(self) -> Dict[str, Any]:
        """Get overall user statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Total users
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['total_users'] = cursor.fetchone()[0]
            
            # Active investors
            cursor.execute('SELECT COUNT(*) FROM users WHERE total_invested > 0')
            stats['active_investors'] = cursor.fetchone()[0]
            
            # Total investments
            cursor.execute('SELECT SUM(total_invested) FROM users')
            stats['total_crypto_invested'] = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(amount_invested_usd) FROM stock_investments WHERE status = "confirmed"')
            stats['total_stock_invested'] = cursor.fetchone()[0] or 0
            
            # Total balances
            cursor.execute('SELECT SUM(current_balance) FROM users')
            stats['total_balances'] = cursor.fetchone()[0] or 0
            
            # Pending items
            cursor.execute('SELECT COUNT(*) FROM investments WHERE status = "pending"')
            stats['pending_investments'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM withdrawals WHERE status = "pending"')
            stats['pending_withdrawals'] = cursor.fetchone()[0]
            
            return stats
        def add_manual_stock(self, admin_id, user_id, ticker, amount, price):
            """Add manual stock investment by admin"""
            try:
                shares = amount / price
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO stock_investments 
                        (user_id, stock_ticker, amount_invested_usd, purchase_price, shares_owned, 
                        investment_date, status, confirmed_by, confirmed_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, ticker, amount, price, shares,
                        datetime.now().isoformat(), 'confirmed', admin_id, datetime.now().isoformat()
                    ))
                    
                    # Update user's total invested
                    cursor.execute('''
                        UPDATE users 
                        SET total_invested = total_invested + ?
                        WHERE user_id = ?
                    ''', (amount, user_id))
                    
                    conn.commit()
                    return True
            except Exception as e:
                logging.error(f"Error adding manual stock: {e}")
                return False
# Global database instance
db = DatabaseManager()