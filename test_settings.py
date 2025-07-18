#!/usr/bin/env python3
"""Test script to verify settings update functionality"""

import requests
import json
import time

# Test the health endpoint
print("Testing health endpoint...")
try:
    response = requests.get('http://localhost:5000/health')
    print(f"Health check response: {response.json()}")
except Exception as e:
    print(f"Health check failed: {e}")

print("\nTo test settings update:")
print("1. Open http://localhost:5000 in your browser")
print("2. Change the symbols or thresholds")
print("3. Click 'Apply Settings'")
print("4. Check the console output for 'Settings update received'")
print("5. Watch for new liquidations/trades for the selected symbols")

print("\nAlternatively, you can test via curl:")
print("""
curl -X POST http://localhost:5000/socket.io/ \
  -H "Content-Type: application/json" \
  -d '{"type": "update_settings", "data": {"symbols": ["BTC", "ETH", "SOL"], "minLiquidation": 50000, "minTrade": 250000}}'
""")