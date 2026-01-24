import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import requests
import datetime

# --- 1. บันทึกข้อมูลลง Sheets ผ่าน Form (ทำงานเงียบๆ) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชัน Logic เดิมของคุณ (กู้คืนมาจาก Colab ทุกบรรทัด) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fundament = stock.ticker_fundament() # << ข้อมูลตารางเทาๆ อยู่ที่นี่
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

        # --- 1. จำแนกประเภทหุ้น ---
        mcap = to_num(fundament['Market Cap'])
        price = to_num(fundament['Price'])
        avg_vol = to_num(fundament['Avg Volume'])
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing"
        else: stock_type = "🔍 Small-Cap / Speculative"

        # --- 2. วิเคราะห์ AI Sentiment ---
        news_analysis = []
        sentiment_summary = "⚪ Neutral News"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_polarity = 0
            for i, row in top_news.iterrows():
                polarity = TextBlob(row['Title']).sentiment.polarity
                total_polarity += polarity
                icon = "🟢" if polarity > 0.1 else "🔴" if polarity < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_score = total_polarity / len(top_news)
            sentiment_summary = f"{avg_score:.2f}"

        # --- 3. คำนวณ Buy the Dip & TP ---
        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp1 = dip_price * 1.07
        tp2 = target_price if target_price > price else price * 1.25
        sl = dip_price * 0.95
        liq_ratio = ((my_investment_usd / price) / avg_vol) * 100
        sl_status = "YES (SAFE)" if liq_ratio < 0.05 else "RISKY"

        # --- 4. คำนวณภาพรวมคนใน ---
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

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp1, tp2, sl, sl_status, sentiment_summary, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None, None

# --- 3. การแสดงผลหน้าเว็บ (เน้นกางข้อมูลออกให้ครบ ไม่ต้องเลื่อนเยอะ) ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")
st.title("🚀 Ultimate Pro Stock Intelligence")

c_input1, c_input2, c_input3 = st.columns([2, 1, 1])
with c_input1: symbol = st.text_input("กรอกชื่อหุ้น (เช่น NVDA):", value="SKYT").upper()
with c_input2: my_money = st.number_input("เงินลงทุนต่อไม้ ($):", value=300)
with c_input3:
    st.write("##")
    btn = st.button("🚀 สแกนเลย")

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sl_stat, sent, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- ข้อมูลสำคัญ (Metric) ---
        st.header(f"📈 {symbol} | {s_type}")
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("Current Price", f"${fund['Price']}")
        col_m2.metric("✅ Buy Zone", f"${dip:.2f}")
        col_m3.metric("🎯 TP Short", f"${tp1:.2f}")
        col_m4.metric("🛑 Stop Loss", f"${sl:.2f}")

        # --- ตารางข้อมูลพื้นฐาน (นี่คือภาพที่ 2 ที่คุณต้องการ!) ---
        st.subheader("📑 ข้อมูลพื้นฐานแบบละเอียด (Fundamental Data)")
        st.table(pd.DataFrame([fund]).T) # ใช้ st.table เพื่อให้มันกางออกยาวๆ เห็นครบทุกบรรทัด

        st.divider()

        # --- สรุปความเชื่อมั่นและเทคนิค ---
        st.markdown(f"**🚩 Signal:** {signal} | **RSI:** {fund['RSI (14)']} | **News Sentiment:** {sent}")
        if summary['total_shares'] > 0:
            sell_p = (summary['sold_shares'] / summary['total_shares']) * 100
            st.warning(f"🏢 Insider ขายออกรวม: {sell_p:.2f}% | มูลค่า: ${summary['sold_value']:,.2f}")

        # --- กราฟและข่าว ---
        
        st.image(chart, use_container_width=True)
        
        st.subheader("📰 ข่าวล่าสุด")
        for line in news[:10]:
            st.write(line)
    else:
        st.error("หาหุ้นไม่เจอครับ ลองเช็คตัวสะกดดูนะ")
