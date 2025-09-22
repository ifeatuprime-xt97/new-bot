"""
Market data fetching and processing
"""
import yfinance as yf
import requests
import logging
from typing import List, Dict, Optional
from config import ALL_STOCKS

class MarketDataManager:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
    
    def get_stock_info(self, tickers: List[str]) -> List[Dict]:
        """Get stock information for multiple tickers"""
        stocks_info = []
        
        if not tickers:
            return stocks_info
        
        try:
            # Batch fetch for efficiency
            data = yf.Tickers(' '.join(tickers))
            
            for ticker in tickers:
                try:
                    info = data.tickers[ticker.upper()].info
                    current_price = info.get('regularMarketPrice')
                    previous_close = info.get('previousClose')
                    
                    if current_price and previous_close:
                        price_change_percent = ((current_price - previous_close) / previous_close) * 100
                        change_emoji = '▲' if price_change_percent >= 0 else '▼'
                        price_change_text = f"{change_emoji} {price_change_percent:.2f}%"
                    else:
                        price_change_text = "N/A"
                    
                    stocks_info.append({
                        'ticker': ticker,
                        'name': info.get('shortName', ticker),
                        'price': f"${current_price:,.2f}" if current_price else "N/A",
                        'change': price_change_text,
                        'raw_price': current_price
                    })
                except Exception as e:
                    logging.error(f"Error fetching data for {ticker}: {e}")
                    stocks_info.append({
                        'ticker': ticker,
                        'name': ticker,
                        'price': "Error",
                        'change': "N/A",
                        'raw_price': 0
                    })
        
        except Exception as e:
            logging.error(f"Error in batch stock fetch: {e}")
            # Fallback to individual fetches
            for ticker in tickers:
                stocks_info.append({
                    'ticker': ticker,
                    'name': ticker,
                    'price': "Error",
                    'change': "N/A",
                    'raw_price': 0
                })
        
        return stocks_info
    
    def get_current_stock_price(self, ticker: str) -> float:
        """Get current price for a single stock"""
        try:
            stock = yf.Ticker(ticker)
            price = stock.info.get('regularMarketPrice', 0)
            return float(price) if price else 0.0
        except Exception as e:
            logging.error(f"Error fetching price for {ticker}: {e}")
            return 0.0
    
    def calculate_stock_pnl(self, ticker: str, amount_invested: float, purchase_price: float) -> float:
        """Calculate profit/loss for a stock position"""
        try:
            current_price = self.get_current_stock_price(ticker)
            if current_price <= 0:
                return 0.0
            
            shares = amount_invested / purchase_price
            current_value = shares * current_price
            return current_value - amount_invested
        
        except Exception as e:
            logging.error(f"Error calculating P&L for {ticker}: {e}")
            return 0.0
    
    def get_crypto_prices(self, limit: int = 20) -> Optional[List[Dict]]:
        """Get top cryptocurrency prices from CoinGecko"""
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': limit,
                'page': 1,
                'sparkline': False,
                'price_change_percentage': '24h'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            crypto_info = []
            for item in data:
                price_change = item.get('price_change_percentage_24h_in_currency')
                change_emoji = '▲' if price_change and price_change >= 0 else '▼'
                
                crypto_info.append({
                    'name': item.get('name', 'N/A'),
                    'symbol': item.get('symbol', 'N/A').upper(),
                    'price': f"${item.get('current_price', 0):,.2f}",
                    'change': f"{change_emoji} {price_change:.2f}%" if price_change else "N/A"
                })
            
            return crypto_info
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching crypto prices: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error in crypto price fetch: {e}")
            return None

# Global market data instance
market = MarketDataManager()