import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob
import datetime
import requests # ตัวช่วยส่งข้อมูลเข้า Google Form

# --- 1. ฟังก์ชันบันทึกข้อมูลผ่าน Google Form (ส่งเข้า Sheets อัตโนมัติ) ---
def log_to_sheets(symbol, money):
    # ลิงก์สำหรับส่งคำตอบเข้าฟอร์มของคุณ
    form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfLWvSOAQGO0XzO6DsMLgqjyZeKCe_tLSk1WLJYm4FL7zYPjA/formResponse"
    
    # ข้อมูลที่เราต้องการส่ง (รหัส entry จากภาพที่คุณหาได้)
    payload = {
        "entry.336685021": symbol.upper(), # รหัสช่อง Symbol
        "entry.71218977": str(money)        # รหัสช่อง Investment
    }
    
    try:
        # สั่งส่งข้อมูลแบบลับๆ หลังบ้าน
        requests.post(form_url, data=payload)
    except:
        # หากส่งไม่ได้ ให้ข้ามไปเลย ไม่ต้องขึ้น Error ให้ผู้ใช้เห็น
        pass

# --- 2. ฟังก์ชันวิเคราะห์ Logic จาก Colab (คงเดิมทุกประการ) ---
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

        if mcap > 200_000_000_000:
            stock_type = "💎 Blue Chip (หุ้นยักษ์ใหญ่ พื้นฐานแน่น ไม่แกว่งแรง)"
        elif price < 5 or mcap < 300_000_000:
            stock_type = "⚠️ Penny Stock (หุ้นจิ๋วสายซิ่ง เสี่ยงสูงมาก!)"
        elif 2_000_000_000 <= mcap <= 200_000_000_000:
            stock_type = "🚀 Mid-Cap Swing (หุ้นกลางพื้นฐานดีแต่ซิ่งแรง)"
        else:
            stock_type = "🔍 Small-Cap / Speculative (หุ้นขนาดเล็ก เน้นเก็งกำไร)"

        # --- วิเคราะห์ AI Sentiment ---
        news_analysis = []
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_polarity = 0
            for i, row in top_news.iterrows():
                polarity = TextBlob(row['Title']).sentiment.polarity
                total_polarity += polarity
                icon = "🟢" if polarity > 0.1 else "🔴" if polarity < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_score = total_polarity / len(top_news)
            sentiment_summary = f"🟢 Bullish News ({avg_score:.2f})" if avg_score > 0.1 else f"🔴 Bearish News ({avg_score:.2f})" if avg_score < -0.1 else f"⚪ Neutral News ({avg_score:.2f})"
        else:
            sentiment_summary = "⚪ No recent news found"

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
        agg_summary = {'total_shares_before': 0, 'total_sold_shares': 0, 'total_sold_value': 0, 'avg_sell_price': 0}
        if insider_df is not None and not insider_df.empty:
            insider_df['shares_num'] = insider_df['#Shares'].apply(to_num)
            insider_df['total_owned_num'] = insider_df['#Shares Total'].apply(to_num)
            insider_df['value_num'] = insider_df['Value ($)'].apply(to_num)
            insider_df['cost_num'] = insider_df['Cost'].apply(to_num)
            sales = insider_df[insider_df['Transaction'].str.contains('Sale', case=False, na=False)].copy()
            if not sales.empty:
                agg_summary['total_sold_shares'] = sales['shares_num'].sum()
                agg_summary['total_sold_value'] = sales['value_num'].sum()
                agg_summary['avg_sell_price'] = sales['cost_num'].mean()
                total_current_remaining = insider_df.groupby('Insider Trading')['total_owned_num'].first().sum()
                agg_summary['total_shares_before'] = total_current_remaining + agg_summary['total_sold_shares']

        return fundament, news_analysis, insider_df, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sl_workable, sentiment_summary, stock_type
    except Exception as e:
        return None, str(e), None, None, None, None, None, None, None, None, None, None, None

# --- 3. ส่วนการแสดงผลหน้าแอป ---
st.set_page_config(page_title="Ultimate Pro Stock", layout="wide")
st.title("🚀 Ultimate Pro Stock Intelligence")

symbol = st.text_input("กรอกชื่อหุ้น (Ticker):", value="SKYT").upper()
my_money = st.number_input("เงินลงทุนต่อไม้ ($):", value=300)

if st.button("เริ่มวิเคราะห์แบบเจาะลึก"):
    # บันทึก Log ข้อมูลผ่าน Google Form
    log_to_sheets(symbol, my_money)
    
    with st.spinner('กำลังวิเคราะห์หุ้น...'):
        fund, news_list, insider_raw, summary, signal, chart, dip, tp1, tp2, sl, sl_status, sentiment_top, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        st.subheader(f"📈 วิเคราะห์แนวโน้มกราฟ {symbol} | ประเภท: {s_type}")
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Market Cap", fund['Market Cap'])
        col_m2.metric("Avg Volume", fund['Avg Volume'])
        col_m3.metric("RSI (14)", fund['RSI (14)'])

        st.divider()
        st.markdown(f"**🚩 สัญญาณเทคนิคปัจจุบัน:** {signal}")
        st.write(f"📊 SMA20: {fund['SMA20']} | SMA50: {fund['SMA50']} | SMA200: {fund['SMA200']}")
        st.write(f"📉 กระแสข่าวรวม: {sentiment_top}")

        # คำนวณแนวโน้ม
        try:
            sma20_val = float(fund['SMA20'].replace('%',''))
            trend = "🚀 ขาขึ้น (Bullish)" if sma20_val > 0 else "🕳️ มุดดิน (Oversold)" if sma20_val < -5 else "😴 พักฐาน (Sideway)"
        except:
            trend = "ไม่สามารถระบุแนวโน้มได้"
        st.info(f"💡 สรุปแนวโน้ม: {trend}")

        st.divider()
        st.subheader(f"🎯 กลยุทธ์แนะนำ: Buy the Dip (สำหรับไม้ ${my_money})")
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.success(f"✅ Buy Zone: ${dip:.2f}")
        col_s2.info(f"🎯 TP 1: ${tp1:.2f} | TP 2: ${tp2:.2f}")
        col_s3.error(f"🛑 Stop Loss: ${sl:.2f}")
        st.caption(f"🛡️ สภาพคล่อง SL: {sl_status}")

        st.divider()
        st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน {symbol}")
        if summary['total_shares_before'] > 0:
            total_sell_pct = (summary['total_sold_shares'] / summary['total_shares_before']) * 100
            st.write(f"📦 หุ้นในมือคนในรวม: {summary['total_shares_before']:,.0f} | ขายออกรวม: {total_sell_pct:.2f}%")
            st.write(f"💰 มูลค่าเงินสดรวม: ${summary['total_sold_value']:,.2f} | เพดานราคาเจ้าของ: ${summary['avg_sell_price']:.2f}")
        else:
            st.write("ไม่พบข้อมูลการขายของคนในในช่วงที่ผ่านมา")

        st.divider()
        st.image(chart, use_container_width=True)
        
        st.subheader("📰 ข่าวล่าสุด")
        for line in news_list[:10]:
            st.write(line)
    else:
        st.error(f"ไม่พบข้อมูลสำหรับ: {symbol}")
