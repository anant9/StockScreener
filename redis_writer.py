import os
import json
import redis
import time
import threading
from SmartApi.smartConnect import SmartConnect
from dotenv import load_dotenv
from stock_list import get_token_mapping

# Load environment variables from .env file
load_dotenv()

# Read Angel One API credentials from environment
api_key = os.getenv("ANGEL_API_KEY")
username = os.getenv("ANGEL_USER_ID")
password = os.getenv("ANGEL_PASSWORD")
totp = os.getenv("ANGEL_TOTP")

# Authenticate with Angel One and obtain session and feed token
smartApi = SmartConnect(api_key)
session = smartApi.generateSession(username, password, totp)
feed_token = session['data']['feedToken']

# Connect to Redis using environment config
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

# Load stock symbol to token mapping from your Excel list
stock_tokens = get_token_mapping()  # Format: { 'SBIN': '3045', ... }

# Number of minutes of tick data to keep in Redis history
window_minutes = int(os.getenv("REDIS_TICK_WINDOW_MINUTES", 20))

# Set up WebSocket client for SmartAPI
from SmartApi.smartWebSocketV2 import SmartWebSocketV2
sws = SmartWebSocketV2(
    client_code=username,
    feed_token=feed_token,
    api_key=api_key
)

# Prepare list of tokens to subscribe (up to 50 max)
subscribe_tokens = list(stock_tokens.values())[:50]
subscribe_list = [{"exchangeType": 1, "token": token} for token in subscribe_tokens]

# Handler for incoming WebSocket data
def on_data(wsapp, message):
    try:
        data = json.loads(message)
        if 'token' in data and 'last_traded_price' in data:
            # Reverse lookup token to symbol
            symbol_matches = [s for s, t in stock_tokens.items() if t == data['token']]
            if not symbol_matches:
                return  # Skip if token is not recognized
            symbol = symbol_matches[0]

            # Construct tick object
            tick = {
                "symbol": symbol,
                "ltp": data['last_traded_price'] / 100.0,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            # Store latest tick and push to history in Redis
            redis_client.set(f"tick:{symbol}", json.dumps(tick))
            redis_client.rpush(f"tickhist:{symbol}", json.dumps(tick))
            redis_client.ltrim(f"tickhist:{symbol}", -window_minutes * 60, -1)
    except Exception as e:
        print(f"Tick parse error: {e}")

# Handler for when WebSocket connects
def on_open(wsapp):
    sws.subscribe(subscribe_list)

# Assign handlers
sws.on_open = on_open
sws.on_message = on_data

# Threaded function to maintain WebSocket connection with retry logic
def start_websocket():
    while True:
        try:
            sws.connect()
        except Exception as e:
            print(f"WebSocket connection error: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)

# Start WebSocket listener thread
threading.Thread(target=start_websocket, daemon=True).start()

# Keep main thread alive so the program doesn't exit
while True:
    time.sleep(60)
