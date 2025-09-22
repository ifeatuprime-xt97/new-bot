"""
Market data fetching and processing
"""
import logging
import random
from typing import Dict, Optional

class MarketDataManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Mock stock prices (replace with real API calls)
        self.mock_stock_prices = {
            'AAPL': 175.50, 'MSFT': 330.25, 'GOOGL': 140.75, 'AMZN': 145.80,
            'NVDA': 420.15, 'TSLA': 245.60, 'META': 295.40, 'NFLX': 440.20,
            'INTC': 45.30, 'AMD': 105.75, 'V': 240.80, 'JPM': 150.40,
            'JNJ': 165.90, 'WMT': 155.70, 'PG': 145.25, 'MA': 380.60,
            'HD': 320.45, 'UNH': 510.30, 'VZ': 38.75, 'DIS': 95.80
        }
        
        # Mock crypto prices
        self.mock_crypto_prices = {
            'btc': 42500.00, 'eth': 2650.00, 'usdt': 1.00,
            'sol': 95.50, 'ton': 2.45
        }
    
    def get_current_stock_price(self, ticker: str) -> float:
        """Get current stock price"""
        try:
            # Add some random variation to make it realistic
            base_price = self.mock_stock_prices.get(ticker.upper(), 100.0)
            variation = random.uniform(-0.05, 0.05)  # ±5% variation
            price = base_price * (1 + variation)
            return round(price, 2)
        except Exception as e:
            self.logger.error(f"Error getting price for {ticker}: {e}")
            return 0.0
    
    def get_current_crypto_price(self, crypto: str) -> float:
        """Get current crypto price"""
        try:
            base_price = self.mock_crypto_prices.get(crypto.lower(), 1.0)
            if crypto.lower() == 'usdt':
                return 1.00  # USDT is stable
            
            variation = random.uniform(-0.02, 0.02)  # ±2% variation
            price = base_price * (1 + variation)
            return round(price, 2)
        except Exception as e:
            self.logger.error(f"Error getting crypto price for {crypto}: {e}")
            return 0.0
    
    def calculate_stock_pnl(self, ticker: str, invested_amount: float, purchase_price: float) -> float:
        """Calculate stock P&L"""
        try:
            current_price = self.get_current_stock_price(ticker)
            if current_price <= 0 or purchase_price <= 0:
                return 0.0
            
            shares = invested_amount / purchase_price
            current_value = shares * current_price
            pnl = current_value - invested_amount
            return round(pnl, 2)
        except Exception as e:
            self.logger.error(f"Error calculating P&L for {ticker}: {e}")
            return 0.0
    
    def get_top_crypto_prices(self, limit: int = 20) -> Dict[str, float]:
        """Get top crypto prices"""
        try:
            # Expand the crypto list for live prices display
            extended_cryptos = {
                'bitcoin': 42500.00, 'ethereum': 2650.00, 'tether': 1.00,
                'binance-coin': 315.80, 'solana': 95.50, 'cardano': 0.48,
                'dogecoin': 0.088, 'polygon': 0.85, 'avalanche': 38.50,
                'chainlink': 14.75, 'uniswap': 6.80, 'litecoin': 72.30,
                'bitcoin-cash': 245.60, 'stellar': 0.115, 'filecoin': 5.45,
                'tron': 0.105, 'cosmos': 9.85, 'monero': 158.70,
                'ethereum-classic': 20.45, 'near': 2.15
            }
            
            # Add random variations
            result = {}
            for crypto, base_price in list(extended_cryptos.items())[:limit]:
                if crypto == 'tether':
                    result[crypto] = 1.00
                else:
                    variation = random.uniform(-0.03, 0.03)
                    result[crypto] = round(base_price * (1 + variation), 4)
            
            return result
        except Exception as e:
            self.logger.error(f"Error getting crypto prices: {e}")
            return {}
    
    def get_stock_list_prices(self, tickers: list) -> Dict[str, float]:
        """Get prices for a list of stocks"""
        result = {}
        for ticker in tickers:
            result[ticker] = self.get_current_stock_price(ticker)
        return result

# Global instance
market = MarketDataManager()