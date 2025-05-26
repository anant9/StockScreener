import streamlit as st import os from gpt_parser import parse_prompt from screener_engine import run_screener from prompt_logger import log_prompt from user_sessions import log_user_session from stock_list import load_nifty50_symbols from dotenv import load_dotenv

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")

Session-level email

if "user_email" not in st.session_state: st.session_state.user_email = ""

st.title("📈 LLM-Powered Stock Screener")

--- Email Login ---

if not st.session_state.user_email: email = st.text_input("Enter your email to use the screener") if st.button("Continue"): st.session_state.user_email = email log_user_session(email) st.rerun() st.stop()

--- Prompt Input ---

st.subheader(f"Welcome, {st.session_state.user_email}") prompt = st.text_input("Enter your stock screener strategy in English:", placeholder="e.g., Show stocks with 1% change in last 15 minutes")

if st.button("Run Screener") and prompt: with st.spinner("Parsing your strategy and scanning..."): parsed = parse_prompt(prompt) results = run_screener(parsed) log_prompt(st.session_state.user_email, prompt, parsed) if results.empty: st.warning("No stocks matched your criteria.") else: st.success(f"Found {len(results)} matching stock(s).") st.dataframe(results)

--- Admin Panel ---

if st.session_state.user_email == ADMIN_EMAIL: st.markdown("---") st.subheader("🛠 Admin Panel")

# Show all logged users
from user_sessions import get_all_sessions
sessions = get_all_sessions()
st.markdown("#### User Logins")
st.dataframe(sessions)

# Show all prompts
from prompt_logger import get_prompt_logs
logs = get_prompt_logs()
st.markdown("#### Prompt History")
st.dataframe(logs)

# Redis Tick Viewer
import redis
import json
redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=int(os.getenv("REDIS_PORT")), password=os.getenv("REDIS_PASSWORD"), decode_responses=True)

st.markdown("#### Redis Tick History Viewer")
symbol = st.selectbox("Select symbol", load_nifty50_symbols())
ticks = redis_client.lrange(f"tickhist:{symbol}", 0, -1)
if ticks:
    import pandas as pd
    df_ticks = pd.DataFrame([json.loads(t) for t in ticks])
    st.dataframe(df_ticks)
else:
    st.info("No Redis data found for selected symbol.")

