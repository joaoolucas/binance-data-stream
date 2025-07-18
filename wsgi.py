import threading
import time
import logging
from web_server import app, socketio
from main_visual_production import run_async_in_thread

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting WSGI application...")

# Start the data streams in a separate thread
data_thread = threading.Thread(target=run_async_in_thread, daemon=True)
data_thread.start()

# Give the data thread time to start
time.sleep(2)

# Export the app for gunicorn
application = app

if __name__ == "__main__":
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)