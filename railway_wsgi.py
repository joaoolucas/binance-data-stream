import asyncio
import logging
import os
from web_server import app, socketio
from websocket_manager import BinanceWebSocketManager
from liquidation_handler import LiquidationHandler
from funding_handler import FundingHandler
from trades_handler import TradesHandler
from main_visual_production import VisualLiquidationHandler, VisualFundingHandler, VisualTradesHandler
import signal
import sys

# Configure logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
ws_manager = None
handlers = None
loop = None
subscriptions = []

async def setup_streams():
    """Setup WebSocket streams"""
    global ws_manager, handlers, subscriptions
    
    logger.info("Setting up WebSocket streams...")
    
    # Initialize components
    ws_manager = BinanceWebSocketManager()
    handlers = {
        'liquidation': VisualLiquidationHandler(100000),
        'funding': VisualFundingHandler(10),
        'trades': VisualTradesHandler(500000)
    }
    
    # Subscribe to liquidation stream (all symbols)
    subscriptions = [{
        'stream': "!forceOrder@arr",
        'callback': handlers['liquidation'].handle_liquidation,
        'is_futures': True
    }]
    
    # Add streams for default symbols
    default_symbols = ['BTC', 'ETH']
    for symbol in default_symbols:
        symbol_lower = symbol.lower() + 'usdt'
        
        # Trade streams
        subscriptions.append({
            'stream': f"{symbol_lower}@aggTrade",
            'callback': handlers['trades'].handle_trade,
            'is_futures': True
        })
        
        # Funding streams
        subscriptions.append({
            'stream': f"{symbol_lower}@markPrice",
            'callback': handlers['funding'].handle_funding_rate,
            'is_futures': True
        })
    
    logger.info(f"Subscribing to {len(subscriptions)} streams...")
    await ws_manager.subscribe_multiple(subscriptions)
    logger.info("WebSocket streams setup complete!")

async def run_async_tasks():
    """Run async tasks"""
    global loop
    loop = asyncio.get_event_loop()
    
    # Setup streams
    await setup_streams()
    
    # Start trade aggregation task
    trade_task = asyncio.create_task(handlers['trades'].print_aggregated_trades())
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        logger.info("Async tasks cancelled")
        trade_task.cancel()
        if ws_manager:
            await ws_manager.close_all()

def run_in_thread():
    """Run async code in a thread"""
    asyncio.run(run_async_tasks())

# Start async tasks in a thread
import threading
async_thread = threading.Thread(target=run_in_thread, daemon=True)
async_thread.start()

# Export the app for gunicorn
application = app

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    logger.info('Shutting down gracefully...')
    if ws_manager and loop:
        asyncio.run_coroutine_threadsafe(ws_manager.close_all(), loop)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)