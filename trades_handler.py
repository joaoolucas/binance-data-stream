import logging
import asyncio
from datetime import datetime
from typing import Dict, Tuple
from colorama import Fore, Style, init

init(autoreset=True)
logger = logging.getLogger(__name__)


class TradesHandler:
    def __init__(self, min_usd_value: float = 500000):
        self.min_usd_value = min_usd_value
        self.trade_buckets: Dict[Tuple[str, str, bool], float] = {}
        self.last_check_time = datetime.utcnow()
        
    async def handle_trade(self, data: Dict):
        """Process aggregated trade data from Binance"""
        try:
            symbol = data.get('s', 'Unknown')
            price = float(data.get('p', 0))
            quantity = float(data.get('q', 0))
            timestamp = data.get('T', 0)
            is_buyer_maker = data.get('m', False)
            
            # Calculate USD value
            usd_value = price * quantity
            
            # Get time bucket (second precision)
            dt = datetime.fromtimestamp(timestamp / 1000)
            time_bucket = dt.strftime('%H:%M:%S')
            
            # Format symbol
            symbol_display = symbol.replace('USDT', '')
            
            # Add to bucket
            trade_key = (symbol_display, time_bucket, is_buyer_maker)
            self.trade_buckets[trade_key] = self.trade_buckets.get(trade_key, 0) + usd_value
                
        except Exception as e:
            logger.error(f"Error processing trade data: {e}")
            
    async def print_aggregated_trades(self):
        """Check and print aggregated trades every second"""
        while True:
            await asyncio.sleep(1)
            await self._check_and_print_trades()
            
    async def _check_and_print_trades(self):
        """Check buckets and print trades that exceed threshold"""
        current_time = datetime.utcnow().strftime("%H:%M:%S")
        deletions = []
        
        for trade_key, usd_total in self.trade_buckets.items():
            symbol, time_bucket, is_buyer_maker = trade_key
            
            # Only process completed seconds
            if time_bucket < current_time and usd_total >= self.min_usd_value:
                self._print_aggregated_trade(symbol, time_bucket, usd_total, is_buyer_maker)
                deletions.append(trade_key)
                
        # Clean up printed trades
        for key in deletions:
            del self.trade_buckets[key]
            
        # Clean up old buckets (older than 5 seconds)
        current_dt = datetime.utcnow()
        old_keys = []
        for trade_key in self.trade_buckets.keys():
            _, time_bucket, _ = trade_key
            try:
                bucket_time = datetime.strptime(f"{current_dt.date()} {time_bucket}", "%Y-%m-%d %H:%M:%S")
                if (current_dt - bucket_time).total_seconds() > 5:
                    old_keys.append(trade_key)
            except:
                pass
                
        for key in old_keys:
            del self.trade_buckets[key]
            
    def _print_aggregated_trade(self, symbol: str, time_bucket: str, usd_total: float, is_buyer_maker: bool):
        """Print formatted aggregated trade information"""
        # Determine trade direction and color
        if is_buyer_maker:
            direction = "SELL"
            bg_color = Fore.MAGENTA
            icon = "🔻"
        else:
            direction = "BUY"
            bg_color = Fore.BLUE
            icon = "🔺"
            
        # Format USD value
        if usd_total >= 3_000_000:
            value_str = f"${usd_total/1_000_000:.2f}M"
            # Blinking for very large trades
            prefix = "\033[5m"
            suffix = "\033[0m"
        else:
            value_str = f"${usd_total/1_000_000:.2f}M"
            prefix = ""
            suffix = ""
            
        print(f"\n{bg_color}{Style.BRIGHT}{prefix}{icon} {direction} {Style.RESET_ALL}{suffix}| "
              f"{time_bucket} | "
              f"{symbol} | "
              f"{Fore.YELLOW}{Style.BRIGHT}{value_str}{Style.RESET_ALL}")
              
    @staticmethod
    def get_stream_names():
        """Get WebSocket stream names for BTC and ETH trades"""
        return [
            "btcusdt@aggTrade",
            "ethusdt@aggTrade"
        ]