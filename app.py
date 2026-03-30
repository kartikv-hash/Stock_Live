import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
from datetime import datetime, timedelta

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Live Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    h1, h2, h3 { font-family: 'IBM Plex Mono', monospace; }
    .metric-card {
        background: #0f1117;
        border: 1px solid #2a2d3e;
        border-radius: 8px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.5rem;
    }
    .price-up { color: #00e676; font-weight: 600; }
    .price-down { color: #ff5252; font-weight: 600; }
    .tag {
        display: inline-block;
        background: #1e2130;
        color: #7c83fd;
        border-radius: 4px;
        padding: 2px 8px;
        font-size: 0.75rem;
        font-family: 'IBM Plex Mono', monospace;
        margin-right: 4px;
    }
    .stMetric { background: #0f1117; border-radius: 8px; padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 Stock Dashboard")
    st.markdown("---")

    ticker_input = st.text_input("🔍 Ticker Symbol", value="AAPL", max_chars=10).upper().strip()

    st.markdown("#### Watchlist")
    watchlist = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "TSLA", "META", "SPY"]
    selected_from_watchlist = st.selectbox("Quick select", ["—"] + watchlist)
    if selected_from_watchlist != "—":
        ticker_input = selected_from_watchlist

    st.markdown("---")
    period_map = {
        "1 Day": "1d",
        "5 Days": "5d",
        "1 Month": "1mo",
        "3 Months": "3mo",
        "6 Months": "6mo",
        "1 Year": "1y",
        "2 Years": "2y",
        "5 Years": "5y",
    }
    period_label = st.selectbox("📅 Time Period", list(period_map.keys()), index=4)
    period = period_map[period_label]

    interval_map = {
        "1 Day": "5m",
        "5 Days": "15m",
        "1 Month": "1d",
        "3 Months": "1d",
        "6 Months": "1d",
        "1 Year": "1wk",
        "2 Years": "1wk",
        "5 Years": "1mo",
    }
    interval = interval_map[period_label]

    st.markdown("---")
    show_sma = st.checkbox("Show SMA (20 / 50)", value=True)
    show_bb = st.checkbox("Show Bollinger Bands", value=False)
    show_volume = st.checkbox("Show Volume", value=True)
    show_rsi = st.checkbox("Show RSI", value=True)
    show_macd = st.checkbox("Show MACD", value=False)

    st.markdown("---")
    st.caption("Data via Yahoo Finance · Refreshes on reload")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()

# ─── Data Fetching ────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def get_ticker_data(ticker, period, interval):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period=period, interval=interval)
        info = t.info
        return hist, info, None
    except Exception as e:
        return None, None, str(e)

@st.cache_data(ttl=300)
def get_news(ticker):
    try:
        t = yf.Ticker(ticker)
        return t.news or []
    except:
        return []

# ─── Technicals ───────────────────────────────────────────────────────────────
def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_macd(series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def compute_bollinger(series, window=20):
    sma = series.rolling(window).mean()
    std = series.rolling(window).std()
    return sma + 2 * std, sma - 2 * std

# ─── Main ─────────────────────────────────────────────────────────────────────
hist, info, error = get_ticker_data(ticker_input, period, interval)

if error or hist is None or hist.empty:
    st.error(f"❌ Could not load data for **{ticker_input}**. Check the ticker symbol and try again.")
    st.stop()

# Header
company_name = info.get("shortName", ticker_input)
sector = info.get("sector", "N/A")
industry = info.get("industry", "N/A")
exchange = info.get("exchange", "")

st.markdown(f"# {company_name}")
st.markdown(
    f'<span class="tag">{ticker_input}</span>'
    f'<span class="tag">{exchange}</span>'
    f'<span class="tag">{sector}</span>'
    f'<span class="tag">{industry}</span>',
    unsafe_allow_html=True
)
st.markdown("---")

# ─── Key Metrics ──────────────────────────────────────────────────────────────
current_price = hist["Close"].iloc[-1]
prev_close = info.get("previousClose") or (hist["Close"].iloc[-2] if len(hist) > 1 else current_price)
price_change = current_price - prev_close
price_change_pct = (price_change / prev_close) * 100
arrow = "▲" if price_change >= 0 else "▼"
color_class = "price-up" if price_change >= 0 else "price-down"

col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("💰 Price", f"${current_price:,.2f}", f"{arrow} {price_change_pct:+.2f}%")
with col2:
    mkt_cap = info.get("marketCap")
    mkt_cap_str = f"${mkt_cap/1e12:.2f}T" if mkt_cap and mkt_cap >= 1e12 else (f"${mkt_cap/1e9:.2f}B" if mkt_cap else "N/A")
    st.metric("🏢 Market Cap", mkt_cap_str)
with col3:
    vol = hist["Volume"].iloc[-1]
    avg_vol = info.get("averageVolume") or hist["Volume"].mean()
    st.metric("📊 Volume", f"{vol/1e6:.2f}M", f"Avg: {avg_vol/1e6:.2f}M")
with col4:
    pe = info.get("trailingPE")
    st.metric("📐 P/E Ratio", f"{pe:.1f}" if pe else "N/A")
with col5:
    week52_high = info.get("fiftyTwoWeekHigh")
    week52_low = info.get("fiftyTwoWeekLow")
    st.metric("📅 52W High", f"${week52_high:.2f}" if week52_high else "N/A")
with col6:
    st.metric("📅 52W Low", f"${week52_low:.2f}" if week52_low else "N/A")

st.markdown("---")

# ─── Price Chart ──────────────────────────────────────────────────────────────
subplot_count = 1 + (1 if show_volume else 0) + (1 if show_rsi else 0) + (1 if show_macd else 0)
row_heights = [0.5]
if show_volume: row_heights.append(0.15)
if show_rsi:    row_heights.append(0.18)
if show_macd:   row_heights.append(0.18)
total = sum(row_heights)
row_heights = [r / total for r in row_heights]

specs = [[{"secondary_y": False}]] * subplot_count
fig = make_subplots(
    rows=subplot_count, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    row_heights=row_heights,
    specs=specs
)

# Candlestick
fig.add_trace(go.Candlestick(
    x=hist.index,
    open=hist["Open"], high=hist["High"],
    low=hist["Low"], close=hist["Close"],
    name="Price",
    increasing_line_color="#00e676",
    decreasing_line_color="#ff5252",
    increasing_fillcolor="#00e676",
    decreasing_fillcolor="#ff5252",
), row=1, col=1)

# SMA
if show_sma:
    sma20 = hist["Close"].rolling(20).mean()
    sma50 = hist["Close"].rolling(50).mean()
    fig.add_trace(go.Scatter(x=hist.index, y=sma20, name="SMA 20", line=dict(color="#ffab40", width=1.2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=sma50, name="SMA 50", line=dict(color="#7c83fd", width=1.2)), row=1, col=1)

# Bollinger Bands
if show_bb:
    bb_upper, bb_lower = compute_bollinger(hist["Close"])
    fig.add_trace(go.Scatter(x=hist.index, y=bb_upper, name="BB Upper", line=dict(color="#80cbc4", width=1, dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=bb_lower, name="BB Lower", line=dict(color="#80cbc4", width=1, dash="dot"), fill="tonexty", fillcolor="rgba(128,203,196,0.05)"), row=1, col=1)

current_row = 2

# Volume
if show_volume:
    colors = ["#00e676" if c >= o else "#ff5252" for c, o in zip(hist["Close"], hist["Open"])]
    fig.add_trace(go.Bar(x=hist.index, y=hist["Volume"], name="Volume", marker_color=colors, opacity=0.7), row=current_row, col=1)
    fig.update_yaxes(title_text="Volume", row=current_row, col=1)
    current_row += 1

# RSI
if show_rsi:
    rsi = compute_rsi(hist["Close"])
    fig.add_trace(go.Scatter(x=hist.index, y=rsi, name="RSI", line=dict(color="#ce93d8", width=1.5)), row=current_row, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ff5252", opacity=0.5, row=current_row, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#00e676", opacity=0.5, row=current_row, col=1)
    fig.update_yaxes(title_text="RSI", range=[0, 100], row=current_row, col=1)
    current_row += 1

# MACD
if show_macd:
    macd_line, signal_line = compute_macd(hist["Close"])
    hist_bars = macd_line - signal_line
    bar_colors = ["#00e676" if v >= 0 else "#ff5252" for v in hist_bars]
    fig.add_trace(go.Bar(x=hist.index, y=hist_bars, name="MACD Hist", marker_color=bar_colors, opacity=0.6), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=macd_line, name="MACD", line=dict(color="#7c83fd", width=1.5)), row=current_row, col=1)
    fig.add_trace(go.Scatter(x=hist.index, y=signal_line, name="Signal", line=dict(color="#ffab40", width=1.5)), row=current_row, col=1)
    fig.update_yaxes(title_text="MACD", row=current_row, col=1)

fig.update_layout(
    height=700,
    paper_bgcolor="#0f1117",
    plot_bgcolor="#0f1117",
    font=dict(color="#e0e0e0", family="IBM Plex Mono"),
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=0, r=0, t=10, b=0),
)
fig.update_xaxes(gridcolor="#1e2130", showgrid=True)
fig.update_yaxes(gridcolor="#1e2130", showgrid=True)

st.plotly_chart(fig, use_container_width=True)

# ─── Company Info + News ──────────────────────────────────────────────────────
col_info, col_news = st.columns([1, 2])

with col_info:
    st.markdown("### 🏢 Company Info")
    info_items = {
        "CEO": info.get("companyOfficers", [{}])[0].get("name", "N/A") if info.get("companyOfficers") else "N/A",
        "Employees": f"{info.get('fullTimeEmployees', 0):,}" if info.get("fullTimeEmployees") else "N/A",
        "Country": info.get("country", "N/A"),
        "Website": info.get("website", "N/A"),
        "Dividend Yield": f"{info.get('dividendYield', 0)*100:.2f}%" if info.get("dividendYield") else "N/A",
        "Beta": f"{info.get('beta', 0):.2f}" if info.get("beta") else "N/A",
        "EPS (TTM)": f"${info.get('trailingEps', 0):.2f}" if info.get("trailingEps") else "N/A",
        "Revenue (TTM)": f"${info.get('totalRevenue', 0)/1e9:.2f}B" if info.get("totalRevenue") else "N/A",
    }
    for k, v in info_items.items():
        st.markdown(f"**{k}:** {v}")

    summary = info.get("longBusinessSummary", "")
    if summary:
        with st.expander("📄 Business Summary"):
            st.write(summary)

with col_news:
    st.markdown("### 📰 Latest News")
    news = get_news(ticker_input)
    if news:
        for item in news[:8]:
            title = item.get("title", "No title")
            link = item.get("link", "#")
            publisher = item.get("publisher", "")
            pub_time = item.get("providerPublishTime", 0)
            time_str = datetime.fromtimestamp(pub_time).strftime("%b %d, %Y") if pub_time else ""
            st.markdown(f"🔹 [{title}]({link})  \n<small style='color:#888'>{publisher} · {time_str}</small>", unsafe_allow_html=True)
            st.markdown("---")
    else:
        st.info("No recent news available.")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · Data via Yahoo Finance · Not financial advice")
