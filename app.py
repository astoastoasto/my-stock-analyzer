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

# --- 2. ฟังก์ชันวิเคราะห์ Logic (คืนค่าเดิมจาก Colab ของคุณ 100%) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fundament = stock.ticker_fundament() # ข้อมูลตารางแบบภาพที่ 2
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

        # --- จำแนกประเภทหุ้น ---
        mcap = to_num(fundament['Market Cap'])
        price = to_num(fundament['Price'])
        avg_vol = to_num(fundament['Avg Volume'])
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip (หุ้นยักษ์ใหญ่ พื้นฐานแน่น ไม่แกว่งแรง)"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock (หุ้นจิ๋วสายซิ่ง เสี่ยงสูงมาก!)"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing (หุ้นกลางพื้นฐานดีแต่ซิ่งแรง)"
        else: stock_type = "🔍 Small-Cap / Speculative (หุ้นขนาดเล็ก เน้นเก็งกำไร)"

        # --- วิเคราะห์ AI Sentiment ---
        news_analysis = []
        sentiment_summary = "⚪ Neutral News (0.00)"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_polarity = 0
            for i, row in top_news.iterrows():
                polarity = TextBlob(row['Title']).sentiment.polarity
                total_polarity += polarity
                icon = "🟢 (บวก)" if polarity > 0.1 else "🔴 (ลบ)" if polarity < -0.1 else "⚪ (กลาง)"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_score = total_polarity / len(top_news)
            sentiment_summary = f"🟢 Bullish News ({avg_score:.2f})" if avg_score > 0.1 else f"🔴 Bearish News ({avg_score:.2f})" if avg_score < -0.1 else f"⚪ Neutral News ({avg_score:.2f})"

        # --- คำนวณ Buy the Dip & TP ---
        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp_short = dip_price * 1.07
        tp_target = target_price if target_price > price else price * 1.25
        sl_val = dip_price * 0.95

        # --- คำนวณภาพรวมคนใน ---
        agg_summary = {'total_shares_before': 0, 'total_sold_shares': 0, 'total_sold_value': 0, 'avg_sell_price': 0}
        if insider_df is not None and not insider_df.empty:
            insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)
            insider_df['total_owned_num'] = insider_df['#Shares Total'].apply(to_num)
            sales = insider_df[insider_df['Transaction'].str.contains('Sale', case=False, na=False)].copy()
            if not sales.empty:
                agg_summary['total_sold_shares'] = sales['shares_num'].sum()
                agg_summary['total_sold_value'] = sales['Value ($)'].apply(to_num).sum()
                agg_summary['avg_sell_price'] = sales['Cost'].apply(to_num).mean()
                total_current_remaining = insider_df.groupby('Insider Trading')['total_owned_num'].first().sum()
                agg_summary['total_shares_before'] = total_current_remaining + agg_summary['total_sold_shares']

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sentiment_summary, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None

# --- 3. การแสดงผล UI (คืนค่าเดิมและจัดตารางแบบภาพที่ 2) ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")
st.title("🚀 Ultimate Pro Stock Intelligence")

c1, c2, c3 = st.columns([2, 2, 1])
with c1: symbol = st.text_input("Ticker:", value="SKYT").upper()
with c2: my_money = st.number_input("Budget ($):", value=300)
with c3:
    st.write("##")
    btn = st.button("เริ่มวิเคราะห์")

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sent, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- ส่วนที่ 1: ตารางข้อมูลพื้นฐาน (แบบรูปที่ 2 ที่คุณต้องการ) ---
        st.header(f"📈 {symbol} | {s_type}")
        st.subheader("📑 ข้อมูลพื้นฐานจาก Finviz (Fundamental Table)")
        
        # กางข้อมูลออกมาเป็นตารางให้เห็นครบทุกบรรทัด
        df_fund = pd.DataFrame([fund]).T
        df_fund.columns = ["Value"]
        st.table(df_fund) 

        st.divider()

        # --- ส่วนที่ 2: กลยุทธ์แนะนำ ---
        st.subheader("🎯 กลยุทธ์แนะนำ: Buy the Dip")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"${fund['Price']}")
        m2.metric("✅ Buy Zone", f"${dip:.2f}")
        m3.metric("🎯 Target Price", f"${fund['Target Price']}")
        m4.metric("🛑 Stop Loss", f"${sl:.2f}")
        
        st.info(f"🚩 Signal: {signal} | 📉 RSI: {fund['RSI (14)']} | 📊 SMA20: {fund['SMA20']}")

        st.divider()

        # --- ส่วนที่ 3: สรุปคนใน ---
        st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน {symbol}")
        if summary['total_shares_before'] > 0:
            total_sell_pct = (summary['total_sold_shares'] / summary['total_shares_before']) * 100
            st.write(f"📦 หุ้นในมือรวม: {summary['total_shares_before']:,.0f} | ขายออกรวม: {total_sell_pct:.2f}%")
            st.write(f"💰 เงินสดรวม: ${summary['total_sold_value']:,.2f} | ราคาเฉลี่ยที่ขาย: ${summary['avg_sell_price']:.2f}")
        
        if insider is not None:
            st.dataframe(insider[['Date', 'Insider Trading', 'Transaction', 'Cost', 'Value ($)']].head(10), use_container_width=True)

        st.divider()

        # --- ส่วนที่ 4: กราฟและข่าว ---
        st.image(chart, use_container_width=True)
        st.subheader("📰 ข่าวล่าสุด")
        for line in news: st.write(line)
    else:
        st.error("ไม่พบข้อมูลหุ้น")
