import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests
import datetime

# --- 1. ระบบบันทึกข้อมูล (ส่งเข้า Google Form เงียบๆ หลังบ้าน) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ (ดึงข้อมูลดิบมาโชว์แบบที่เคยทำได้) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fundament = stock.ticker_fundament() # ข้อมูลตารางเทาๆ ที่คุณต้องการ
        news_df = stock.ticker_news()
        insider_df = stock.ticker_inside_trader()
        try: tech_signal = stock.ticker_signal()
        except: tech_signal = "N/A"
        chart_url = stock.ticker_charts()

        def to_num(s):
            s = str(s).replace(',', '').replace('$', '').replace('%', '')
            if 'B' in s: return float(s.replace('B', '')) * 1_000_000_000
            if 'M' in s: return float(s.replace('M', '')) * 1_000_000
            if 'K' in s: return float(s.replace('K', '')) * 1_000
            try: return float(s)
            except: return 0.0

        # Logic: Buy the Dip
        price = to_num(fundament['Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        
        # Logic: Insider Summary
        agg_summary = {'sell_pct': 0, 'total_val': 0}
        if insider_df is not None and not insider_df.empty:
            sold = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]['#Shares'].apply(to_num).sum()
            agg_summary['total_val'] = insider_df[insider_df['Transaction'].str.contains('Sale', na=False)]['Value ($)'].apply(to_num).sum()
            total_own = insider_df['#Shares Total'].apply(to_num).iloc[0] if not insider_df.empty else 1
            agg_summary['sell_pct'] = (sold / (total_own + sold)) * 100

        return fundament, news_df, insider_df, agg_summary, tech_signal, chart_url, dip_price
    except Exception as e: return None, str(e), None, None, None, None, None

# --- 3. การแสดงผล (เน้นตารางข้อมูลแบบรูปที่ 2) ---
st.set_page_config(page_title="Stock Intelligence", layout="wide")

st.title("🚀 Stock Intelligence Dashboard")

# ช่องกรอกข้อมูล
c1, c2, c3 = st.columns([2, 1, 1])
with c1: symbol = st.text_input("Ticker:", value="SKYT").upper()
with c2: my_money = st.number_input("Budget ($):", value=300)
with c3:
    st.write("##")
    btn = st.button("RUN SCAN")

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- ส่วนที่ 1: ตาราง Fundamental (คืนชีพข้อมูลรูปที่ 2) ---
        st.header(f"📊 {symbol} Fundamental Data")
        # กางข้อมูลออกมาเป็นตารางยาวๆ ให้เห็นครบทุกบรรทัดเหมือน Finviz
        df_fund = pd.DataFrame([fund]).T
        df_fund.columns = ["Value"]
        st.table(df_fund) 

        st.divider()

        # --- ส่วนที่ 2: กลยุทธ์และการคำนวณ ---
        st.subheader("🎯 Trading Analysis")
        col1, col2, col3 = st.columns(3)
        col1.metric("Current Price", f"${fund['Price']}")
        col2.metric("✅ Buy Zone (Dip)", f"${dip:.2f}")
        col3.metric("🎯 Target Price", f"${fund['Target Price']}")
        
        st.write(f"🚩 **Technical Signal:** {signal} | **RSI:** {fund['RSI (14)']} | **SMA20:** {fund['SMA20']}")
        st.write(f"🏢 **Insider Confidence:** ขายออก {summary['sell_pct']:.2f}% | มูลค่ารวม: ${summary['total_val']:,.2f}")

        st.divider()

        # --- ส่วนที่ 3: กราฟและข่าวล่าสุด ---
        st.image(chart, use_container_width=True)
        
        st.subheader("📰 Latest News & Sentiment")
        if news is not None:
            for i, row in news.head(10).iterrows():
                st.write(f"• {row['Date']} - {row['Title']}")
    else:
        st.error("ไม่พบข้อมูลหุ้นตัวนี้ โปรดเช็คตัวสะกดอีกครั้ง")
