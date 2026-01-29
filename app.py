import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests

# --- 1. ระบบบันทึกข้อมูล (Google Form) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try:
        requests.post(form_url, data=payload)
    except:
        pass

# --- 2. ฟังก์ชันวิเคราะห์ Logic (เข้มงวด แม่นยำระดับมือโปร) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty:
            return None
        
        df['SMA20_calc'] = ta.sma(df['Close'], length=20)
        df['SMA50_calc'] = ta.sma(df['Close'], length=50)
        df['RSI_calc'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        p_now = df['Close'].iloc[-1]
        p_prev = df['Close'].iloc[-2]
        rsi_val = df['RSI_calc'].iloc[-1]
        m_val = df['MACD_12_26_9'].iloc[-1]
        m_s = df['MACDs_12_26_9'].iloc[-1]
        s20 = df['SMA20_calc'].iloc[-1]
        s50 = df['SMA50_calc'].iloc[-1]

        stock_fv = finvizfinance(symbol)
        fundament = stock_fv.ticker_fundament()
        news_df = stock_fv.ticker_news()
        insider_df = stock_fv.ticker_inside_trader()
        chart_url = stock_fv.ticker_charts()

        def to_num(s):
            s = str(s).replace(',', '').replace('$', '').replace('%', '')
            if 'B' in s: return float(s.replace('B', '')) * 1_000_000_000
            if 'M' in s: return float(s.replace('M', '')) * 1_000_000
            if 'K' in s: return float(s.replace('K', '')) * 1_000
            try:
                return float(s)
            except:
                return 0.0

        mcap = to_num(fundament['Market Cap'])

        if mcap > 200_000_000_000:
            stock_type = "💎 Blue Chip"
        elif p_now < 5 or mcap < 300_000_000:
            stock_type = "⚠️ Penny Stock"
        else:
            stock_type = "🚀 Growth/Speculative"

        news_analysis = []
        sentiment_summary = "⚪ Neutral"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_p = 0
            for _, row in top_news.iterrows():
                p = TextBlob(row['Title']).sentiment.polarity
                total_p += p
                icon = "🟢" if p > 0.1 else "🔴" if p < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            sentiment_summary = f"({total_p/len(top_news):.2f})"

        agg_summary = {'total_shares': 0, 'sold_shares': 0}
        if insider_df is not None and not insider_df.empty:
            insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)
            sales = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]
            agg_summary['sold_shares'] = sales['shares_num'].sum()
            agg_summary['total_shares'] = insider_df['shares_num'].sum()

        return fundament, news_analysis, insider_df, agg_summary, chart_url, sentiment_summary, stock_type, rsi_val, p_now, p_prev, s20, s50, m_val, m_s

    except Exception as e:
        return str(e)

# --- 3. การแสดงผล UI ---
st.set_page_config(page_title="Ultimate Pro Stock Analysis", layout="wide")
st.markdown("### 🔍 Stock Analysis")

col_in1, col_in2, col_input3 = st.columns([2, 2, 1])
with col_in1:
    symbol = st.text_input("กรอกชื่อหุ้น (Ticker):", value="NVDA").upper()
with col_in2:
    my_money = st.number_input("งบลงทุนต่อไม้ ($):", value=300)
with col_input3:
    st.markdown('<div style="padding-top: 28px;"></div>', unsafe_allow_html=True)
    btn = st.button("🚀 SCAN", use_container_width=True)

if btn:
    log_to_sheets(symbol, my_money)
    result = get_ultimate_pro_intelligence(symbol, my_money)

    if isinstance(result, tuple):
        fund, news, insider, summary, chart, sent, s_type, rsi, p_now, p_prev, s20, s50, m_val, m_s = result

        st.subheader(f"📈 วิเคราะห์ {symbol} | ประเภท: {s_type}")

        # --- 🚨 TREND LOGIC (ของเดิม ไม่ลบ) ---
        if p_now < s20 or p_now < s50 or m_val < m_s or rsi < 48 or p_now < p_prev:
            old_trend = "BEAR"
        elif p_now > s20 and p_now > s50 and m_val > m_s and rsi > 52:
            old_trend = "BULL"
        else:
            old_trend = "SIDE"

        # --- ADDED: Trend Score (เพิ่ม ไม่แตะของเดิม) ---
        trend_score = 0
        trend_score += 1 if p_now > s20 else 0
        trend_score += 1 if p_now > s50 else 0
        trend_score += 1 if m_val > m_s else 0
        trend_score += 1 if rsi > 55 else -1 if rsi < 45 else 0
        trend_score += 1 if p_now > p_prev else -1

        if trend_score >= 4:
            st.success("💡 สรุปแนวโน้ม: 🚀 ขาขึ้นจริง")
        elif trend_score <= 1:
            st.error("💡 สรุปแนวโน้ม: 🔴 ขาลง / เสี่ยง")
        else:
            st.info("💡 สรุปแนวโน้ม: 😴 พักฐาน")

        st.write(f"📊 Market Cap: {fund['Market Cap']} | Price: ${p_now:.2f} | RSI: {rsi:.2f}")
        st.image(chart, use_container_width=True)

        with st.expander("📰 ดูข่าวล่าสุด"):
            for line in news[:10]:
                st.write(line)
