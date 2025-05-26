import os
import time
import requests
import mysql.connector
from stock_list import load_nifty50_symbols
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ANGEL_API_KEY")
USERNAME = os.getenv("ANGEL_USER_ID")
PASSWORD = os.getenv("ANGEL_PASSWORD")
TOTP = os.getenv("ANGEL_TOTP")
BASE_URL = "https://apiconnect.angelbroking.com/rest/secure/angelbroking/historical/v1/getCandleData"

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")


def get_mysql_connection():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE
    )


def fetch_candles(symbol, interval):
    payload = {
        "exchange": "NSE",
        "symboltoken": symbol + "-EQ",
        "interval": interval,
        "fromdate": time.strftime("%Y-%m-%d 09:15"),
        "todate": time.strftime("%Y-%m-%d %H:%M")
    }
    headers = {
        "X-PrivateKey": API_KEY,
        "Accept": "application/json",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-UserType": "USER",
        "Authorization": f"Bearer {TOTP}"
    }
    response = requests.post(BASE_URL, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    return []


def insert_candles_to_mysql(symbol, candles, interval):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    for c in candles:
        cursor.execute("""
            INSERT INTO historical_candles (symbol, interval, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (symbol, interval, c[0], c[1], c[2], c[3], c[4], c[5]))
    conn.commit()
    cursor.close()
    conn.close()


def get_mysql_change_pct(symbol, minutes):
    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM historical_candles
        WHERE symbol = %s AND interval = '1minute'
        ORDER BY timestamp DESC LIMIT %s
    """, (symbol, minutes))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows or len(rows) < 2:
        return None
    ltp_now = rows[0]['close']
    ltp_then = rows[-1]['close']
    pct_change = ((ltp_now - ltp_then) / ltp_then) * 100
    return {
        "ltp_now": ltp_now,
        "ltp_then": ltp_then,
        "pct_change": pct_change,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
