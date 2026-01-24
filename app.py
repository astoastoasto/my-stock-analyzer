import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests
import datetime

# --- 1. ระบบบันทึกข้อมูล (Google Form) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ Logic (ยกมาจาก Colab ของคุณทุกบรรทัด) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fundament = stock.ticker_fundament()
        news_df = stock.ticker_news()
        insider_df = stock.ticker_inside_trader()
        try: tech_signal = stock.ticker_signal()
        except: tech_signal = "No specific technical signal"
        chart_url = stock.ticker_charts()

        def to_num(s):
            s = str(s).replace(',', '').replace('$', '').replace('%', '')
            if 'B' in s: return float(s.replace('B', '')) * 1_000_000_000
            if 'M' in s: return float(s.replace('M', '')) * 1_000_000
            if 'K' in s: return float(s.replace('K', '')) * 1_000
            try: return float(s)
            except: return 0.0

        # จำแนกประเภทหุ้น
        mcap = to_num(fundament['Market Cap'])
        price = to_num(fundament['Price'])
        avg_vol = to_num(fundament['Avg Volume'])
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing"
        else: stock_type = "🔍 Small-Cap / Speculative"

        # AI Sentiment
        news_analysis = []
        sentiment_summary = "⚪ Neutral News"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_polarity = 0
            for i, row in top_news.iterrows():
                polarity = TextBlob(row['Title']).sentiment.polarity
                total_polarity += polarity
                icon = "🟢" if polarity > 0.1 else "🔴" if polarity < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_score = total_polarity / len(top_news)
            sentiment_summary = f"{avg_score:.2f}"

        # Buy the Dip
        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp1 = dip_price * 1.07
        tp2 = target_price if target_price > price else price * 1.25
        sl = dip_price * 0.95
        liq_ratio = ((my_investment_usd / price) / avg_vol) * 100
        sl_status = "YES (SAFE)" if liq_ratio < 0.05 else "RISKY"

        # สรุปคนใน
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

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp1, tp2, sl, sl_status, sentiment_summary, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None, None

# --- 3. การแสดงผล (เลียนแบบ Colab แต่อยู่บนเว็บ) ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")
st.title("🚀 Ultimate Pro Stock Intelligence")

col_in1, col_in2, col_in3 = st.columns([2, 1, 1])
with col_in1: symbol = st.text_input("Ticker:", value="SKYT").upper()
with col_in2: my_money = st.number_input("Budget ($):", value=300)
with col_in3:
    st.write("##")
    btn = st.button("RUN SCAN")

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sl_stat, sent, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- ข้อมูลพื้นฐานครบถ้วนแบบภาพที่ 2 ---
        st.header(f"📈 {symbol} | {s_type}")
        st.write("### 📑 ข้อมูลพื้นฐานจาก Finviz (Fundamental Table)")
        st.table(pd.DataFrame([fund]).T) # แสดงตารางแนวตั้งครบทุกแถว

        # --- สรุปแนวโน้มและกลยุทธ์ (Logic เดิม 100%) ---
        st.divider()
        st.subheader("🎯 กลยุทธ์และการวิเคราะห์")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"${fund['Price']}")
        col2.metric("✅ Buy Zone", f"${dip:.2f}")
        col3.metric("🎯 TP 1", f"${tp1:.2f}")
        col4.metric("🎯 TP 2", f"${tp2:.2f}")

        st.write(f"🚩 **Signal:** {signal} | **SMA20:** {fund['SMA20']} | **RSI:** {fund['RSI (14)']} | **Sentiment:** {sent}")
        st.error(f"🛑 Stop Loss: ${sl:.2f} | 🛡️ สภาพคล่อง: {sl_stat}")

        # --- สรุปคนใน ---
        st.divider()
        st.subheader(f"🏢 สรุปคนใน {symbol}")
        if summary['total_shares'] > 0:
            pct = (summary['sold_shares'] / summary['total_shares']) * 100
            st.write(f"📦 หุ้นในมือรวม: {summary['total_shares']:,.0f} | ขายออก: {pct:.2f}%")
            st.write(f"💰 เงินสดรวม: ${summary['sold_value']:,.2f} | ราคาเฉลี่ย: ${summary['avg_price']:.2f}")

        # --- กราฟและข่าว ---
        st.divider()
        
        st.image(chart, use_container_width=True)
        
        st.subheader("📰 วิเคราะห์ข่าวล่าสุด 10 อันดับ")
        for line in news[:10]:
            st.write(line)
    else:
        st.error("ไม่พบข้อมูลหุ้น")
