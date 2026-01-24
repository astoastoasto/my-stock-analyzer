import streamlit as st
import pandas as pd
from finvizfinance.quote import finvizfinance
from textblob import TextBlob

# --- ฟังก์ชันหลัก (รวม Logic ทั้งหมดที่คุณต้องการ) ---
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

        # 1. จำแนกประเภทหุ้น
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

        # 2. วิเคราะห์ AI Sentiment
        news_analysis = []
        avg_score = 0
        sentiment_summary = "⚪ Neutral News (0.00)"
        if news_df is not None and not news_df.empty:
            top_news = news_df.head(15)
            total_polarity = 0
            for i, row in top_news.iterrows():
                polarity = TextBlob(row['Title']).sentiment.polarity
                total_polarity += polarity
                icon = "🟢" if polarity > 0.1 else "🔴" if polarity < -0.1 else "⚪"
                news_analysis.append(f"{icon} [{row['Date']}] {row['Title']}")
            avg_score = total_polarity / len(top_news)
            sentiment_summary = f"🟢 Bullish ({avg_score:.2f})" if avg_score > 0.1 else f"🔴 Bearish ({avg_score:.2f})" if avg_score < -0.1 else f"⚪ Neutral ({avg_score:.2f})"

        # 3. คำนวณ Buy the Dip & TP
        target_price = to_num(fundament['Target Price'])
        sma20_dist = to_num(fundament['SMA20']) / 100
        dip_price = price if sma20_dist < 0 else price * (1 - 0.02)
        tp_short = dip_price * 1.07
        tp_target = target_price if target_price > price else price * 1.25
        sl_val = dip_price * 0.95
        liq_ratio = ((my_investment_usd / price) / avg_vol) * 100
        sl_workable = "✅ SAFE" if liq_ratio < 0.05 else "⚠️ RISKY"

        # 4. คำนวณภาพรวมคนใน
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

        return fundament, news_analysis, agg_summary, tech_signal, chart_url, dip_price, tp_short, tp_target, sl_val, sl_workable, sentiment_summary, stock_type
    except Exception as e:
        return None, str(e), None, None, None, None, None, None, None, None, None, None

# --- หน้าจอ App ---
st.set_page_config(page_title="Pro Stock Intelligence", layout="wide")
st.title("🚀 Ultimate Pro Stock Intelligence")

symbol = st.text_input("กรอกชื่อหุ้น (เช่น NVDA, SKYT):", value="SKYT").upper()
my_money = st.number_input("เงินลงทุนต่อไม้ ($):", value=300)

if st.button("เริ่มวิเคราะห์แบบเจาะลึก"):
    with st.spinner('กำลังประมวลผล...'):
        fund, news, summary, signal, chart, dip, tp1, tp2, sl, sl_stat, sentiment, s_type = get_ultimate_pro_intelligence(symbol, my_money)

    if fund:
        # Header และ ประเภทหุ้น
        st.subheader(f"📈 วิเคราะห์แนวโน้ม {symbol} | ประเภท: {s_type}")
        
        # คอลัมน์สรุปข้อมูลพื้นฐาน
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Market Cap", fund['Market Cap'])
        c2.metric("Avg Volume", fund['Avg Volume'])
        c3.metric("RSI (14)", fund['RSI (14)'])
        c4.metric("Sentiment ข่าว", sentiment)

        # สรุปแนวโน้ม
        sma20_val = float(fund['SMA20'].replace('%',''))
        trend = "🚀 ขาขึ้น (Bullish)" if sma20_val > 0 else "🕳️ มุดดิน (Oversold)" if sma20_val < -5 else "😴 พักฐาน (Sideway)"
        st.info(f"🚩 สัญญาณเทคนิค: {signal} | สรุปแนวโน้ม: {trend}")

        # กราฟ
        st.image(chart, use_container_width=True)

        # กลยุทธ์แนะนำ
        st.divider()
        st.subheader("🎯 กลยุทธ์แนะนำ: Buy the Dip")
        g1, g2, g3, g4 = st.columns(4)
        g1.warning(f"✅ Buy Zone: ${dip:.2f}")
        g2.success(f"🎯 TP 1 (สั้น): ${tp1:.2f}")
        g3.success(f"🎯 TP 2 (เป้า): ${tp2:.2f}")
        g4.error(f"🛑 Stop Loss: ${sl:.2f}")
        st.caption(f"🛡️ สภาพคล่อง SL: {sl_stat}")

        # สรุปคนใน
        st.divider()
        st.subheader(f"🏢 สรุปความเชื่อมั่นคนใน (Insider Trading)")
        if summary['total_shares_before'] > 0:
            total_sell_pct = (summary['total_sold_shares'] / summary['total_shares_before']) * 100
            i1, i2, i3 = st.columns(3)
            i1.write(f"📦 ขายออกรวม: {total_sell_pct:.2f}%")
            i2.write(f"💰 มูลค่าเงินสดรวม: ${summary['total_sold_value']:,.2f}")
            i3.write(f"🔝 เพดานราคาเจ้าของ: ${summary['avg_sell_price']:.2f}")
        else:
            st.write("ไม่พบข้อมูลการขายของคนในในช่วงที่ผ่านมา")

        # ข่าว
        st.divider()
        st.subheader("📰 วิเคราะห์อารมณ์ข่าวล่าสุด")
        for line in news[:10]:
            st.write(line)
    else:
        st.error(f"เกิดข้อผิดพลาด: {news}")
