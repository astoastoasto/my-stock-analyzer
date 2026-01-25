import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from finvizfinance.quote import finvizfinance
import requests

# --- 1. ระบบบันทึกข้อมูล (Google Form) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ใหม่ (Yahoo Finance + Technical Indicators) ---
def get_advanced_analysis(symbol, my_investment_usd=300):
    try:
        # ดึงข้อมูลจาก Yahoo Finance (สดใหม่กว่า Finviz)
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty: return None
        
        # คำนวณ Technical Indicators
        df['SMA20'] = ta.sma(df['Close'], length=20)
        df['SMA50'] = ta.sma(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)

        # ข้อมูลล่าสุด
        last_price = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        rsi_val = df['RSI'].iloc[-1]
        macd_val = df['MACD_12_26_9'].iloc[-1]
        macd_signal = df['MACDs_12_26_9'].iloc[-1]
        s20 = df['SMA20'].iloc[-1]
        s50 = df['SMA50'].iloc[-1]

        # ดึงข้อมูลพื้นฐานจาก Finviz (ใช้ประกอบเรื่อง Market Cap/Insider)
        stock_fv = finvizfinance(symbol)
        fund = stock_fv.ticker_fundament()
        chart_url = stock_fv.ticker_charts()

        # --- 🚨 TREND LOGIC (วิเคราะห์แบบแอปพรีเมียม) ---
        # ขาลง (Bearish): ราคาหลุดเส้นเฉลี่ย หรือ MACD ตัดลง หรือ RSI อ่อนแรง
        if last_price < s20 or last_price < s50 or macd_val < macd_signal or rsi_val < 45:
            trend_label = "🔴 ขาลงชัดเจน (Bearish/Correction)"
            trend_color = "error"
            if rsi_val < 30:
                trend_label = "🕳️ มุดดิน (Oversold - รอสัญญาณเด้ง)"
                trend_color = "warning"
        # ขาขึ้น (Bullish): ยืนเหนือเส้นเฉลี่ยทุกเส้น + MACD เป็นบวก + RSI แข็งแรง
        elif last_price > s20 and last_price > s50 and macd_val > macd_signal and rsi_val > 50:
            trend_label = "🚀 ขาขึ้นแข็งแกร่ง (Strong Bullish)"
            trend_color = "success"
        else:
            trend_label = "😴 พักฐาน (Sideway)"
            trend_color = "info"

        return df, fund, trend_label, trend_color, last_price, rsi_val, chart_url
    except Exception as e:
        return None

# --- 3. UI Layout ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")
st.markdown("### 🔍 Stock Analysis (Yahoo Finance Engine)")

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
        
        st.subheader(f"📈 วิเคราะห์ {symbol}")
        
        # แสดงสถานะแนวโน้ม
        if t_color == "success": st.success(f"💡 สรุปแนวโน้ม: {t_label}")
        elif t_color == "error": st.error(f"💡 สรุปแนวโน้ม: {t_label}")
        elif t_color == "warning": st.warning(f"💡 สรุปแนวโน้ม: {t_label}")
        else: st.info(f"💡 สรุปแนวโน้ม: {t_label}")

        st.write(f"📊 Price: ${price:.2f} | RSI: {rsi:.2f} | Market Cap: {fund['Market Cap']}")
        
        # กลยุทธ์แนะนำ
        st.subheader("🎯 กลยุทธ์แนะนำ")
        c1, c2, c3 = st.columns(3)
        c1.success(f"✅ Buy Zone: ${price * 0.98:.2f}")
        c2.info(f"🎯 Target: ${price * 1.07:.2f}")
        c3.error(f"🛑 Stop Loss: ${price * 0.95:.2f}")

        # กราฟจาก Finviz
        st.image(chart, use_container_width=True)
    else:
        st.error("ไม่พบข้อมูลหุ้นตัวนี้")
