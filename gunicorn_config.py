import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"

# Worker processes
workers = 1
worker_class = 'gevent'
worker_connections = 1000

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Timeout
timeout = 120
keepalive = 5

# Process naming
proc_name = 'binance-data-stream'

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL/Security
keyfile = None
certfile = None

# Reload
reload = False