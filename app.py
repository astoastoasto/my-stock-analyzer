import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests
import datetime

# --- 1. ระบบบันทึกข้อมูล ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ Logic ---
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

        mcap = to_num(fundament['Market Cap'])
        price = to_num(fundament['Price'])
        avg_vol = to_num(fundament['Avg Volume'])
        rsi_val = to_num(fundament['RSI (14)'])
        
        # เพิ่มค่า SMA50 และ ราคาปิดวันก่อนหน้า เพื่อความแม่นยำ
        sma50_raw = to_num(fundament['SMA50']) 
        prev_close = to_num(fundament['Prev Close'])

        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing"
        else: stock_type = "🔍 Small-Cap / Speculative"

        news_analysis = []
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_polarity = 0
            for i, row in top_news.iterrows():
                polarity = TextBlob(row['Title']).sentiment.polarity
                total_polarity += polarity
                icon = "🟢 (บวก)" if polarity > 0.1 else "🔴 (ลบ)" if polarity < -0.1 else "⚪ (กลาง)"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_score = total_polarity / len(top_news)
            sentiment_summary = f"({avg_score:.2f})"
        else:
            sentiment_summary = "N/A"

        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp_short = dip_price * 1.07
        tp_target = target_price if target_price > price else price * 1.25
        sl_val = dip_price * 0.95
        liq_ratio = ((my_investment_usd / price) / avg_vol) * 100
        sl_workable = "YES (SAFE)" if liq_ratio < 0.05 else "RISKY"

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

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sl_workable, sentiment_summary, stock_type, rsi_val, sma50_raw, prev_close
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None, None, None, None, None

# --- 3. UI Layout ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")

st.markdown("### 🔍 Stock Analysis")

col_input1, col_input2, col_input3 = st.columns([2, 2, 1])
with col_input1:
    symbol = st.text_input("กรอกชื่อหุ้น:", value="SKYT").upper()
with col_input2:
    my_money = st.number_input("งบลงทุน ($):", value=300)
with col_input3:
    st.markdown('<div style="padding-top: 28px;"></div>', unsafe_allow_html=True)
    btn = st.button("🚀 SCAN", use_container_width=True)

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sl_stat, sent, s_type, rsi_val, sma50_raw, prev_close = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        st.subheader(f"📈 วิเคราะห์ {symbol} | ประเภท: {s_type}")
        st.write(f"📊 Market Cap: {fund['Market Cap']} | Avg Volume: {fund['Avg Volume']}")
        
        st.markdown(f"**🚩 สัญญาณเทคนิคปัจจุบัน:** {signal}")
        st.write(f"📊 SMA20: {fund['SMA20']} | SMA50: {fund['SMA50']} | SMA200: {fund['SMA200']}")
        st.write(f"📉 RSI (14): {fund['RSI (14)']} | 📰 กระแสข่าวรวม: {sent}")

        # --- ปรับปรุง Trend Logic (เช็คละเอียดแบบแอปจ่ายเงิน) ---
        sma20_dist = float(fund['SMA20'].replace('%',''))
        sma50_dist = float(fund['SMA50'].replace('%',''))
        current_price = float(fund['Price'].replace(',',''))
        
        # 1. เช็คขาลง (Bearish): หลุดเส้นสำคัญ หรือ RSI อ่อนแรง หรือราคาต่ำกว่าเมื่อวาน
        if sma20_dist < 0 or sma50_dist < 0 or rsi_val < 45 or current_price < prev_close:
            trend_status = "🔴 ขาลง (Bearish - เสี่ยงสูง)"
            if rsi_val <= 30:
                st.warning(f"💡 สรุปแนวโน้ม: 🕳️ มุดดิน (Oversold - ลงแรงเกินไปรอเด้ง)")
            else:
                st.error(f"💡 สรุปแนวโน้ม: {trend_status}")
                
        # 2. เช็คขาขึ้น (Bullish): ต้องยืนเหนือทั้ง SMA20 และ SMA50 และ RSI > 50
        elif sma20_dist > 0 and sma50_dist > 0 and rsi_val > 50:
            st.success(f"💡 สรุปแนวโน้ม: 🚀 ขาขึ้นชัดเจน (Strong Bullish)")
            
        # 3. พักฐาน
        else:
            st.info(f"💡 สรุปแนวโน้ม: 😴 พักฐาน/แนวโน้มไม่ชัดเจน (Sideway)")

        st.subheader(f"🎯 กลยุทธ์แนะนำ: Buy the Dip (ไม้ ${my_money})")
        col1, col2, col3 = st.columns(3)
        col1.success(f"✅ Buy Zone: ${dip:.2f}")
        col2.info(f"🎯 TP 1: ${tp1:.2f} | TP 2: ${tp2:.2f}")
        col3.error(f"🛑 Stop Loss: ${sl:.2f}")
        st.caption(f"🛡️ สภาพคล่อง SL: {sl_stat}")

        st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน {symbol}")
        if summary['total_shares_before'] > 0:
            total_sell_pct = (summary['total_sold_shares'] / summary['total_shares_before']) * 100
            st.write(f"📦 หุ้นในมือรวม: {summary['total_shares_before']:,.0f} | ขายออกรวม: {total_sell_pct:.2f}%")
            st.write(f"💰 มูลค่าเงินสดรวม: ${summary['total_sold_value']:,.2f} | ราคาเฉลี่ย: ${summary['avg_sell_price']:.2f}")

        
        st.image(chart, use_container_width=True)
        
        with st.expander("📰 ดูข่าววิเคราะห์ล่าสุด 10 อันดับ"):
            for line in news[:10]:
                st.write(line)
    else:
        st.error("ไม่พบข้อมูลหุ้น")
