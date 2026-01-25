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

# --- 2. ฟังก์ชันวิเคราะห์ Logic (เข้มงวด แม่นยำระดับมือโปร) ---
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

        # ข้อมูลพื้นฐานสำหรับคำนวณ
        price = to_num(fundament['Price'])
        prev_close = to_num(fundament['Prev Close'])
        mcap = to_num(fundament['Market Cap'])
        avg_vol = to_num(fundament['Avg Volume'])
        rsi_val = to_num(fundament['RSI (14)'])
        
        # ดึงระยะห่างจากเส้นค่าเฉลี่ย (%)
        sma20_dist = float(fundament['SMA20'].replace('%',''))
        sma50_dist = float(fundament['SMA50'].replace('%',''))

        # จำแนกประเภทหุ้น
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing"
        else: stock_type = "🔍 Small-Cap / Speculative"

        # วิเคราะห์ Sentiment ข่าว
        news_analysis = []
        sentiment_summary = "⚪ Neutral"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_p = 0
            for i, row in top_news.iterrows():
                p = TextBlob(row['Title']).sentiment.polarity
                total_p += p
                icon = "🟢" if p > 0.1 else "🔴" if p < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_s = total_p / len(top_news)
            sentiment_summary = f"({avg_s:.2f})"

        # คำนวณ Buy the Dip & TP
        target_price = to_num(fundament['Target Price'])
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp_short = dip_price * 1.07
        tp_target = target_price if target_price > price else price * 1.25
        sl_val = dip_price * 0.95
        
        # สภาพคล่อง SL
        liq_ratio = ((my_investment_usd / price) / avg_vol) * 100
        sl_workable = "YES (SAFE)" if liq_ratio < 0.05 else "RISKY"

        # วิเคราะห์คนใน
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

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sl_workable, sentiment_summary, stock_type, rsi_val, sma20_dist, sma50_dist, price, prev_close
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None

# --- 3. การแสดงผล UI ---
st.set_page_config(page_title="Ultimate Pro Stock Analysis", layout="wide")

# หัวข้อหลัก
st.markdown("### 🔍 Stock Analysis")

# ส่วนรับค่าแถวเดียว (ปุ่ม SCAN ขนานกับช่องกรอกข้อมูล)
col_in1, col_in2, col_input3 = st.columns([2, 2, 1])
with col_in1:
    symbol = st.text_input("กรอกชื่อหุ้น (Ticker):", value="NVDA").upper()
with col_in2:
    my_money = st.number_input("งบลงทุนต่อไม้ ($):", value=300)
with col_input3:
    st.markdown('<div style="padding-top: 28px;"></div>', unsafe_allow_html=True)
    btn = st.button("🚀 SCAN", use_container_width=True)

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sl_stat, sent, s_type, rsi, s20, s50, p_now, p_prev = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # แสดงหัวข้อหลักและประเภทหุ้น
        st.subheader(f"📈 วิเคราะห์ {symbol} | ประเภท: {s_type}")
        st.write(f"📊 Market Cap: {fund['Market Cap']} | Avg Volume: {fund['Avg Volume']}")
        
        # --- Logic ตัดสินแนวโน้มแบบแม่นยำ (ป้องกัน NVDA เขียวหลอก) ---
        # เงื่อนไข Bullish: ราคาต้องยืนเหนือเส้น 20, 50 วัน + RSI เกิน 50 + ราคาวันนี้ไม่ต่ำกว่าเมื่อวาน
        if s20 > 0 and s50 > 0 and rsi > 50 and p_now >= p_prev:
            st.success(f"💡 สรุปแนวโน้ม: 🚀 ขาขึ้นแข็งแกร่ง (Strong Bullish)")
        elif s20 < 0 or s50 < 0 or rsi < 45 or p_now < p_prev:
            if rsi < 30:
                st.warning(f"💡 สรุปแนวโน้ม: 🕳️ มุดดิน (Oversold - ลงแรงเกินไปรอเด้ง)")
            else:
                st.error(f"💡 สรุปแนวโน้ม: 🔴 ขาลงชัดเจน (Bearish - เสี่ยงสูง)")
        else:
            st.info(f"💡 สรุปแนวโน้ม: 😴 พักฐาน/แนวโน้มไม่ชัดเจน (Sideway)")

        # ข้อมูลสัญญาณเทคนิค
        st.write(f"🚩 **Technical Signal:** {signal}")
        st.write(f"📊 SMA20: {fund['SMA20']} | SMA50: {fund['SMA50']} | SMA200: {fund['SMA200']}")
        st.write(f"📉 RSI (14): {fund['RSI (14)']} | 📰 News Sentiment: {sent}")

        # กลยุทธ์แนะนำ
        st.subheader(f"🎯 กลยุทธ์แนะนำ (ไม้ ${my_money})")
        col1, col2, col3 = st.columns(3)
        col1.success(f"✅ Buy Zone: ${dip:.2f}")
        col2.info(f"🎯 TP: ${tp1:.2f} - ${tp2:.2f}")
        col3.error(f"🛑 Stop Loss: ${sl:.2f}")
        st.caption(f"🛡️ สภาพคล่อง SL: {sl_stat}")

        # สรุปข้อมูลคนใน
        st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน {symbol}")
        if summary['total_shares'] > 0:
            sell_pct = (summary['sold_shares'] / summary['total_shares']) * 100
            st.write(f"📦 หุ้นในมือรวม: {summary['total_shares']:,.0f} | ขายออกรวม: {sell_pct:.2f}%")
            st.write(f"💰 มูลค่าเงินสด: ${summary['sold_value']:,.2f} | ราคาเฉลี่ยที่เจ้าของขาย: ${summary['avg_price']:.2f}")
        else:
            st.write("ไม่พบข้อมูลการขายของคนใน")

        # แสดงภาพกราฟ
        
        st.image(chart, use_container_width=True)
        
        # ข่าววิเคราะห์
        with st.expander("📰 ดูข่าววิเคราะห์ล่าสุด 10 อันดับ"):
            for line in news[:10]:
                st.write(line)
    else:
        st.error("ไม่พบข้อมูลหุ้นตัวนี้ โปรดตรวจสอบ Ticker อีกครั้ง")
