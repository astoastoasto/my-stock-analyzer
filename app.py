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

# --- 2. ฟังก์ชันวิเคราะห์ Logic จาก Colab (ครบทุกมิติ ไม่ตัดทอน) ---
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

        # --- จำแนกประเภทหุ้น ---
        mcap = to_num(fundament['Market Cap'])
        price = to_num(fundament['Price'])
        avg_vol = to_num(fundament['Avg Volume'])
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing"
        else: stock_type = "🔍 Speculative"

        # --- วิเคราะห์ AI Sentiment ---
        news_analysis = []
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_p = 0
            for i, row in top_news.iterrows():
                p = TextBlob(row['Title']).sentiment.polarity
                total_p += p
                icon = "🟢" if p > 0.1 else "🔴" if p < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_s = total_p / len(top_news)
            sentiment_summary = f"🟢 Bullish ({avg_s:.2f})" if avg_s > 0.1 else f"🔴 Bearish ({avg_s:.2f})" if avg_s < -0.1 else "⚪ Neutral"
        else:
            sentiment_summary = "⚪ No Data"

        # --- คำนวณ Buy the Dip & TP ---
        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp_short = dip_price * 1.07
        tp_target = target_price if target_price > price else price * 1.25
        sl_val = dip_price * 0.95
        liq_ratio = ((my_investment_usd / price) / avg_vol) * 100
        sl_workable = "YES (SAFE)" if liq_ratio < 0.05 else "RISKY"

        # --- คำนวณภาพรวมคนใน ---
        agg_summary = {'total_shares_before': 0, 'total_sold_shares': 0, 'total_sold_value': 0, 'avg_sell_price': 0, 'sell_pct': 0}
        if insider_df is not None and not insider_df.empty:
            insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)
            insider_df['total_owned_num'] = insider_df['#Shares Total'].apply(to_num)
            sales = insider_df[insider_df['Transaction'].str.contains('Sale', case=False, na=False)].copy()
            if not sales.empty:
                sold = sales['shares_num'].sum()
                agg_summary['total_sold_shares'] = sold
                agg_summary['total_sold_value'] = sales['Value ($)'].apply(to_num).sum()
                agg_summary['avg_sell_price'] = sales['Cost'].apply(to_num).mean()
                total_before = insider_df.groupby('Insider Trading')['total_owned_num'].first().sum() + sold
                agg_summary['total_shares_before'] = total_before
                agg_summary['sell_pct'] = (sold / total_before) * 100 if total_before > 0 else 0

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sl_workable, sentiment_summary, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None, None

# --- 3. ส่วนการแสดงผล (Compact Layout) ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")

# Header เรียงแถวเดียวประหยัดเนื้อที่
c_h1, c_h2, c_h3 = st.columns([2, 2, 1])
with c_h1: symbol = st.text_input("Ticker:", value="SKYT").upper()
with c_h2: my_money = st.number_input("Budget ($):", value=300)
with c_h3: 
    st.write("##") # ปรับระยะปุ่ม
    btn = st.button("🚀 SCAN")

if btn:
    log_to_sheets(symbol, my_money)
    with st.spinner('Analyzing...'):
        fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sl_stat, sentiment, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- ข้อมูลสำคัญ (Metric Row) ---
        st.subheader(f"📈 {symbol} | {s_type}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"${fund['Price']}")
        m2.metric("✅ Buy Zone", f"${dip:.2f}")
        m3.metric("🎯 TP 1 (Short)", f"${tp1:.2f}")
        m4.metric("🛑 Stop Loss", f"${sl:.2f}", delta_color="inverse")

        # บรรทัดสรุปเทคนิคและคนใน
        sma20_v = float(fund['SMA20'].replace('%',''))
        trend = "🚀 ขาขึ้น" if sma20_v > 0 else "🕳️ มุดดิน" if sma20_v < -5 else "😴 พักฐาน"
        st.markdown(f"**💡 Trend:** {trend} | **🚩 Signal:** {signal} | **📰 News:** {sentiment} | **🏢 Insider Sold:** {summary['sell_pct']:.2f}%")
        
        st.divider()

        # --- ส่วนรายละเอียด (ซ่อนใน Tabs ให้เลือกดูได้โดยไม่ต้องเลื่อนยาว) ---
        tab1, tab2, tab3 = st.tabs(["📊 Charts", "🏢 Insider & Analysis", "📰 News"])
        
        with tab1:
            st.image(chart, use_container_width=True)
            st.write(f"📊 SMA20: {fund['SMA20']} | SMA50: {fund['SMA50']} | SMA200: {fund['SMA200']} | RSI: {fund['RSI (14)']}")
            
        with tab2:
            st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน {symbol}")
            if summary['total_shares_before'] > 0:
                st.write(f"📦 หุ้นในมือคนในรวม: {summary['total_shares_before']:,.0f} | ขายออกรวม: {summary['sell_pct']:.2f}%")
                st.write(f"💰 มูลค่าเงินสดรวม: ${summary['total_sold_value']:,.2f} | เพดานราคาเจ้าของ: ${summary['avg_sell_price']:.2f}")
            if insider is not None:
                st.dataframe(insider[['Date', 'Insider Trading', 'Transaction', 'Cost', '#Shares', 'Value ($)']].head(10), use_container_width=True)
            
        with tab3:
            st.subheader("📰 วิเคราะห์อารมณ์ข่าวล่าสุด")
            for line in news[:10]: st.write(line)
    else:
        st.error(f"ไม่พบข้อมูลสำหรับ: {symbol}")
