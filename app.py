import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import datetime
import requests

# --- 1. ฟังก์ชันบันทึกข้อมูล ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {
        "entry.336685021": symbol.upper(),
        "entry.71218977": str(money)
    }
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ Logic (ปรับปรุงการดึงข้อมูลให้แม่นยำขึ้น) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fundament = stock.ticker_fundament()
        news_df = stock.ticker_news()
        insider_df = stock.ticker_inside_trader()
        try: tech_signal = stock.ticker_signal()
        except: tech_signal = "Neutral"
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

        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap"
        else: stock_type = "🔍 Speculative"

        news_analysis = []
        sentiment_summary = "⚪ Neutral"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(10)
            total_p = 0
            for i, row in top_news.iterrows():
                p = TextBlob(row['Title']).sentiment.polarity
                total_p += p
                icon = "🟢" if p > 0.1 else "🔴" if p < -0.1 else "⚪"
                news_analysis.append(f"{icon} {row['Title']}")
            avg_s = total_p / len(top_news)
            sentiment_summary = f"🟢 Bullish ({avg_s:.2f})" if avg_s > 0.1 else f"🔴 Bearish ({avg_s:.2f})" if avg_s < -0.1 else f"⚪ Neutral"

        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp_short = dip_price * 1.07
        tp_target = target_price if target_price > price else price * 1.25
        sl_val = dip_price * 0.95
        
        agg_summary = {'total_sold_value': 0, 'sell_pct': 0}
        if insider_df is not None and not insider_df.empty:
            insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)
            insider_df['total_owned_num'] = insider_df['#Shares Total'].apply(to_num)
            sales = insider_df[insider_df['Transaction'].str.contains('Sale', case=False, na=False)].copy()
            if not sales.empty:
                sold = sales['shares_num'].sum()
                agg_summary['total_sold_value'] = sales['Value ($)'].apply(to_num).sum()
                total_before = insider_df.groupby('Insider Trading')['total_owned_num'].first().sum() + sold
                agg_summary['sell_pct'] = (sold / total_before) * 100 if total_before > 0 else 0

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sentiment_summary, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None

# --- 3. ส่วน UI แบบกะทัดรัด (Compact Mode) ---
st.set_page_config(page_title="Pro Stock", layout="wide")

# ส่วนหัวโปรแกรมแบบประหยัดพื้นที่
col_head1, col_head2, col_head3 = st.columns([2, 2, 1])
with col_head1:
    symbol = st.text_input("Ticker:", value="SKYT").upper()
with col_head2:
    my_money = st.number_input("Budget ($):", value=300)
with col_head3:
    st.write(" ") # ปรับระยะ
    btn = st.button("SCAN")

if btn:
    log_to_sheets(symbol, my_money)
    with st.spinner('Scanning...'):
        fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sentiment, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- โซนสรุปสำคัญ (ไม่ต้องเลื่อนหน้าจอ) ---
        st.subheader(f"{symbol} | {s_type} | Trend: {fund['SMA20']}")
        
        # กางข้อมูลสำคัญออก 4 คอลัมน์
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current Price", f"${fund['Price']}")
        m2.metric("Buy Zone", f"${dip:.2f}")
        m3.metric("Take Profit", f"${tp1:.2f}")
        m4.metric("Stop Loss", f"${sl:.2f}", delta_color="inverse")

        # ข้อมูล Insider และ Sentiment แบบบรรทัดเดียว
        st.markdown(f"**🏢 Insider:** ขาย {summary['sell_pct']:.2f}% (${summary['total_sold_value']:,.0f}) | **📰 Sentiment:** {sentiment} | **🚩 Signal:** {signal}")
        
        st.divider()

        # --- ส่วนที่ต้องเลื่อนดู (ซ่อนใน Tabs) ---
        tab1, tab2, tab3 = st.tabs(["📊 Technical Chart", "📰 Latest News", "🏢 Insider Detail"])
        
        with tab1:
            st.image(chart, use_container_width=True)
            
        with tab2:
            for line in news: st.write(line)
            
        with tab3:
            if insider is not None:
                st.dataframe(insider[['Date', 'Insider Trading', 'Transaction', 'Cost', 'Value ($)']].head(10), use_container_width=True)
            else:
                st.write("No data found.")
    else:
        st.error(f"Error: {news}")
