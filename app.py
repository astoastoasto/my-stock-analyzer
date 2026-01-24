import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob

# --- ฟังก์ชันดึงข้อมูล ---
@st.cache_data(ttl=3600) # ช่วยให้แอปโหลดเร็วขึ้น ไม่ต้องดึงใหม่ทุกครั้ง
def get_stock_data(symbol):
    try:
        stock = finvizfinance(symbol)
        fund = stock.ticker_fundament()
        news = stock.ticker_news()
        insider = stock.ticker_inside_trader()
        chart = stock.ticker_charts()
        return fund, news, insider, chart
    except:
        return None, None, None, None

def to_num(s):
    s = str(s).replace(',', '').replace('$', '').replace('%', '')
    if 'B' in s: return float(s.replace('B', '')) * 1_000_000_000
    if 'M' in s: return float(s.replace('M', '')) * 1_000_000
    try: return float(s)
    except: return 0.0

# --- หน้าจอหลัก ---
st.set_page_config(page_title="AI Insight", layout="wide")
st.title("💎 AI Stock Insight & Insider Tracker")

symbol = st.text_input("กรอกชื่อหุ้น (เช่น NVDA, TSLA, MSFT):", value="NVDA").upper()

if symbol:
    fund, news, insider, chart = get_stock_data(symbol)
    
    if fund:
        # ส่วนแสดงกราฟ
        st.subheader(f"📊 Market Overview: {symbol}")
        st.image(chart, use_container_width=True)

        # ส่วนสรุปกลยุทธ์ (ใช้ Columns ให้ดูสวย)
        col1, col2, col3 = st.columns(3)
        price = to_num(fund['Price'])
        with col1:
            st.info(f"💡 แนวโน้ม: {fund['SMA20']}")
        with col2:
            st.success(f"🎯 Target Price: ${fund['Target Price']}")
        with col3:
            st.warning(f"🛡️ RSI (14): {fund['RSI (14)']}")

        # ส่วน Insider Trading (ไฮไลท์สำคัญ)
        st.divider()
        st.subheader("🏢 ข้อมูลการซื้อขายของผู้บริหาร (Insider)")
        if insider is not None and not insider.empty:
            # แต่งตารางให้ดูง่าย
            st.dataframe(insider[['Date', 'Insider Trading', 'Relationship', 'Transaction', 'Cost', '#Shares', 'Value ($)']].head(10))
        else:
            st.write("ไม่มีข้อมูลการซื้อขายของคนในในช่วงนี้")

        # ส่วนวิเคราะห์ข่าว
        st.divider()
        st.subheader("📰 AI News Sentiment")
        for i, row in news.head(5).iterrows():
            polarity = TextBlob(row['Title']).sentiment.polarity
            icon = "🟢" if polarity > 0 else "🔴" if polarity < 0 else "⚪"
            st.write(f"{icon} {row['Date']} - {row['Title']}")
            
    else:
        st.error("ไม่พบข้อมูลหุ้นตัวนี้ โปรดระบุ Ticker ให้ถูกต้อง")