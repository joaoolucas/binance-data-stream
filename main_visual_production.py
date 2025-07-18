import asyncio
import logging
import signal
from colorama import init
import threading
import time

from websocket_manager import BinanceWebSocketManager
from liquidation_handler import LiquidationHandler
from funding_handler import FundingHandler
from trades_handler import TradesHandler
from web_server import app, socketio, emit_liquidation, emit_trade, emit_funding

# Initialize colorama for Windows support
init()

# Configure logging
import os
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Available symbols
ALL_SYMBOLS = ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'XRP', 'ADA', 'AVAX']


class VisualLiquidationHandler(LiquidationHandler):
    def _print_liquidation(self, symbol, side, price, quantity, usd_value, timestamp):
        # Call parent to print to console
        super()._print_liquidation(symbol, side, price, quantity, usd_value, timestamp)
        
        # Emit to web interface
        emit_liquidation({
            'symbol': symbol.replace('USDT', ''),
            'side': side,
            'price': price,
            'quantity': quantity,
            'usdValue': usd_value,
            'timestamp': timestamp
        })


class VisualFundingHandler(FundingHandler):
    def __init__(self, min_funding_rate: float = 0.01):
        super().__init__(min_funding_rate)
        self.current_rates = {}  # Store current rates for all symbols
        
    def _print_funding_rate(self, symbol, funding_rate_pct, annual_rate, timestamp):
        # Call parent to print to console
        super()._print_funding_rate(symbol, funding_rate_pct, annual_rate, timestamp)
        
        # Store the current rate
        self.current_rates[symbol] = {
            'rate': funding_rate_pct,
            'annual': annual_rate,
            'direction': "LONGS PAY SHORTS" if funding_rate_pct > 0 else "SHORTS PAY LONGS",
            'timestamp': timestamp
        }
        
        # Emit to web interface
        emit_funding(symbol, self.current_rates[symbol])


class VisualTradesHandler(TradesHandler):
    def _print_aggregated_trade(self, symbol, time_bucket, usd_total, is_buyer_maker):
        # Call parent to print to console
        super()._print_aggregated_trade(symbol, time_bucket, usd_total, is_buyer_maker)
        
        # Emit to web interface
        emit_trade({
            'symbol': symbol,
            'timestr': time_bucket,
            'usdValue': usd_total,
            'direction': 'SELL' if is_buyer_maker else 'BUY'
        })


