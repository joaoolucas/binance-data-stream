from flask import Flask, render_template, request, jsonify
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


@app.route('/health')
def health():
    """Health check endpoint for monitoring WebSocket connections"""
    from main_visual_production import stream_instance
    
    health_data = {
        'status': 'healthy',
        'websocket_connections': 0,
        'active_streams': [],
        'stream_instance': False,
        'recent_liquidations': len(recent_events['liquidations']),
        'recent_trades': len(recent_events['trades']),
        'funding_symbols': len(recent_events['funding'])
    }
    
    try:
        if stream_instance:
            health_data['stream_instance'] = True
            if hasattr(stream_instance, 'ws_manager') and stream_instance.ws_manager:
                # Count active connections
                health_data['websocket_connections'] = len(stream_instance.ws_manager.connections)
                health_data['active_streams'] = list(stream_instance.current_subscriptions.keys())
                
                # Check if liquidation stream is active
                if '!forceOrder@arr' not in stream_instance.current_subscriptions:
                    health_data['status'] = 'degraded'
                    health_data['error'] = 'Liquidation stream not active'
        else:
            health_data['status'] = 'unhealthy'
            health_data['error'] = 'Stream instance not initialized'
    except Exception as e:
        health_data['status'] = 'error'
        health_data['error'] = str(e)
    
    return jsonify(health_data)


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