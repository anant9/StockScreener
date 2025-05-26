import redis
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    password=os.getenv("REDIS_PASSWORD"),
    decode_responses=True
)

def get_redis_change_pct(symbol: str, interval_minutes: int) -> dict:
    key = f"tickhist:{symbol}"
    ticks = redis_client.lrange(key, 0, -1)
    if not ticks or len(ticks) < 2:
        return None

    now = datetime.now()
    target_time = now - timedelta(minutes=interval_minutes)
    parsed_ticks = [json.loads(t) for t in ticks]

    ltp_now = parsed_ticks[-1]["ltp"]
    ltp_then = None

    for t in parsed_ticks:
        tick_time = datetime.strptime(t["timestamp"], "%Y-%m-%d %H:%M:%S")
        if tick_time >= target_time:
            ltp_then = t["ltp"]
            break

    if ltp_then is None:
        ltp_then = parsed_ticks[0]["ltp"]

    pct_change = ((ltp_now - ltp_then) / ltp_then) * 100

    return {
        "ltp_now": ltp_now,
        "ltp_then": ltp_then,
        "pct_change": pct_change,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    }
