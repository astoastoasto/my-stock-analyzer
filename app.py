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

# --- 2. ฟังก์ชันวิเคราะห์ Logic (Yahoo Finance Engine) ---
def get_advanced_analysis(symbol, my_investment_usd=300):
    try:
        # ดึงข้อมูลจาก Yahoo Finance (สดใหม่กว่า)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty: return None
        
        # คำนวณ Technical Indicators แบบแม่นยำ
        df['SMA20'] = ta.sma(df['Close'], length=20)
        df['SMA50'] = ta.sma(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # ค่าล่าสุดสำหรับตัดสินใจ
        p_now = df['Close'].iloc[-1]
        p_prev = df['Close'].iloc[-2]
        rsi_val = df['RSI'].iloc[-1]
        macd_val = df['MACD_12_26_9'].iloc[-1]
        macd_s = df['MACDs_12_26_9'].iloc[-1]
        s20 = df['SMA20'].iloc[-1]
        s50 = df['SMA50'].iloc[-1]

        # ดึงข้อมูลเสริมจาก Finviz (Insider/Market Cap)
        stock_fv = finvizfinance(symbol)
        fund = stock_fv.ticker_fundament()
        chart_url = stock_fv.ticker_charts()

        # --- 🚨 TREND LOGIC (เข้มงวดแบบแอปพรีเมียม) ---
        # ขาลง (Bearish): ราคาหลุด SMA, MACD ตัดลง, หรือราคาต่ำกว่าเมื่อวาน
        if p_now < s20 or p_now < s50 or macd_val < macd_s or rsi_val < 48 or p_now < p_prev:
            trend_label = "🔴 ขาลงชัดเจน (Bearish/Correction)"
            trend_color = "red"
            if rsi_val < 30:
                trend_label = "🕳️ มุดดิน (Oversold - ลงแรงเกินไปรอเด้ง)"
                trend_color = "orange"
        # ขาขึ้น (Bullish): เขียวทุกมิติ
        elif p_now > s20 and p_now > s50 and macd_val > macd_s and rsi_val > 52:
            trend_label = "🚀 ขาขึ้นแข็งแกร่ง (Strong Bullish)"
            trend_color = "green"
        else:
            trend_label = "😴 พักฐาน (Sideway)"
            trend_color = "blue"

        return df, fund, trend_label, trend_color, p_now, rsi_val, chart_url
    except: return None

# --- 3. UI Layout ---
st.set_page_config(page_title="Ultimate Pro Stock Analysis", layout="wide")

st.markdown("### 🔍 Stock Analysis")

# ปุ่ม SCAN ขนานกับช่องข้อมูล
col_in1, col_in2, col_in3 = st.columns([2, 2, 1])
with col_in1: symbol = st.text_input("กรอกชื่อหุ้น:", value="NVDA").upper()
with col_in2: my_money = st.number_input("งบลงทุน ($):", value=300)
with col_in3:
    st.markdown('<div style="padding-top: 28px;"></div>', unsafe_allow_html=True)
    btn = st.button("🚀 SCAN", use_container_width=True)

if btn:
    log_to_sheets(symbol, my_money)
    result = get_advanced_analysis(symbol, my_money)

    if result:
        df, fund, t_label, t_color, price, rsi, chart = result
        
        st.subheader(f"📈 วิเคราะห์ {symbol} | ประเภท: {fund.get('Sector', 'N/A')}")
        st.write(f"📊 Market Cap: {fund.get('Market Cap', 'N/A')} | Price: ${price:.2f}")
        
        # แสดงสถานะแนวโน้ม
        if t_color == "green": st.success(f"💡 สรุปแนวโน้ม: {t_label}")
        elif t_color == "red": st.error(f"💡 สรุปแนวโน้ม: {t_label}")
        elif t_color == "orange": st.warning(f"💡 สรุปแนวโน้ม: {t_label}")
        else: st.info(f"💡 สรุปแนวโน้ม: {t_label}")

        st.write(f"📊 SMA20: {fund.get('SMA20', 'N/A')} | SMA50: {fund.get('SMA50', 'N/A')} | RSI: {rsi:.2f}")

        # กลยุทธ์แนะนำ
        st.subheader(f"🎯 กลยุทธ์แนะนำ (ไม้ ${my_money})")
        c1, c2, c3 = st.columns(3)
        c1.success(f"✅ Buy Zone: ${price * 0.98:.2f}")
        c2.info(f"🎯 Target: ${price * 1.07:.2f}")
        c3.error(f"🛑 Stop Loss: ${price * 0.95:.2f}")

        # กราฟ
        
        st.image(chart, use_container_width=True)
        
    else:
        st.error("ไม่พบข้อมูลหุ้น หรือระบบขัดข้อง โปรดเช็คไฟล์ requirements.txt")
