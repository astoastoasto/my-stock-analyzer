import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests
import datetime

# --- 1. บันทึกข้อมูล (Google Form) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. Logic วิเคราะห์หุ้น (ดึงข้อมูล Fundamental มาทั้งหมด) ---
def get_data(symbol, my_money):
    try:
        stock = finvizfinance(symbol)
        fund = stock.ticker_fundament() # ตารางข้อมูลที่คุณต้องการ
        news_df = stock.ticker_news()
        insider_df = stock.ticker_inside_trader()
        chart_url = stock.ticker_charts()
        try: signal = stock.ticker_signal()
        except: signal = "Neutral"

        def to_num(s):
            s = str(s).replace(',', '').replace('$', '').replace('%', '')
            if 'B' in s: return float(s.replace('B', '')) * 1_000_000_000
            if 'M' in s: return float(s.replace('M', '')) * 1_000_000
            if 'K' in s: return float(s.replace('K', '')) * 1_000
            try: return float(s)
            except: return 0.0

        price = to_num(fund['Price'])
        avg_vol = to_num(fund['Avg Volume'])
        sma20_dist = to_num(fund['SMA20']) / 100
        dip = price if sma20_dist < 0 else price * (1 - 0.02)
        
        # Insider Logic
        sell_pct = 0
        if insider_df is not None and not insider_df.empty:
            sold = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]['#Shares'].apply(to_num).sum()
            own = insider_df['#Shares Total'].apply(to_num).iloc[0] if not insider_df.empty else 0
            sell_pct = (sold / (own + sold)) * 100 if (own + sold) > 0 else 0

        return fund, news_df, insider_df, chart_url, signal, dip, sell_pct
    except: return None, None, None, None, None, None, None

# --- 3. UI Design (Compact & Professional) ---
st.set_page_config(page_title="Stock Intelligence", layout="wide")

# ส่วนบน: รับค่า (เรียงแถวเดียว)
c1, c2, c3 = st.columns([2, 2, 1])
with c1: symbol = st.text_input("Ticker:", value="NVDA").upper()
with c2: my_money = st.number_input("Budget ($):", value=300)
with c3: 
    st.write("##")
    btn = st.button("🚀 SCAN NOW")

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, chart, signal, dip, sell_p = get_data(symbol, my_money)

    if fund:
        # --- แถวที่ 1: สรุปกลยุทธ์ (ไม่ต้องเลื่อน) ---
        st.subheader(f"📈 {symbol} Analysis Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"${fund['Price']}")
        m2.metric("✅ Buy Zone", f"${dip:.2f}")
        m3.metric("🎯 Target Price", f"${fund['Target Price']}")
        m4.metric("🛑 Stop Loss", f"${dip*0.95:.2f}")

        # --- แถวที่ 2: ตารางข้อมูลแบบภาพที่ 2 (จัดระเบียบให้ดูง่าย) ---
        st.write("📊 **Fundamental Overview** (ดึงข้อมูลดิบมาโชว์ครบ)")
        df_display = pd.DataFrame([fund])
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.divider()

        # --- แถวที่ 3: กราฟและรายละเอียดอื่นๆ (ซ่อนใน Tab) ---
        tab1, tab2, tab3 = st.tabs(["📉 Technical Chart", "🏢 Insider & Sentiment", "📰 News"])
        
        with tab1:
            st.image(chart, use_container_width=True)
            st.write(f"🚩 Signal: {signal} | SMA20: {fund['SMA20']} | RSI: {fund['RSI (14)']}")
            
        with tab2:
            st.write(f"🏢 Insider Sold: {sell_p:.2f}% | Market Cap: {fund['Market Cap']}")
            if insider is not None:
                st.dataframe(insider[['Date', 'Insider Trading', 'Transaction', 'Cost', 'Value ($)']].head(10), use_container_width=True)
            
        with tab3:
            if news is not None:
                for i, row in news.head(10).iterrows():
                    st.write(f"• {row['Date']} - {row['Title']}")
    else:
        st.error("ไม่พบข้อมูลหุ้นตัวนี้ โปรดตรวจสอบชื่ออีกครั้ง")
