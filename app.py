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
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ Logic (เข้มงวด แม่นยำระดับมือโปร) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        # ดึงข้อมูลจาก Yahoo Finance
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty: return None
        
        # คำนวณ Technical Indicators
        df['SMA20_calc'] = ta.sma(df['Close'], length=20)
        df['SMA50_calc'] = ta.sma(df['Close'], length=50)
        df['RSI_calc'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # ค่าล่าสุดสำหรับตัดสินใจ
        p_now = df['Close'].iloc[-1]
        p_prev = df['Close'].iloc[-2]
        rsi_val = df['RSI_calc'].iloc[-1]
        macd_val = df['MACD_12_26_9'].iloc[-1]
        macd_s = df['MACDs_12_26_9'].iloc[-1]
        s20 = df['SMA20_calc'].iloc[-1]
        s50 = df['SMA50_calc'].iloc[-1]

        # ดึงข้อมูลเสริมจาก Finviz
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
            try: return float(s)
            except: return 0.0

        mcap = to_num(fundament['Market Cap'])
        avg_vol = to_num(fundament['Avg Volume'])

        # จำแนกประเภทหุ้น
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif p_now < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing"
        else: stock_type = "🔍 Small-Cap / Speculative"

        # วิเคราะห์ Sentiment ข่าว
        news_analysis = []
        sentiment_summary = "⚪ Neutral"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_p = 0
            for i, row in top_news.iterrows():
                p = TextBlob(row['Title']).sentiment.polarity
                total_p += p
                icon = "🟢" if p > 0.1 else "🔴" if p < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_s = total_p / len(top_news)
            sentiment_summary = f"({avg_s:.2f})"

        # คำนวณจุดซื้อขาย
        target_price = to_num(fundament['Target Price'])
        dip_price = p_now * 0.98
        tp_short = p_now * 1.07
        tp_target = target_price if target_price > p_now else p_now * 1.25
        sl_val = p_now * 0.95
        
        # สภาพคล่อง SL
        liq_ratio = ((my_investment_usd / p_now) / avg_vol) * 100
        sl_workable = "YES (SAFE)" if liq_ratio < 0.05 else "RISKY"

        # วิเคราะห์คนใน
        agg_summary = {'total_shares': 0, 'sold_shares': 0, 'sold_value': 0, 'avg_price': 0}
        if insider_df is not None and not insider_df.empty:
            insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)
            insider_df['total_owned_num'] = insider_df['#Shares Total'].apply(to_num)
            sales = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)].copy()
            if not sales.empty:
                agg_summary['sold_shares'] = sales['shares_num'].sum()
                agg_summary['sold_value'] = sales['Value ($)'].apply(to_num).sum()
                agg_summary['avg_price'] = sales['Cost'].apply(to_num).mean()
                total_own = insider_df.groupby('Insider Trading')['total_owned_num'].first().sum()
                agg_summary['total_shares'] = total_own + agg_summary['sold_shares']

        return fundament, news_analysis, insider_df, agg_summary, chart_url, dip_price, tp_short, tp_target, sl_val, sl_workable, sentiment_summary, stock_type, rsi_val, p_now, p_prev, s20, s50, macd_val, macd_s
    except Exception as e: return str(e)

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
        fund, news, insider, summary, chart, dip, tp1, tp2, sl, sl_stat, sent, s_type, rsi, p_now, p_prev, s20, s50, m_val, m_s = result

        # หัวข้อหลัก
        st.subheader(f"📈 วิเคราะห์ {symbol} | ประเภท: {s_type}")
        st.write(f"📊 Market Cap: {fund['Market Cap']} | Avg Volume: {fund['Avg Volume']}")
        
        # --- TREND LOGIC ---
        if p_now > s20 and p_now > s50 and m_val > m_s and rsi > 50 and p_now >= p_prev:
            st.success(f"💡 สรุปแนวโน้ม: 🚀 ขาขึ้นแข็งแกร่ง (Strong Bullish)")
        elif p_now < s20 or p_now < s50 or m_val < m_s or rsi < 45 or p_now < p_prev:
            if rsi < 30: st.warning(f"💡 สรุปแนวโน้ม: 🕳️ มุดดิน (Oversold - รอเด้ง)")
            else: st.error(f"💡 สรุปแนวโน้ม: 🔴 ขาลงชัดเจน (Bearish - เสี่ยงสูง)")
        else:
            st.info(f"💡 สรุปแนวโน้ม: 😴 พักฐาน (Sideway)")

        # ข้อมูลเทคนิค
        st.write(f"📊 SMA20: {fund['SMA20']} | SMA50: {fund['SMA50']} | SMA200: {fund['SMA200']}")
        st.write(f"📉 RSI: {rsi:.2f} | 📰 News Sentiment: {sent}")

        # กลยุทธ์
        st.subheader(f"🎯 กลยุทธ์แนะนำ (ไม้ ${my_money})")
        c1, c2, c3 = st.columns(3)
        c1.success(f"✅ Buy Zone: ${dip:.2f}")
        c2.info(f"🎯 TP: ${tp1:.2f} - ${tp2:.2f}")
        c3.error(f"🛑 Stop Loss: ${sl:.2f}")
        st.caption(f"🛡️ สภาพคล่อง SL: {sl_stat}")

        # ตาราง Fundamental (กลับมาแล้ว!)
        with st.expander("📑 ข้อมูลพื้นฐานจาก Finviz (Fundamental Table)"):
            st.table(pd.DataFrame([fund]).T)

        # ข้อมูลคนใน
        st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน {symbol}")
        if summary['total_shares'] > 0:
            sell_pct = (summary['sold_shares'] / summary['total_shares']) * 100
            st.write(f"📦 หุ้นในมือรวม: {summary['total_shares']:,.0f} | ขายออก: {sell_pct:.2f}%")
            st.write(f"💰 มูลค่าเงินสด: ${summary['sold_value']:,.2f} | ราคาเฉลี่ย: ${summary['avg_price']:.2f}")
        
        # กราฟ
                st.image(chart, use_container_width=True)
        
        # ข่าว
        with st.expander("📰 ดูข่าววิเคราะห์ล่าสุด 10 อันดับ"):
            for line in news[:10]: st.write(line)
    else:
        st.error(f"เกิดข้อผิดพลาด: {result}")
