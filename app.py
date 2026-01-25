import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests

# --- 1. ระบบบันทึกข้อมูล ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ (Logic ใหม่: กรองหุ้นร่วงหนักได้แม่นยำ) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fund = stock.ticker_fundament()
        news_df = stock.ticker_news()
        insider_df = stock.ticker_inside_trader()
        chart_url = stock.ticker_charts()

        def to_num(s):
            s = str(s).replace(',', '').replace('$', '').replace('%', '')
            try: return float(s)
            except: return 0.0

        # ข้อมูลสำหรับวิเคราะห์แนวโน้ม
        price = to_num(fund['Price'])
        prev_close = to_num(fund['Prev Close']) # ราคาปิดเมื่อวาน
        rsi = to_num(fund['RSI (14)'])
        sma20_dist = to_num(fund['SMA20'])
        sma50_dist = to_num(fund['SMA50']) # ดึงค่าระยะห่างเส้น 50 วัน

        # --- 🚨 NEW TREND LOGIC (เข้มงวดแบบมือโปร) ---
        # 1. Bearish (ขาลง): หลุดเส้น 20 หรือ 50 หรือ RSI ต่ำ หรือราคาต่ำกว่าเมื่อวาน
        if sma20_dist < 0 or sma50_dist < 0 or rsi < 48 or price < prev_close:
            trend_label = "🔴 ขาลงชัดเจน (Bearish - เสี่ยงสูงมาก)"
            trend_color = "red"
            if rsi < 30: 
                trend_label = "🕳️ มุดดิน (Oversold - ลงแรงเกินไปอาจมีเด้ง)"
                trend_color = "orange"
        
        # 2. Bullish (ขาขึ้น): ต้องยืนเหนือทุกเส้น และ RSI ต้องแข็งแรง (> 52)
        elif sma20_dist > 0 and sma50_dist > 0 and rsi > 52:
            trend_label = "🚀 ขาขึ้นแข็งแกร่ง (Strong Bullish)"
            trend_color = "green"
        
        # 3. Sideway (พักตัว)
        else:
            trend_label = "😴 แนวโน้มไม่ชัดเจน/พักฐาน (Sideway)"
            trend_color = "blue"

        return fund, news_df, insider_df, chart_url, trend_label, trend_color, price, rsi
    except: return None, None, None, None, None, None, None, None

# --- 3. UI Layout ---
st.set_page_config(page_title="Pro Stock Analysis", layout="wide")
st.markdown("### 🔍 Stock Analysis")

c1, c2, c3 = st.columns([2, 2, 1])
with c1: symbol = st.text_input("Ticker:", value="NVDA").upper()
with c2: my_money = st.number_input("Budget ($):", value=300)
with c3:
    st.markdown('<div style="padding-top: 28px;"></div>', unsafe_allow_html=True)
    btn = st.button("🚀 SCAN", use_container_width=True)

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, chart, trend_label, trend_color, price, rsi = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # แสดงผลแนวโน้มด้วยสีที่ชัดเจน
        if trend_color == "green": st.success(f"💡 สรุปแนวโน้ม: {trend_label}")
        elif trend_color == "red": st.error(f"💡 สรุปแนวโน้ม: {trend_label}")
        elif trend_color == "orange": st.warning(f"💡 สรุปแนวโน้ม: {trend_label}")
        else: st.info(f"💡 สรุปแนวโน้ม: {trend_label}")

        # ข้อมูลดิบพื้นฐาน
        st.write(f"📊 **Price:** ${price} | **RSI:** {rsi} | **SMA20:** {fund['SMA20']} | **SMA50:** {fund['SMA50']}")

        # กลยุทธ์
        st.subheader("🎯 กลยุทธ์แนะนำ")
        if trend_color == "red":
            st.markdown("⚠️ **คำแนะนำ:** ขาลงชัดเจน **'รอหน้าเทรด'** อย่าเพิ่งรีบช้อน ให้สังเกตแนวรับสำคัญ")
        elif trend_color == "green":
            st.markdown("✅ **คำแนะนำ:** แนวโน้มดี **'Let Profit Run'** หรือย่อซื้อตามแนวรับ")

        st.image(chart, use_container_width=True)
    else:
        st.error("หาหุ้นไม่เจอครับ")
