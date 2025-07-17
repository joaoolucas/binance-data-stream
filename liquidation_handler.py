import logging
from datetime import datetime
from typing import Dict, Optional
from colorama import Fore, Style, init

init(autoreset=True)
logger = logging.getLogger(__name__)


class LiquidationHandler:
    def __init__(self, min_usd_value: float = 100000):
        self.min_usd_value = min_usd_value
        self.symbols_of_interest = []  # Will be set dynamically
        
    async def handle_liquidation(self, data: Dict):
        """Process liquidation order data from Binance futures"""
        try:
            # The !forceOrder@arr stream returns data in this format:
            # {"e":"forceOrder","E":123456789,"o":{"s":"BTCUSDT","S":"SELL","o":"LIMIT","f":"IOC","q":"0.001","p":"9910.00","ap":"9910.00","x":"FILLED","l":"0.001","z":"0.001","T":123456789}}
            
            # Check if this is a liquidation event
            if data.get('e') == 'forceOrder' and 'o' in data:
                order_data = data.get('o', {})
            else:
                # Silently ignore unexpected format
                return
                
            symbol = order_data.get('s', 'Unknown')
            
            # Filter for symbols of interest (if list is not empty)
            if self.symbols_of_interest and symbol not in self.symbols_of_interest:
                return
                
            side = order_data.get('S', 'Unknown')
            price = float(order_data.get('p', 0))
            quantity = float(order_data.get('z', 0))  # Use filled quantity
            timestamp = data.get('E', 0)  # Use event time from outer object
            
            # Calculate USD value
            usd_value = price * quantity
            
            # Only process large liquidations
            if usd_value >= self.min_usd_value:
                self._print_liquidation(symbol, side, price, quantity, usd_value, timestamp)
                
        except Exception as e:
            logger.error(f"Error processing liquidation data: {e}")
            
    def _print_liquidation(self, symbol: str, side: str, price: float, 
                          quantity: float, usd_value: float, timestamp: int):
        """Print formatted liquidation information"""
        dt = datetime.fromtimestamp(timestamp / 1000)
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Format symbol (remove USDT)
        symbol_display = symbol.replace('USDT', '')
        
        # Determine liquidation type and color
        if side == 'SELL':
            liq_type = "LONG LIQ"
            bg_color = Fore.BLUE
            icon = "🔻"
        else:
            liq_type = "SHORT LIQ"
            bg_color = Fore.MAGENTA
            icon = "🔺"
            
        # Format USD value
        if usd_value >= 1_000_000:
            value_str = f"${usd_value/1_000_000:.2f}M"
            attrs = Style.BRIGHT  # Bold for large liquidations
        else:
            value_str = f"${usd_value/1_000:.0f}K"
            attrs = ""
            
        print(f"\n{bg_color}{attrs}💥 {liq_type} {Style.RESET_ALL}| "
              f"{time_str} | "
              f"{symbol_display} | "
              f"Price: ${price:,.2f} | "
              f"{Fore.YELLOW}{attrs}{value_str}{Style.RESET_ALL}")
              
    @staticmethod
    def get_stream_names():
        """Get WebSocket stream names for all liquidations"""
        # Using the array format to get all liquidations
        return ["!forceOrder@arr"]