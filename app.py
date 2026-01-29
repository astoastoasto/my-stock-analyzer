import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests

# =========================
# 1. LOG TO GOOGLE FORM
# =========================
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {
        "entry.336685021": symbol.upper(),
        "entry.71218977": str(money)
    }
    try:
        requests.post(form_url, data=payload, timeout=3)
    except:
        pass


# =========================
# 2. HELPER
# =========================
def to_num(val):
    s = str(val).replace(',', '').replace('$', '').replace('%', '')
    if 'B' in s: return float(s.replace('B', '')) * 1_000_000_000
    if 'M' in s: return float(s.replace('M', '')) * 1_000_000
    if 'K' in s: return float(s.replace('K', '')) * 1_000
    try:
        return float(s)
    except:
        return 0.0


# =========================
# 3. TECHNICAL ANALYSIS
# =========================
def get_technical_data(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1y")

    if df is None or df.empty or len(df) < 60:
        return None, "ข้อมูลราคาไม่พอ"

    df['SMA20'] = ta.sma(df['Close'], 20)
    df['SMA50'] = ta.sma(df['Close'], 50)
    df['RSI'] = ta.rsi(df['Close'], 14)

    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    return {
        "price": latest['Close'],
        "prev_price": prev['Close'],
        "sma20": latest['SMA20'],
        "sma50": latest['SMA50'],
        "rsi": latest['RSI'],
        "macd": latest['MACD_12_26_9'],
        "macd_signal": latest['MACDs_12_26_9']
    }, None


# =========================
# 4. FINVIZ DATA
# =========================
def get_finviz_data(symbol):
    fv = finvizfinance(symbol)
    fund = fv.ticker_fundament()
    news = fv.ticker_news()
    insider = fv.ticker_inside_trader()
    chart = fv.ticker_charts()
    return fund, news, insider, chart


# =========================
# 5. SENTIMENT
# =========================
def analyze_news_sentiment(news_df):
    if news_df is None or news_df.empty:
        return [], "⚪ Neutral"

    scores = []
    lines = []

    for _, row in news_df.head(15).iterrows():
        polarity = TextBlob(row['Title']).sentiment.polarity
        scores.append(polarity)
        icon = "🟢" if polarity > 0.1 else "🔴" if polarity < -0.1 else "⚪"
        lines.append(f"{icon} [{row['Date']}] {row['Title']}")

    avg = sum(scores) / len(scores)
    return lines, f"({avg:.2f})"


# =========================
# 6. INSIDER ANALYSIS
# =========================
def analyze_insider(insider_df):
    summary = {"total": 0, "sold": 0}

    if insider_df is None or insider_df.empty:
        return summary

    insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)

    sold = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]
    summary['sold'] = sold['shares_num'].sum()
    summary['total'] = insider_df['shares_num'].sum()

    return summary


# =========================
# 7. TREND LOGIC (ของเดิม + ชัดขึ้น)
# =========================
def detect_trend(t):
    if (
        t['price'] < t['sma20'] or
        t['price'] < t['sma50'] or
        t['macd'] < t['macd_signal'] or
        t['rsi'] < 48 or
        t['price'] < t['prev_price']
    ):
        if t['rsi'] < 35:
            return "🕳️ Oversold (รอเด้งสั้น)", "warning"
        return "🔴 ขาลงชัดเจน (Bearish)", "error"

    if (
        t['price'] > t['sma20'] and
        t['price'] > t['sma50'] and
        t['macd'] > t['macd_signal'] and
        t['rsi'] > 52
    ):
        return "🚀 ขาขึ้นแข็งแกร่ง (Strong Bullish)", "success"

    return "😴 พักฐาน / Sideway", "info"


# =========================
# 8. UI
# =========================
st.set_page_config("Ultimate Pro Stock Analysis", layout="wide")
st.title("🔍 Ultimate Pro Stock Analysis")

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    symbol = st.text_input("Ticker", "NVDA").upper()
with c2:
    budget = st.number_input("งบต่อไม้ ($)", 100, 10000, 300)
with c3:
    st.markdown("<br>", unsafe_allow_html=True)
    scan = st.button("🚀 SCAN", use_container_width=True)

if scan:
    log_to_sheets(symbol, budget)

    tech, err = get_technical_data(symbol)
    if err:
        st.error(err)
        st.stop()

    fund, news, insider, chart = get_finviz_data(symbol)
    news_lines, sentiment = analyze_news_sentiment(news)
    insider_sum = analyze_insider(insider)

    trend_text, trend_type = detect_trend(tech)
    getattr(st, trend_type)(f"💡 แนวโน้ม: {trend_text}")

    st.write(
        f"📊 Price: ${tech['price']:.2f} | "
        f"RSI: {tech['rsi']:.2f} | "
        f"Market Cap: {fund.get('Market Cap','-')}"
    )

    st.subheader("🎯 กลยุทธ์")
    a, b, c = st.columns(3)
    a.success(f"Buy ~ ${tech['price']*0.98:.2f}")
    b.info(f"Target ~ ${tech['price']*1.07:.2f}")
    c.error(f"SL ~ ${tech['price']*0.95:.2f}")

    with st.expander("📑 Fundamental (Finviz)"):
        st.table(pd.DataFrame([fund]).T)

    with st.expander("📰 ข่าวล่าสุด"):
        for n in news_lines[:10]:
            st.write(n)

    st.image(chart, use_container_width=True)
