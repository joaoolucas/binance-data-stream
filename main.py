import asyncio
import logging
import signal
from colorama import init

from websocket_manager import BinanceWebSocketManager
from liquidation_handler import LiquidationHandler
from funding_handler import FundingHandler
from trades_handler import TradesHandler

# Initialize colorama for Windows support
init()

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BinanceDataStream:
    def __init__(self):
        # Thresholds - modify these values to change filtering
        self.min_liquidation_usd = 100000  # Minimum liquidation size in USD
        self.min_trade_usd = 500000        # Minimum aggregated trade size per second in USD
        self.min_funding_rate = 0          # Minimum annual funding rate in %
        
        # Initialize components
        self.ws_manager = BinanceWebSocketManager()
        self.liquidation_handler = LiquidationHandler(self.min_liquidation_usd)
        self.funding_handler = FundingHandler(self.min_funding_rate)
        self.trades_handler = TradesHandler(self.min_trade_usd)
        
        self.running = False
        
    async def start(self):
        """Start all data streams"""
        self.running = True
        
        # Prepare subscriptions
        subscriptions = []
        
        # Liquidation streams
        for stream in self.liquidation_handler.get_stream_names():
            subscriptions.append({
                'stream': stream,
                'callback': self.liquidation_handler.handle_liquidation,
                'is_futures': True
            })
            
        # Trade streams (futures market to match liquidations)
        for stream in self.trades_handler.get_stream_names():
            subscriptions.append({
                'stream': stream,
                'callback': self.trades_handler.handle_trade,
                'is_futures': True
            })
            
        # Funding rate streams (futures market)
        for stream in self.funding_handler.get_stream_names():
            subscriptions.append({
                'stream': stream,
                'callback': self.funding_handler.handle_funding_rate,
                'is_futures': True
            })
        
        # Subscribe to WebSocket streams
        await self.ws_manager.subscribe_multiple(subscriptions)
        
        # Start the trade aggregation task
        trade_aggregation_task = asyncio.create_task(
            self.trades_handler.print_aggregated_trades()
        )
        
        # Keep the main task running
        try:
            while self.running:
                await asyncio.sleep(0.1)  # Faster response to interrupts
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            trade_aggregation_task.cancel()
            await self.ws_manager.close_all()
            
    def stop(self):
        """Stop all data streams"""
        print("\n\n🛑 Shutting down data streams...")
        self.running = False


async def main():
    """Main entry point"""
    stream = BinanceDataStream()
    
    try:
        await stream.start()
    except KeyboardInterrupt:
        stream.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        print("👋 Goodbye!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user")
        print("👋 Goodbye!")