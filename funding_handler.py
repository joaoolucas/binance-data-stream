import logging
from datetime import datetime
from typing import Dict
from colorama import Fore, Style, init

init(autoreset=True)
logger = logging.getLogger(__name__)


class FundingHandler:
    def __init__(self, min_funding_rate: float = 0.01):
        self.min_funding_rate = min_funding_rate
        self.last_rates = {}  # Track last seen rates to detect changes
        
    async def handle_funding_rate(self, data: Dict):
        """Process funding rate data from WebSocket markPrice stream"""
        try:
            symbol = data.get('s', 'Unknown')
            funding_rate = float(data.get('r', 0))
            timestamp = data.get('E', 0)
            
            # For new symbols, always show the first rate
            is_new_symbol = symbol not in self.last_rates
            
            # Check if this is a new rate or rate has changed
            if not is_new_symbol and symbol in self.last_rates and self.last_rates[symbol] == funding_rate:
                return  # Skip if rate hasn't changed
                
            self.last_rates[symbol] = funding_rate
            
            # Convert to percentage and annualized rate
            funding_rate_pct = funding_rate * 100
            annual_rate = funding_rate_pct * 3 * 365  # Funding every 8 hours
            
            # Check if rate is significant (using annual rate)
            if abs(annual_rate) >= self.min_funding_rate:
                self._print_funding_rate(symbol, funding_rate_pct, annual_rate, timestamp)
                
        except Exception as e:
            logger.error(f"Error processing funding rate data: {e}")
            
    def _print_funding_rate(self, symbol: str, funding_rate_pct: float, annual_rate: float, timestamp: int):
        """Print formatted funding rate information"""
        dt = datetime.fromtimestamp(timestamp / 1000)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Color based on annual rate
        if annual_rate > 50:
            rate_color = Fore.RED
            intensity = "🔥 EXTREME"
        elif annual_rate > 30:
            rate_color = Fore.YELLOW
            intensity = "⚠️  HIGH"
        elif annual_rate > 5:
            rate_color = Fore.CYAN
            intensity = "📊 MODERATE"
        elif annual_rate < -10:
            rate_color = Fore.GREEN
            intensity = "💚 NEGATIVE"
        else:
            rate_color = Fore.WHITE
            intensity = "➖ NEUTRAL"
            
        # Direction indicator
        if funding_rate_pct > 0:
            direction = "LONGS PAY SHORTS"
        else:
            direction = "SHORTS PAY LONGS"
            
        print(f"\n{Fore.MAGENTA}💰 FUNDING RATE {Fore.RESET}| "
              f"{time_str} | "
              f"{symbol} | "
              f"Rate: {rate_color}{funding_rate_pct:+.4f}%{Style.RESET_ALL} | "
              f"Annual: {rate_color}{annual_rate:+.1f}%{Style.RESET_ALL} | "
              f"{intensity} | "
              f"{direction}")
              
    @staticmethod
    def get_stream_names():
        """Get WebSocket stream names for BTC and ETH funding rates"""
        return [
            "btcusdt@markPrice",
            "ethusdt@markPrice"
        ]