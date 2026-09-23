import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============ PAGE CONFIG (Mobile-First) ============
st.set_page_config(
    page_title="Halal Swing Scanner",
    page_icon="📈",
    layout="centered",  # centered works better on mobile
    initial_sidebar_state="collapsed"  # collapse sidebar on mobile
)

# ============ MOBILE RESPONSIVE CSS ============
st.markdown("""
<style>
@media (max-width: 600px) {
    .stButton > button { min-height: 48px !important; font-size: 1rem !important; }
    .stDataFrame { font-size: 0.8rem !important; }
}
</style>
""", unsafe_allow_html=True)

# ============ HALAL STOCK UNIVERSE (Nifty 500 Shariah subset) ============
# In production, fetch from Nifty Shariah factsheet or use curated list
HALAL_STOCKS = [
    "TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS",
    "HINDUNILVR.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
    "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS",
    "ULTRACEMCO.NS", "ASIANPAINT.NS", "TITAN.NS", "BHARTIARTL.NS",
    "MARUTI.NS", "HEROMOTOCO.NS", "BAJAJ-AUTO.NS",
    "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "COALINDIA.NS",
    "TATACONSUM.NS", "APOLLOHOSP.NS", "HINDALCO.NS",
]

# ============ TECHNICAL INDICATORS ============
def compute_indicators(df):
    df = df.copy()
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    # EMAs
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    # MACD
    ema12 = df['Close'].ewm(span=12).mean()
    ema26 = df['Close'].ewm(span=26).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
    # ADX (simplified)
    high, low, close = df['High'], df['Low'], df['Close']
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    plus_dm = (high - high.shift()).where((high - high.shift()) > (low.shift() - low), 0)
    minus_dm = (low.shift() - low).where((low.shift() - low) > (high - high.shift()), 0)
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    df['ADX'] = dx.rolling(14).mean()
    # Volume average
    df['Vol_Avg'] = df['Volume'].rolling(20).mean()
    return df

# ============ SCANNER LOGIC ============
def scan_stock(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return None
        df = compute_indicators(df)
        latest = df.iloc[-1]
        
        # Entry conditions
        rsi_ok = latest['RSI'] < 45
        trend_ok = latest['Close'] > latest['EMA20'] > latest['EMA50']
        macd_ok = latest['MACD'] > latest['MACD_Signal']
        adx_ok = latest['ADX'] > 20
        vol_ok = latest['Volume'] > latest['Vol_Avg']
        
        # Score
        score = sum([rsi_ok, trend_ok, macd_ok, adx_ok, vol_ok])
        
        return {
            'Symbol': symbol.replace('.NS', ''),
            'Price': round(float(latest['Close']), 2),
            'RSI': round(float(latest['RSI']), 1),
            'ADX': round(float(latest['ADX']), 1),
            'EMA_Trend': '✅' if trend_ok else '❌',
            'MACD': '✅' if macd_ok else '❌',
            'Volume': '✅' if vol_ok else '❌',
            'Score': score,
            'Signal': '🟢 BUY' if score >= 4 else ('🟡 WATCH' if score >= 3 else '⚪ NEUTRAL')
        }
    except:
        return None

# ============ UI ============
st.title("📈 Halal Swing Scanner")
st.caption("NSE Shariah-Compliant Stocks • Live Swing Trade Signals")

if st.button("🔍 Run Live Scan", use_container_width=True):
    with st.spinner("Scanning halal stocks..."):
        results = []
        for sym in HALAL_STOCKS:
            r = scan_stock(sym)
            if r:
                results.append(r)
        results.sort(key=lambda x: x['Score'], reverse=True)
        df_res = pd.DataFrame(results)
        
        # Display top picks
        buys = df_res[df_res['Signal'] == '🟢 BUY']
        if not buys.empty:
            st.subheader("🎯 Top Swing Picks")
            st.dataframe(buys, use_container_width=True, hide_index=True)
        
        st.subheader("📊 Full Scan Results")
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        
        st.caption(f"Scanned {len(results)} halal stocks • {datetime.now().strftime('%d %b %Y, %I:%M %p')}")
