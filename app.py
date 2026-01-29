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
        
        # === Indicators เดิม ===
        df['SMA20_calc'] = ta.sma(df['Close'], length=20)
        df['SMA50_calc'] = ta.sma(df['Close'], length=50)
        df['RSI_calc'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # === ADD: Market Structure ===
        df['HH'] = df['High'] > df['High'].shift(1)
        df['HL'] = df['Low'] > df['Low'].shift(1)
        df['LH'] = df['High'] < df['High'].shift(1)
        df['LL'] = df['Low'] < df['Low'].shift(1)

        recent_hh = df['HH'].tail(5).sum()
        recent_ll = df['LL'].tail(5).sum()

        # === ADD: Resistance / Breakout Detection ===
        resistance = df['High'].rolling(20).max().iloc[-2]
        p_now = df['Close'].iloc[-1]
        near_breakout = (p_now > resistance * 0.98) and (p_now < resistance)

        # === ค่าล่าสุด ===
        p_prev = df['Close'].iloc[-2]
        rsi_val = df['RSI_calc'].iloc[-1]
        m_val = df['MACD_12_26_9'].iloc[-1]
        m_s = df['MACDs_12_26_9'].iloc[-1]
        s20 = df['SMA20_calc'].iloc[-1]
        s50 = df['SMA50_calc'].iloc[-1]

        # === Finviz ===
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

        # === Stock Type ===
        if mcap > 200_000_000_000:
            stock_type = "💎 Blue Chip"
        elif p_now < 5 or mcap < 300_000_000:
            stock_type = "⚠️ Penny Stock"
        else:
            stock_type = "🚀 Growth/Speculative"

        # === News Sentiment ===
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
            sentiment_summary = f"({total_p / len(top_news):.2f})"

        # === Insider ===
        agg_summary = {'total_shares': 0, 'sold_shares': 0}
        if insider_df is not None and not insider_df.empty:
            insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)
            sales = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]
            agg_summary['sold_shares'] = sales['shares_num'].sum()

        # === UPDATED RETURN ===
        return (
            fundament, news_analysis, insider_df, agg_summary,
            chart_url, sentiment_summary, stock_type,
            rsi_val, p_now, p_prev, s20, s50, m_val, m_s,
            recent_hh, recent_ll, near_breakout
        )
    except Exception as e:
        return str(e)

# --- 3. UI ---
st.set_page_config(page_title="Ultimate Pro Stock Analysis", layout="wide")
st.markdown("### 🔍 Stock Analysis")

symbol = st.text_input("กรอกชื่อหุ้น (Ticker):", value="NVDA").upper()
my_money = st.number_input("งบลงทุนต่อไม้ ($):", value=300)
btn = st.button("🚀 SCAN", use_container_width=True)

if btn:
    log_to_sheets(symbol, my_money)
    result = get_ultimate_pro_intelligence(symbol, my_money)

    if isinstance(result, tuple):
        (
            fund, news, insider, summary, chart, sent, s_type,
            rsi, p_now, p_prev, s20, s50, m_val, m_s,
            recent_hh, recent_ll, near_breakout
        ) = result

        st.subheader(f"📈 วิเคราะห์ {symbol} | ประเภท: {s_type}")

        # === UPDATED TREND LOGIC ===
        if p_now > s20 > s50 and m_val > m_s and rsi > 55 and recent_hh >= 3:
            if near_breakout:
                st.success("💡 สรุปแนวโน้ม: 🚀 กำลังจะเบรกแนวต้าน (Breakout Setup)")
            else:
                st.success("💡 สรุปแนวโน้ม: 📈 ขาขึ้นชัดเจน (Bullish Trend)")

        elif p_now > s50 and rsi > 45 and recent_ll == 0:
            st.info("💡 สรุปแนวโน้ม: 🔵 ขาขึ้นแต่พักตัว (Bullish Pullback)")

        elif p_now < s20 < s50 and m_val < m_s and rsi < 45 and recent_ll >= 3:
            st.error("💡 สรุปแนวโน้ม: 🔴 ขาลงชัดเจน (Bearish Trend)")

        elif recent_hh > 0 and recent_ll > 0:
            st.info("💡 สรุปแนวโน้ม: 😴 Sideway / สะสมแรง")

        else:
            st.warning("💡 สรุปแนวโน้ม: 🟡 Sideway Down / ไม่ชัดเจน")

        st.image(chart, use_container_width=True)
