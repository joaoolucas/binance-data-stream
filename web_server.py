from flask import Flask, render_template, request
from flask_socketio import SocketIO
from flask_cors import CORS
import asyncio
from threading import Thread
import json
from datetime import datetime
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Store recent events for new connections
recent_events = {
    'liquidations': [],
    'trades': [],
    'funding': {}
}
MAX_RECENT_EVENTS = 50


@app.route('/')
def index():
    return render_template('index.html')


def emit_liquidation(data):
    """Emit liquidation event to all connected clients"""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'data': data
    }
    recent_events['liquidations'].append(event)
    if len(recent_events['liquidations']) > MAX_RECENT_EVENTS:
        recent_events['liquidations'].pop(0)
    
    socketio.emit('liquidation', event)


def emit_trade(data):
    """Emit trade event to all connected clients"""
    event = {
        'timestamp': datetime.utcnow().isoformat(),
        'data': data
    }
    recent_events['trades'].append(event)
    if len(recent_events['trades']) > MAX_RECENT_EVENTS:
        recent_events['trades'].pop(0)
    
    socketio.emit('trade', event)


def emit_funding(symbol, data):
    """Emit funding rate event to all connected clients"""
    recent_events['funding'][symbol] = {
        'timestamp': datetime.utcnow().isoformat(),
        'data': data
    }
    socketio.emit('funding', {'symbol': symbol, 'data': data})


@socketio.on('connect')
def handle_connect():
    """Send recent events to newly connected client"""
    print('Client connected')
    
    # Send recent liquidations
    for event in recent_events['liquidations'][-10:]:
        socketio.emit('liquidation', event, room=request.sid)
    
    # Send recent trades
    for event in recent_events['trades'][-10:]:
        socketio.emit('trade', event, room=request.sid)
    
    # Send current funding rates
    for symbol, data in recent_events['funding'].items():
        socketio.emit('funding', {'symbol': symbol, 'data': data['data']}, room=request.sid)


@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


@socketio.on('update_settings')
def handle_settings_update(data):
    """Handle settings update from client"""
    print(f"Settings update received: {data}")
    # This will be handled by the main application
    # For now, just acknowledge
    socketio.emit('settings_updated', {'status': 'ok'})


def run_server():
    """Run the Flask server"""
    import os
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)