class BinanceDataStreamVisualDynamic:
    def __init__(self):
        # Default settings
        self.active_symbols = ['BTC', 'ETH']
        self.min_liquidation_usd = 100000
        self.min_trade_usd = 500000
        self.min_funding_rate = 10
        
        # Initialize components
        self.ws_manager = BinanceWebSocketManager()
        self.liquidation_handler = VisualLiquidationHandler(self.min_liquidation_usd)
        self.funding_handler = VisualFundingHandler(self.min_funding_rate)
        self.trades_handler = VisualTradesHandler(self.min_trade_usd)
        
        self.running = False
        self.current_subscriptions = {}
        self.update_queue = asyncio.Queue()
        self.loop = None
        
    def update_settings(self, symbols=None, min_liquidation=None, min_trade=None):
        """Update settings dynamically - thread safe"""
        update_data = {}
        
        if symbols is not None:
            self.active_symbols = symbols
            update_data['symbols'] = symbols
            print(f"Updated symbols: {symbols}")
            
        if min_liquidation is not None:
            self.min_liquidation_usd = min_liquidation
            self.liquidation_handler.min_usd_value = min_liquidation
            print(f"Updated min liquidation: ${min_liquidation}")
            
        if min_trade is not None:
            self.min_trade_usd = min_trade
            self.trades_handler.min_usd_value = min_trade
            print(f"Updated min trade: ${min_trade}")
            
        # Queue the update for the async loop to handle
        if self.loop and update_data:
            asyncio.run_coroutine_threadsafe(
                self.update_queue.put(update_data),
                self.loop
            )
        
    def send_current_funding_rates(self):
        """Send current funding rates for active symbols"""
        for symbol in self.active_symbols:
            symbol_full = f"{symbol}USDT"
            if symbol_full in self.funding_handler.current_rates:
                emit_funding(symbol_full, self.funding_handler.current_rates[symbol_full])
    
    async def update_streams(self):
        """Update WebSocket streams based on active symbols"""
        # Close existing connections that are no longer needed
        for stream_name in list(self.current_subscriptions.keys()):
            symbol = stream_name.split('@')[0].upper()
            if symbol.replace('USDT', '') not in self.active_symbols:
                # Close this stream
                if stream_name in self.ws_manager.connections:
                    await self.ws_manager.connections[stream_name].close()
                    del self.ws_manager.connections[stream_name]
                    del self.ws_manager.callbacks[stream_name]
                    del self.current_subscriptions[stream_name]
                    print(f"Closed stream: {stream_name}")
        
        # Add new streams
        new_subscriptions = []
        
        for symbol in self.active_symbols:
            symbol_lower = symbol.lower() + 'usdt'
            
            # Trade stream
            stream_name = f"{symbol_lower}@aggTrade"
            if stream_name not in self.current_subscriptions:
                new_subscriptions.append({
                    'stream': stream_name,
                    'callback': self.trades_handler.handle_trade,
                    'is_futures': True
                })
                self.current_subscriptions[stream_name] = True
                
            # Funding stream
            stream_name = f"{symbol_lower}@markPrice"
            if stream_name not in self.current_subscriptions:
                new_subscriptions.append({
                    'stream': stream_name,
                    'callback': self.funding_handler.handle_funding_rate,
                    'is_futures': True
                })
                self.current_subscriptions[stream_name] = True
        
        # Subscribe to new streams
        if new_subscriptions:
            await self.ws_manager.subscribe_multiple(new_subscriptions)
            print(f"Added {len(new_subscriptions)} new streams")
            
        # Send current funding rates after a short delay to allow streams to connect
        await asyncio.sleep(0.5)
        self.send_current_funding_rates()
        
    async def start(self):
        """Start all data streams"""
        self.running = True
        self.loop = asyncio.get_running_loop()
        
        import os
        port = os.environ.get('PORT', 5000)
        print(f"📊 Web Interface: http://localhost:{port}")
        
        # Initial subscriptions
        subscriptions = []
        
        # Liquidation stream (all symbols)
        subscriptions.append({
            'stream': "!forceOrder@arr",
            'callback': self.liquidation_handler.handle_liquidation,
            'is_futures': True
        })
        self.current_subscriptions["!forceOrder@arr"] = True
        
        # Add streams for default symbols
        for symbol in self.active_symbols:
            symbol_lower = symbol.lower() + 'usdt'
            
            # Trade streams
            stream_name = f"{symbol_lower}@aggTrade"
            subscriptions.append({
                'stream': stream_name,
                'callback': self.trades_handler.handle_trade,
                'is_futures': True
            })
            self.current_subscriptions[stream_name] = True
            
            # Funding streams
            stream_name = f"{symbol_lower}@markPrice"
            subscriptions.append({
                'stream': stream_name,
                'callback': self.funding_handler.handle_funding_rate,
                'is_futures': True
            })
            self.current_subscriptions[stream_name] = True
        
        # Subscribe to WebSocket streams
        await self.ws_manager.subscribe_multiple(subscriptions)
        
        # Start the trade aggregation task
        trade_aggregation_task = asyncio.create_task(
            self.trades_handler.print_aggregated_trades()
        )
        
        # Start task to process updates from the queue
        update_task = asyncio.create_task(self._process_updates())
        
        # Keep the main task running
        try:
            while self.running:
                await asyncio.sleep(0.1)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            trade_aggregation_task.cancel()
            update_task.cancel()
            await self.ws_manager.close_all()
            
    async def _process_updates(self):
        """Process updates from the queue"""
        while self.running:
            try:
                # Wait for updates with timeout
                update = await asyncio.wait_for(self.update_queue.get(), timeout=1.0)
                if 'symbols' in update:
                    await self.update_streams()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing update: {e}")
            
    def stop(self):
        """Stop all data streams"""
        print("\n\n🛑 Shutting down data streams...")
        self.running = False


# Global instance for settings updates
stream_instance = None


@socketio.on('update_settings')
def handle_settings_update(data):
    """Handle settings update from client"""
    print(f"Settings update received: {data}")
    
    if stream_instance:
        symbols = data.get('symbols', [])
        min_liq = data.get('minLiquidation')
        min_trade = data.get('minTrade')
        
        stream_instance.update_settings(
            symbols=symbols if symbols else None,
            min_liquidation=min_liq,
            min_trade=min_trade
        )
        
        # Send current funding rates for the active symbols
        stream_instance.send_current_funding_rates()
    
    socketio.emit('settings_updated', {'status': 'ok'})


def run_async_in_thread():
    """Run the async data streams in a separate thread"""
    global stream_instance
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    stream_instance = BinanceDataStreamVisualDynamic()
    
    try:
        loop.run_until_complete(stream_instance.start())
    except Exception as e:
        logger.error(f"Error in async thread: {e}")
    finally:
        loop.close()


if __name__ == "__main__":
    # Start the data streams in a separate thread
    data_thread = threading.Thread(target=run_async_in_thread, daemon=True)
    data_thread.start()
    
    # Give the data thread time to start
    time.sleep(2)
    
    # Run the Flask app in the main thread
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)