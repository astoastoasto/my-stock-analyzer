import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import datetime
import requests

# --- 1. ระบบบันทึกข้อมูล (Google Form) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {
        "entry.336685021": symbol.upper(),
        "entry.71218977": str(money)
    }
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ Logic (ดึงข้อมูลพื้นฐานทั้งหมดมาโชว์) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fundament = stock.ticker_fundament() # ข้อมูลในภาพที่ 2 อยู่ในตัวแปรนี้
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
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        else: stock_type = "🚀 Mid-Growth"

        # --- AI Sentiment ---
        news_analysis = []
        if news_df is not None and not news_df.empty:
            total_p = 0
            for i, row in news_df.head(10).iterrows():
                p = TextBlob(row['Title']).sentiment.polarity
                total_p += p
                icon = "🟢" if p > 0.1 else "🔴" if p < -0.1 else "⚪"
                news_analysis.append(f"{icon} {row['Title']}")
            sentiment_summary = f"({(total_p/10):.2f})"
        else: sentiment_summary = "N/A"

        # --- Buy the Dip Logic ---
        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        
        # --- Insider Logic ---
        agg_summary = {'sell_pct': 0, 'total_val': 0}
        if insider_df is not None and not insider_df.empty:
            sold = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]['#Shares'].apply(to_num).sum()
            agg_summary['total_val'] = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]['Value ($)'].apply(to_num).sum()
            total_own = insider_df['#Shares Total'].apply(to_num).iloc[0] if not insider_df.empty else 0
            agg_summary['sell_pct'] = (sold / (total_own + sold)) * 100 if (total_own + sold) > 0 else 0

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, sentiment_summary, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None, None

# --- 3. ส่วน UI แบบกะทัดรัดแต่ข้อมูลครบ (เหมือนภาพที่ 2) ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")

col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h1: symbol = st.text_input("Ticker:", value="SKYT").upper()
with col_h2: my_money = st.number_input("Budget ($):", value=300)
with col_h3: 
    st.write("##")
    btn = st.button("🚀 SCAN")

if btn:
    log_to_sheets(symbol, my_money)
    with st.spinner('Analyzing...'):
        fund, news, insider, summary, signal, chart, dip, sent, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- ส่วนบน: สรุปกลยุทธ์ (Above the Fold) ---
        st.subheader(f"📈 {symbol} | {s_type} | Signal: {signal}")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"${fund['Price']}")
        m2.metric("✅ Buy Zone", f"${dip:.2f}")
        m3.metric("🎯 Target Price", f"${fund['Target Price']}")
        m4.metric("🛑 Stop Loss", f"${dip*0.95:.2f}")

        # --- ส่วนกลาง: ตารางข้อมูลพื้นฐาน (นี่คือข้อมูลแบบภาพที่ 2 ที่คุณต้องการ) ---
        st.write("### 📊 Fundamental Data (Finviz Style)")
        # แปลง Dictionary เป็น DataFrame เพื่อโชว์เป็นตารางเหมือนภาพที่ 2
        df_fund = pd.DataFrame([fund]).T
        df_fund.columns = ["Value"]
        st.dataframe(df_fund.T, use_container_width=True) # โชว์แบบแนวนอนประหยัดพื้นที่

        st.divider()

        # --- ส่วนล่าง: แท็บเก็บรายละเอียด ---
        tab1, tab2, tab3 = st.tabs(["📊 Technical Chart", "🏢 Insider Trading", "📰 Analysis News"])
        
        with tab1:
            st.image(chart, use_container_width=True)
            st.write(f"RSI: {fund['RSI (14)']} | SMA20: {fund['SMA20']} | Volume: {fund['Volume']}")
            
        with tab2:
            st.write(f"🏢 Insider Sold: {summary['sell_pct']:.2f}% | Value: ${summary['total_val']:,.0f}")
            if insider is not None:
                st.dataframe(insider[['Date', 'Insider Trading', 'Transaction', 'Cost', 'Value ($)']].head(10), use_container_width=True)
            
        with tab3:
            st.write(f"📰 Sentiment Score: {sent}")
            for line in news: st.write(line)
    else:
        st.error("ไม่พบข้อมูลหุ้นตัวนี้")
