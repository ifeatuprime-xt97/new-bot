"""
Configuration settings for the trading bot
"""
import os
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List

# Bot Configuration
BOT_TOKEN = "8295756385:AAHNVHS4zMXYKVylnLjiWbJ_4LtZiWcKhyI"
ADMIN_USER_IDS = [6417609151]

# Investment Plans
class InvestmentPlan(Enum):
    CORE = {"name": "Core (Starter)", "min_amount": 1000, "max_amount": 15000, "daily_return": 0.0143}
    GROWTH = {"name": "Growth (Balanced)", "min_amount": 20000, "max_amount": 80000, "daily_return": 0.0214}
    ALPHA = {"name": "Alpha (Premium)", "min_amount": 100000, "max_amount": float('inf'), "daily_return": 0.0286}

# Crypto Wallet Addresses
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
        '0x742d35Cc6B88F86E8C7CB3C8B3D0F6C1C2E6a4b1',
        '0x1bde33327a27459C9237651871822895632231f2',
        '0x2c4D7962d385D23D3e8a4D42b584DBA3742d4834',
        '0x3eA6E5A8e21a22453e9a4f3C15c1bFa38437A99E',
        '0x4aB1E297A649f7eA23aA1192323f4aE8e3B4a2b6'
    ]
}

# Stock Lists
TECH_STOCKS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'NFLX', 'INTC', 'AMD']
NON_TECH_STOCKS = ['V', 'JPM', 'JNJ', 'WMT', 'PG', 'MA', 'HD', 'UNH', 'VZ', 'DIS']
ALL_STOCKS = TECH_STOCKS + NON_TECH_STOCKS

# Conversation States
REGISTER_NAME, REGISTER_EMAIL = range(2)
AWAITING_PAYMENT_DETAILS, AWAITING_STOCK_PAYMENT_DETAILS = range(2, 4)
AWAITING_WITHDRAW_AMOUNT, AWAITING_WITHDRAW_ADDRESS = range(4, 6)
AWAITING_BROADCAST_MESSAGE, AWAITING_STOCK_SHARES = range(6, 8)