import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import datetime
import requests

# --- 1. ระบบบันทึกข้อมูล (Google Form) ---
def log_to_sheets(symbol, money):
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    payload = {"entry.336685021": symbol.upper(), "entry.71218977": str(money)}
    try: requests.post(form_url, data=payload)
    except: pass

# --- 2. ฟังก์ชันวิเคราะห์ (คืนค่าเดิมจากที่คุณเคยทำได้) ---
def get_ultimate_pro_intelligence(symbol, my_investment_usd=300):
    try:
        stock = finvizfinance(symbol)
        fundament = stock.ticker_fundament() # ตารางข้อมูลที่คุณต้องการ
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

        # --- ส่วนที่ 1: จำแนกประเภทหุ้น ---
        mcap = to_num(fundament['Market Cap'])
        price = to_num(fundament['Price'])
        avg_vol = to_num(fundament['Avg Volume'])
        if mcap > 200_000_000_000: stock_type = "💎 Blue Chip"
        elif price < 5 or mcap < 300_000_000: stock_type = "⚠️ Penny Stock"
        elif 2_000_000_000 <= mcap <= 200_000_000_000: stock_type = "🚀 Mid-Cap Swing"
        else: stock_type = "🔍 Small-Cap / Speculative"

        # --- ส่วนที่ 2: วิเคราะห์ AI Sentiment ---
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
        else: sentiment_summary = "N/A"

        # --- ส่วนที่ 3: คำนวณ Buy the Dip & TP ---
        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp_short = dip_price * 1.07
        tp_target = target_price if target_price > price else price * 1.25
        sl_val = dip_price * 0.95
        liq_ratio = ((my_investment_usd / price) / avg_vol) * 100
        sl_workable = "YES (SAFE)" if liq_ratio < 0.05 else "RISKY"

        # --- ส่วนที่ 4: คำนวณภาพรวมคนใน ---
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
            insider_df['Sell %'] = insider_df.apply(lambda x: f"{(x['shares_num']/(x['shares_num']+x['total_owned_num'])*100):.2f}%" if 'Sale' in x['Transaction'] else "0.00%", axis=1)

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sl_workable, liq_ratio, sentiment_summary, stock_type
    except Exception as e: return None, str(e), None, None, None, None, None, None, None, None, None, None, None, None

# --- 3. การแสดงผลแบบจัดเต็ม (เน้นครบ ไม่เน้นหลบ) ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")
st.title("🚀 Ultimate Pro Stock Intelligence")

# ส่วนรับค่า
c1, c2, c3 = st.columns([2, 2, 1])
with c1: symbol = st.text_input("กรอกชื่อหุ้น:", value="SKYT").upper()
with c2: my_money = st.number_input("เงินลงทุน ($):", value=300)
with c3:
    st.write("##")
    btn = st.button("เริ่มวิเคราะห์")

if btn:
    log_to_sheets(symbol, my_money)
    fund, news, insider, summary, signal, chart, dip, tp1, tp2, sl, sl_stat, liq, sent, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # --- ข้อมูลสรุปบนสุด ---
        st.header(f"📈 {symbol} | {s_type}")
        
        # แสดงตาราง Fundamental ที่คุณต้องการ (แบบรูปที่ 2)
        st.write("📊 **Fundamental Data Table**")
        df_fund = pd.DataFrame([fund]).T
        df_fund.columns = ["ข้อมูล"]
        st.table(df_fund) # ใช้ st.table เพื่อให้เห็นครบทุกบรรทัดไม่ต้องเลื่อนในตาราง

        st.divider()

        # --- กลยุทธ์แนะนำ ---
        st.subheader(f"🎯 กลยุทธ์แนะนำ: Buy the Dip (ไม้ ${my_money})")
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        col_s1.metric("✅ Buy Zone", f"${dip:.2f}")
        col_s2.metric("🎯 TP 1", f"${tp1:.2f}")
        col_s3.metric("🎯 TP 2", f"${tp2:.2f}")
        col_s4.metric("🛑 Stop Loss", f"${sl:.2f}")
        st.write(f"🛡️ สภาพคล่อง SL: {sl_stat} | Signal: {signal} | News Score: {sent}")

        st.divider()

        # --- สรุปคนใน ---
        st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน {symbol}")
        if summary['total_shares_before'] > 0:
            total_sell_pct = (summary['total_sold_shares'] / summary['total_shares_before']) * 100
            st.write(f"📦 หุ้นในมือรวม: {summary['total_shares_before']:,.0f} | ขายออกรวม: {total_sell_pct:.2f}%")
            st.write(f"💰 เงินสดรวม: ${summary['total_sold_value']:,.2f} | ราคาเฉลี่ยที่ขาย: ${summary['avg_sell_price']:.2f}")
        
        # ตาราง Insider
        if insider is not None:
            st.dataframe(insider[['Date', 'Insider Trading', 'Transaction', 'Cost', '#Shares', 'Value ($)', 'Sell %']].head(10), use_container_width=True)

        st.divider()

        # --- กราฟและข่าว ---
        st.image(chart, caption=f"กราฟเทคนิค {symbol}", use_container_width=True)
        st.subheader("📰 วิเคราะห์อารมณ์ข่าวล่าสุด")
        for line in news[:10]:
            st.write(line)
    else:
        st.error("ไม่พบข้อมูลหุ้น")
