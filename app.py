import streamlit as st
import pandas as pd
import os, time
from datetime import datetime

import config
from market_data import (load_tickers_from_csv, get_ticker_info,
                          get_premarket_data, get_ohlcv, get_daily_ohlcv,
                          get_news, detect_trend)
from indicators import get_signals
from sentiment  import analyze_sentiment
from screener   import passes_filters, build_result, rank_and_select
from charts     import make_price_rsi_chart

# ── Página ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="StockBot · Day Trading Scanner",
                   page_icon="📈", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Syne',sans-serif;}
.stApp{background:#060B14;}
.header-box{background:linear-gradient(135deg,#0A1628 0%,#0E2040 100%);
  border:1px solid #1C3D6B;border-radius:14px;padding:22px 30px;margin-bottom:22px;}
.header-box h1{color:#00D4FF;font-size:2rem;margin:0;font-weight:800;}
.header-box p{color:#5D7A9A;margin:4px 0 0;font-size:.88rem;}
.result-card{background:#09111F;border:1px solid #162840;border-radius:12px;
  padding:18px 22px;margin-bottom:14px;}
.result-card.top{border-color:#00D4FF;box-shadow:0 0 28px rgba(0,212,255,.09);}
.badge{display:inline-block;padding:2px 10px;border-radius:20px;
  font-size:.72rem;font-weight:700;letter-spacing:.5px;}
.badge-etf{background:#1A237E;color:#7986CB;}
.badge-lev{background:#4A148C;color:#CE93D8;}
.badge-stock{background:#1B5E20;color:#81C784;}
.badge-up{background:#1B5E20;color:#A5D6A7;}
.badge-down{background:#7F0000;color:#EF9A9A;}
.badge-lat{background:#33312A;color:#FFD54F;}
.metric-row{display:flex;gap:14px;flex-wrap:wrap;margin:10px 0;}
.metric-item{background:#0E1A2E;border-radius:8px;padding:8px 14px;min-width:108px;text-align:center;}
.metric-item .val{font-size:1.05rem;font-weight:700;color:#E0E0E0;}
.metric-item .lbl{font-size:.68rem;color:#4A6580;text-transform:uppercase;letter-spacing:1px;}
.sentiment-box{background:#0C1525;border-left:3px solid #7C4DFF;border-radius:0 8px 8px 0;
  padding:10px 14px;margin:10px 0;font-size:.84rem;color:#B0BEC5;}
.trade-levels{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;}
.rank-badge{background:#00D4FF;color:#060B14;font-weight:800;border-radius:50%;
  width:30px;height:30px;display:inline-flex;align-items:center;justify-content:center;font-size:.9rem;}
.sidebar-section{background:#09111F;border:1px solid #162840;border-radius:8px;
  padding:14px;margin-bottom:12px;}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuración")

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**🔑 API Key Anthropic**")
    if config.ANTHROPIC_API_KEY:
        st.success("✅ API Key cargada desde Secrets")
    else:
        ak = st.text_input("", type="password", placeholder="sk-ant-...")
        if ak:
            config.ANTHROPIC_API_KEY = ak
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**📁 Lista de Tickers**")
    uploaded_file = st.file_uploader("Subí tu CSV (opcional)", type=["csv"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**🏷️ Tipos de activos**")
    include_stocks = st.checkbox("Acciones",          value=True)
    include_etf    = st.checkbox("ETFs",              value=True)
    include_lev    = st.checkbox("ETFs Apalancados",  value=False)
    include_inv    = st.checkbox("ETFs Inversos",     value=False)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**💲 Filtros de Precio**")
    config.MIN_PRICE = st.number_input("Precio mín (USD)", value=config.MIN_PRICE, min_value=0.0, step=1.0)
    config.MAX_PRICE = st.number_input("Precio máx (USD)", value=config.MAX_PRICE, min_value=0.0, step=10.0)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**📊 Filtros de GAP**")
    config.MIN_GAP_PCT = st.number_input("GAP mín (%)", value=config.MIN_GAP_PCT, min_value=0.0, step=0.1, format="%.1f")
    config.MAX_GAP_PCT = st.number_input("GAP máx (%)", value=config.MAX_GAP_PCT, min_value=0.0, step=1.0, format="%.1f")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**🛡️ Gestión de Riesgo**")
    config.STOP_LOSS_PCT    = st.number_input("Stop Loss (%)",     value=config.STOP_LOSS_PCT,    min_value=0.1, step=0.1, format="%.1f")
    config.TARGET_PROFIT_PCT= st.number_input("Target ganancia (%)",value=config.TARGET_PROFIT_PCT,min_value=0.1, step=0.1, format="%.1f")
    st.caption(f"Comisión broker: {config.BROKER_FEE_PCT}% (fija)")
    st.markdown('</div>', unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="header-box">
  <h1>📈 StockBot · Day Trading Scanner</h1>
  <p>Análisis técnico + IA · Mercado USA · {datetime.now().strftime('%A %d/%m/%Y %H:%M')}</p>
</div>""", unsafe_allow_html=True)

# ── Carga de tickers ──────────────────────────────────────────────────────────
ticker_records = []
src = uploaded_file if uploaded_file else os.path.join(os.path.dirname(__file__), "tickers.csv")

try:
    ticker_records = load_tickers_from_csv(src, include_leveraged=include_lev, include_inverse=include_inv)
except Exception as e:
    st.error(f"❌ Error al cargar tickers: {e}")

# Filtro por tipo
filtered = []
for r in ticker_records:
    t = r["tipo"].upper()
    if t == "ACCION"        and not include_stocks: continue
    if t == "ETF"           and not include_etf:    continue
    if t == "ETF_APALANCADO"and not include_lev:    continue
    if t == "ETF_INVERSO"   and not include_inv:    continue
    filtered.append(r)
ticker_records = filtered

tickers  = [r["symbol"] for r in ticker_records]
tipo_map = {r["symbol"]: r["tipo"] for r in ticker_records}

if ticker_records:
    n_a = sum(1 for r in ticker_records if r["tipo"]=="ACCION")
    n_e = sum(1 for r in ticker_records if r["tipo"]=="ETF")
    n_l = sum(1 for r in ticker_records if r["tipo"]=="ETF_APALANCADO")
    n_i = sum(1 for r in ticker_records if r["tipo"]=="ETF_INVERSO")
    st.info(f"📋 **{len(tickers)} tickers** · Acciones: {n_a} · ETFs: {n_e} · Apalancados: {n_l} · Inversos: {n_i}")

# ── Botón ─────────────────────────────────────────────────────────────────────
c1, c2 = st.columns([2, 5])
with c1:
    run_scan = st.button("🔍 EJECUTAR ANÁLISIS", type="primary", use_container_width=True)
with c2:
    st.caption("Analiza todos los tickers y selecciona el TOP 6 por score")

# ── Análisis ──────────────────────────────────────────────────────────────────
if run_scan and tickers:
    candidates, rejected = [], []
    bar    = st.progress(0, text="Iniciando análisis...")
    status = st.empty()
    total  = len(tickers)

    for i, symbol in enumerate(tickers):
        bar.progress((i+1)/total, text=f"Analizando {symbol}... ({i+1}/{total})")
        status.caption(f"⏳ `{symbol}`")

        premarket = get_premarket_data(symbol)
        entry     = (premarket or {}).get("pre_price", 0)
        ok, reason = passes_filters(premarket, entry)
        if not ok:
            rejected.append({"symbol": symbol, "razón": reason})
            continue

        df_intra = get_ohlcv(symbol, config.PREMARKET_PERIOD, config.INTRADAY_INTERVAL)
        df_daily = get_daily_ohlcv(symbol)
        signals  = get_signals(df_intra)
        trend    = detect_trend(df_daily)
        if not signals:
            rejected.append({"symbol": symbol, "razón": "Sin datos para indicadores"})
            continue

        ticker_info = get_ticker_info(symbol, tipo_csv=tipo_map.get(symbol))
        news        = get_news(symbol)
        sentiment   = analyze_sentiment(symbol, news, trend)
        result      = build_result(ticker_info, premarket, signals, sentiment, trend)
        candidates.append(result)
        time.sleep(0.3)

    bar.progress(1.0, text="✅ Análisis completado")
    status.empty()

    top6 = rank_and_select(candidates)

    if not top6:
        st.warning("⚠️ Ningún ticker pasó los filtros. Revisá los parámetros.")
    else:
        m1,m2,m3,m4 = st.columns(4)
        m1.metric("Analizados", total)
        m2.metric("Pasaron filtros", len(candidates))
        m3.metric("Rechazados", len(rejected))
        m4.metric("Seleccionados", len(top6))
        st.markdown("---")
        st.markdown("## 🏆 TOP 6 Seleccionados")

        for rank, res in enumerate(top6, 1):
            top_cls = "result-card top" if rank==1 else "result-card"
            with st.container():
                st.markdown(f'<div class="{top_cls}">', unsafe_allow_html=True)

                c1,c2,c3 = st.columns([0.5,4,1.5])
                with c1:
                    st.markdown(f'<div class="rank-badge">#{rank}</div>', unsafe_allow_html=True)
                with c2:
                    tipo = res["type"].upper()
                    if "APALANCADO" in tipo: ab = "badge-lev"
                    elif "ETF" in tipo:      ab = "badge-etf"
                    else:                    ab = "badge-stock"
                    tc = ("badge-up" if res["trend"]=="ALCISTA"
                          else "badge-down" if res["trend"]=="BAJISTA" else "badge-lat")
                    gs = "+" if res["gap_pct"]>=0 else ""
                    st.markdown(f"""
                    <b style='font-size:1.2rem;color:#E0E0E0'>{res['symbol']}</b>
                    &nbsp;<span style='color:#4A6580;font-size:.88rem'>{res['name']}</span><br>
                    <span class='badge {ab}'>{res['type']}</span>&nbsp;
                    <span class='badge {tc}'>📈 {res['trend']}</span>&nbsp;
                    <span class='badge' style='background:#0D2040;color:#90CAF9'>
                      GAP {gs}{res['gap_pct']:.2f}%</span>
                    """, unsafe_allow_html=True)
                with c3:
                    sp = int(res['score']*100)
                    sc = "#4CAF50" if sp>=65 else "#FFB800" if sp>=45 else "#EF5350"
                    st.markdown(f"""
                    <div style='text-align:right'>
                      <div style='font-size:1.8rem;font-weight:800;color:{sc}'>{sp}</div>
                      <div style='font-size:.68rem;color:#4A6580'>SCORE</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div class='metric-row'>
                  <div class='metric-item'><div class='val'>{res['rsi']:.1f}</div><div class='lbl'>RSI · {res['rsi_signal']}</div></div>
                  <div class='metric-item'><div class='val' style='font-size:.88rem'>{res['macd_signal']}</div><div class='lbl'>MACD</div></div>
                  <div class='metric-item'><div class='val' style='font-size:.88rem'>{res['vwap_signal']}</div><div class='lbl'>VWAP ${res['vwap']:.2f}</div></div>
                  <div class='metric-item'><div class='val' style='font-size:.88rem'>{res['cvd_signal']}</div><div class='lbl'>CVD</div></div>
                  <div class='metric-item'><div class='val'>${res['pre_price']:.2f}</div><div class='lbl'>Precio</div></div>
                  <div class='metric-item'><div class='val'>{res['pre_volume']:,.0f}</div><div class='lbl'>Volumen</div></div>
                </div>""", unsafe_allow_html=True)

                si = {"MUY ALCISTA":"🟢","ALCISTA":"🟡","NEUTRO":"⚪","BAJISTA":"🟠","MUY BAJISTA":"🔴"}.get(res['sentiment_label'],"⚪")
                st.markdown(f"""
                <div class='sentiment-box'>
                  <b>🤖 IA:</b> {si} {res['sentiment_label']} (confianza: {res['sentiment_confidence']}) —
                  {res['sentiment_summary']}<br>
                  <i style='color:#7986CB'>💡 {res['sentiment_recommendation']}</i>
                </div>""", unsafe_allow_html=True)

                di = "🟢 LONG" if res['direction']=="LONG" else "🔴 SHORT"
                st.markdown(f"""
                <div class='trade-levels'>
                  <div><span style='color:#4A6580;font-size:.75rem'>DIRECCIÓN</span><br><b>{di}</b></div>
                  <div style='width:1px;background:#162840'></div>
                  <div><span style='color:#4A6580;font-size:.75rem'>ENTRADA</span><br><b style='color:#4CAF50'>${res['entry']:.4f}</b></div>
                  <div><span style='color:#4A6580;font-size:.75rem'>STOP LOSS</span><br><b style='color:#EF5350'>${res['stop_loss']:.4f}</b></div>
                  <div><span style='color:#4A6580;font-size:.75rem'>TAKE PROFIT</span><br><b style='color:#2196F3'>${res['take_profit']:.4f}</b></div>
                  <div><span style='color:#4A6580;font-size:.75rem'>R/R</span><br><b style='color:#CFD8DC'>{res['risk_reward']:.1f}x</b></div>
                  <div><span style='color:#4A6580;font-size:.75rem'>GANANCIA NETA</span><br><b style='color:#4CAF50'>{res['net_gain_pct']:.3f}%</b></div>
                </div>""", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            with st.expander(f"📊 Gráfico {res['symbol']}"):
                st.plotly_chart(make_price_rsi_chart(res), use_container_width=True)
            st.markdown("")

        if rejected:
            with st.expander(f"🚫 {len(rejected)} tickers rechazados"):
                st.dataframe(pd.DataFrame(rejected), use_container_width=True)

elif run_scan and not tickers:
    st.error("❌ No hay tickers para analizar.")
else:
    st.markdown("""
    <div style='text-align:center;padding:60px 20px;color:#243447'>
      <div style='font-size:3rem'>📊</div>
      <div style='font-size:1.05rem;margin-top:12px'>
        Configurá los parámetros en el sidebar<br>y presioná <b>EJECUTAR ANÁLISIS</b>
      </div>
    </div>""", unsafe_allow_html=True)
