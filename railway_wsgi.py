import asyncio
import logging
import os
from web_server import app, socketio
from websocket_manager import BinanceWebSocketManager
from liquidation_handler import LiquidationHandler
from funding_handler import FundingHandler
from trades_handler import TradesHandler
from main_visual_production import VisualLiquidationHandler, VisualFundingHandler, VisualTradesHandler, BinanceDataStreamVisualDynamic
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
stream_instance = None
loop = None

async def setup_and_run_streams():
    """Setup and run WebSocket streams"""
    global stream_instance
    
    logger.info("Setting up WebSocket streams...")
    
    # Initialize the stream instance
    stream_instance = BinanceDataStreamVisualDynamic()
    
    # Make it available for imports
    import main_visual_production
    main_visual_production.stream_instance = stream_instance
    
    # Start the streams
    await stream_instance.start()

async def run_async_tasks():
    """Run async tasks"""
    global loop
    loop = asyncio.get_event_loop()
    
    try:
        await setup_and_run_streams()
    except asyncio.CancelledError:
        logger.info("Async tasks cancelled")
        if stream_instance:
            stream_instance.stop()

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
    if stream_instance:
        stream_instance.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting server on port {port}")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)