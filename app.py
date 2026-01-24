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

# --- 2. ฟังก์ชันวิเคราะห์ (คืนค่าเดิมที่คุณต้องการ 100%) ---
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
        else: stock_type = "🚀 Growth/Speculative"

        # วิเคราะห์ Sentiment
        news_list = []
        if news_df is not None and not news_df.empty:
            for i, row in news_df.head(10).iterrows():
                p = TextBlob(row['Title']).sentiment.polarity
                icon = "🟢" if p > 0.1 else "🔴" if p < -0.1 else "⚪"
                news_list.append(f"{icon} [{row['Date']}] {row['Title']}")

        # คำนวณ Buy the Dip
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        
        # สรุปคนใน
        agg_sum = {'total_val': 0, 'sell_pct': 0}
        if insider_df is not None and not insider_df.empty:
            sold = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]['#Shares'].apply(to_num).sum()
            agg_sum['total_val'] = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]['Value ($)'].apply(to_num).sum()
            total_own = insider_df['#Shares Total'].apply(to_num).iloc[0] if not insider_df.empty else 1
            agg_sum['sell_pct'] = (sold / (total_own + sold)) * 100

        return fundament, news_list, insider_df, agg_sum, tech_signal, chart_url, dip_price, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None

# --- 3. การแสดงผล (เน้นข้อมูลครบถ้วนแบบดั้งเดิม) ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")
st.title("🚀 Ultimate Pro Stock Intelligence")

c1, c2, c3 = st.columns([2, 1, 1])
with c1: symbol = st.text_input("Ticker:", value="SKYT").upper()
with c2: my_money = st.number_input("Budget ($):", value=300)
with c3:
    st.write("##")
    btn = st.button("RUN SCAN")

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        st.header(f"📈 {symbol} | {s_type}")
        
        # --- นี่คือตารางแบบภาพที่ 2 ที่คุณต้องการ ---
        st.subheader("📑 Fundamental Data Table")
        # แปลงเป็นตารางแนวตั้งเหมือน Finviz
        df_fund = pd.DataFrame([fund]).T
        df_fund.columns = ["Value"]
        st.table(df_fund) 

        # --- สรุปกลยุทธ์ ---
        st.divider()
        st.subheader("🎯 Trading Strategy")
        st.success(f"✅ Buy Zone: ${dip:.2f} | 🎯 Target: ${fund['Target Price']} | 🛑 Stop Loss: ${dip*0.95:.2f}")
        st.info(f"🚩 Signal: {signal} | RSI: {fund['RSI (14)']} | SMA20: {fund['SMA20']}")

        # --- ข้อมูลคนใน ---
        st.divider()
        st.subheader("🏢 Insider Activity")
        st.write(f"ขายออกรวม: {summary['sell_pct']:.2f}% | มูลค่า: ${summary['total_val']:,.2f}")
        if insider is not None:
            st.dataframe(insider[['Date', 'Insider Trading', 'Transaction', 'Cost', 'Value ($)']].head(10))

        # --- กราฟและข่าว ---
        st.divider()
        st.image(chart, use_container_width=True)
        st.subheader("📰 Analysis News")
        for n in news: st.write(n)
    else:
        st.error("Error: Could not fetch data.")
