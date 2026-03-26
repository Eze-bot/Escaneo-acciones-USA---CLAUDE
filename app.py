"""
app.py  ·  Stock Bot — Analizador de Acciones USA para Day Trading
Interfaz principal con Streamlit.
"""

import streamlit as st
import pandas as pd
import sys, os, time
from datetime import datetime

# ── Path ──────────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

import config
from modules.market_data import (
    load_tickers_from_csv, get_ticker_info,
    get_premarket_data, get_ohlcv, get_daily_ohlcv,
    get_news, detect_trend,
)
from modules.indicators import get_signals
from modules.sentiment import analyze_sentiment
from modules.screener import passes_filters, build_result, rank_and_select
from modules.charts import make_price_rsi_chart

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="StockBot · Day Trading Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Space+Grotesk:wght@400;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
  code, .mono { font-family: 'JetBrains Mono', monospace !important; }

  .stApp { background: #0A0E1A; }

  .header-box {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B2838 100%);
    border: 1px solid #1E3A5F;
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 24px;
  }
  .header-box h1 { color: #00D4FF; font-size: 2rem; margin: 0; letter-spacing: -0.5px; }
  .header-box p  { color: #8899AA; margin: 4px 0 0; font-size: 0.9rem; }

  .result-card {
    background: #0D1B2A;
    border: 1px solid #1E3A5F;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
  }
  .result-card.top { border-color: #00D4FF; box-shadow: 0 0 20px rgba(0,212,255,0.08); }

  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
  .badge-etf   { background: #1A237E; color: #7986CB; }
  .badge-stock { background: #1B5E20; color: #81C784; }
  .badge-up    { background: #1B5E20; color: #A5D6A7; }
  .badge-down  { background: #7F0000; color: #EF9A9A; }
  .badge-lat   { background: #33312A; color: #FFD54F; }

  .metric-row {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin: 10px 0;
  }
  .metric-item {
    background: #141E30;
    border-radius: 8px;
    padding: 8px 14px;
    min-width: 110px;
    text-align: center;
  }
  .metric-item .val { font-size: 1.1rem; font-weight: 700; color: #E0E0E0; }
  .metric-item .lbl { font-size: 0.7rem; color: #607D8B; text-transform: uppercase; letter-spacing: 1px; }

  .score-bar {
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(90deg, #EF5350, #FFB800, #4CAF50);
    margin: 6px 0 14px;
  }
  .score-marker {
    width: 12px;
    height: 12px;
    background: white;
    border-radius: 50%;
    position: relative;
    top: -9px;
    box-shadow: 0 0 6px rgba(255,255,255,0.6);
  }

  .sentiment-box {
    background: #111827;
    border-left: 3px solid #7C4DFF;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    margin: 10px 0;
    font-size: 0.85rem;
    color: #CFD8DC;
  }

  .trade-levels {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 10px;
  }
  .level-entry { color: #4CAF50; font-weight: 700; }
  .level-stop  { color: #EF5350; font-weight: 700; }
  .level-tp    { color: #2196F3; font-weight: 700; }

  .rank-badge {
    background: #00D4FF;
    color: #0A0E1A;
    font-weight: 700;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
  }

  .sidebar-section {
    background: #0D1B2A;
    border: 1px solid #1E3A5F;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 14px;
  }

  div[data-testid="stProgress"] > div { background: #00D4FF !important; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Configuración")

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**🔑 API Key Anthropic**")
    if config.ANTHROPIC_API_KEY:
        st.success("✅ API Key cargada desde Secrets")
    else:
        api_key = st.text_input("", type="password", value="",
                                 placeholder="sk-ant-... (o configurá en Secrets)")
        if api_key:
            config.ANTHROPIC_API_KEY = api_key
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**📁 Lista de Tickers**")
    uploaded_file = st.file_uploader("Subí tu CSV con tickers", type=["csv"])
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**🏷️ Tipos de activos**")
    include_stocks   = st.checkbox("Acciones",           value=True)
    include_etf      = st.checkbox("ETFs",               value=True)
    include_lev      = st.checkbox("ETFs Apalancados",   value=False)
    include_inv      = st.checkbox("ETFs Inversos",      value=False)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**💲 Filtros de Precio**")
    min_price = st.number_input("Precio mínimo (USD)", value=config.MIN_PRICE,
                                 min_value=0.0, step=1.0)
    max_price = st.number_input("Precio máximo (USD)", value=config.MAX_PRICE,
                                 min_value=0.0, step=10.0)
    config.MIN_PRICE = min_price
    config.MAX_PRICE = max_price
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**📊 Filtros de GAP**")
    min_gap = st.number_input("GAP mínimo (%)", value=config.MIN_GAP_PCT,
                               min_value=0.0, step=0.1, format="%.1f")
    max_gap = st.number_input("GAP máximo (%)", value=config.MAX_GAP_PCT,
                               min_value=0.0, step=1.0, format="%.1f")
    config.MIN_GAP_PCT = min_gap
    config.MAX_GAP_PCT = max_gap
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown("**🛡️ Gestión de Riesgo**")
    stop_loss = st.number_input("Stop Loss (%)", value=config.STOP_LOSS_PCT,
                                 min_value=0.1, step=0.1, format="%.1f")
    target = st.number_input("Target de ganancia (%)", value=config.TARGET_PROFIT_PCT,
                              min_value=0.1, step=0.1, format="%.1f")
    config.STOP_LOSS_PCT = stop_loss
    config.TARGET_PROFIT_PCT = target
    st.caption(f"Comisión broker: {config.BROKER_FEE_PCT}% (fija)")
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="header-box">
  <h1>📈 StockBot · Day Trading Scanner</h1>
  <p>Análisis técnico + IA · Mercado USA · {datetime.now().strftime('%A %d/%m/%Y %H:%M')}</p>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  CARGA DE TICKERS
# ══════════════════════════════════════════════════════════════════════════════
ticker_records = []  # lista de dicts {symbol, tipo}

if uploaded_file:
    try:
        ticker_records = load_tickers_from_csv(
            uploaded_file,
            include_leveraged=include_lev,
            include_inverse=include_inv,
        )
    except Exception as e:
        st.error(f"❌ Error al leer el CSV: {e}")
else:
    # Usar el CSV incluido en el repo
    import os
    default_csv = os.path.join(os.path.dirname(__file__), "data", "tickers.csv")
    if os.path.exists(default_csv):
        ticker_records = load_tickers_from_csv(
            default_csv,
            include_leveraged=include_lev,
            include_inverse=include_inv,
        )

# Aplicar filtro de tipo de activo
if ticker_records:
    filtered = []
    for r in ticker_records:
        t = r["tipo"].upper()
        if t == "ACCION" and not include_stocks:
            continue
        if t == "ETF" and not include_etf:
            continue
        if t == "ETF_APALANCADO" and not include_lev:
            continue
        if t == "ETF_INVERSO" and not include_inv:
            continue
        filtered.append(r)
    ticker_records = filtered

tickers = [r["symbol"] for r in ticker_records]
tipo_map = {r["symbol"]: r["tipo"] for r in ticker_records}

if ticker_records:
    n_acc = sum(1 for r in ticker_records if r["tipo"] == "ACCION")
    n_etf = sum(1 for r in ticker_records if r["tipo"] == "ETF")
    n_lev = sum(1 for r in ticker_records if r["tipo"] == "ETF_APALANCADO")
    n_inv = sum(1 for r in ticker_records if r["tipo"] == "ETF_INVERSO")
    st.info(f"📋 **{len(tickers)} tickers** listos para analizar — "
            f"Acciones: {n_acc} · ETFs: {n_etf} · Apalancados: {n_lev} · Inversos: {n_inv}")
else:
    tipo_map = {}
    st.warning("⚠️ No hay tickers cargados. Subí tu CSV o habilitá algún tipo de activo.")


# ══════════════════════════════════════════════════════════════════════════════
#  BOTÓN DE ANÁLISIS
# ══════════════════════════════════════════════════════════════════════════════
col_btn1, col_btn2 = st.columns([2, 5])
with col_btn1:
    run_scan = st.button("🔍 EJECUTAR ANÁLISIS", type="primary", use_container_width=True)
with col_btn2:
    st.caption("Analizará todos los tickers y seleccionará el TOP 6 por score")


# ══════════════════════════════════════════════════════════════════════════════
#  ANÁLISIS PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
if run_scan and tickers:
    candidates = []
    rejected = []

    progress_bar = st.progress(0, text="Iniciando análisis...")
    status_box = st.empty()
    total = len(tickers)

    for i, symbol in enumerate(tickers):
        pct = int((i / total) * 100)
        progress_bar.progress(pct / 100, text=f"Analizando {symbol}... ({i+1}/{total})")
        status_box.caption(f"⏳ Procesando `{symbol}`")

        # 1. Pre-mercado y filtros
        premarket = get_premarket_data(symbol)
        entry_price = (premarket or {}).get("pre_price", 0)
        ok, reason = passes_filters(premarket, entry_price)

        if not ok:
            rejected.append({"symbol": symbol, "razon": reason})
            continue

        # 2. Datos e indicadores
        df_intra = get_ohlcv(symbol, period=config.PREMARKET_PERIOD,
                              interval=config.INTRADAY_INTERVAL)
        df_daily = get_daily_ohlcv(symbol)
        signals = get_signals(df_intra)
        trend = detect_trend(df_daily)

        if not signals:
            rejected.append({"symbol": symbol, "razon": "Sin datos para indicadores"})
            continue

        # 3. Info del ticker (usa tipo del CSV directamente)
        ticker_info = get_ticker_info(symbol, tipo_csv=tipo_map.get(symbol))

        # 4. Noticias + Sentimiento IA
        news = get_news(symbol, max_items=5)
        sentiment = analyze_sentiment(symbol, news, trend)

        # 5. Construir resultado
        result = build_result(ticker_info, premarket, signals, sentiment, trend)
        candidates.append(result)

        time.sleep(0.3)  # Rate limiting

    progress_bar.progress(1.0, text="✅ Análisis completado")
    status_box.empty()

    # ── Selección TOP 6 ─────────────────────────────────────────────────────
    top6 = rank_and_select(candidates)

    if not top6:
        st.warning("⚠️ Ningún ticker pasó los filtros. Revisá los parámetros en el sidebar.")
    else:
        # ── Resumen ─────────────────────────────────────────────────────────
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tickers analizados", total)
        m2.metric("Pasaron filtros", len(candidates))
        m3.metric("Rechazados", len(rejected))
        m4.metric("Seleccionados", len(top6))

        st.markdown("---")
        st.markdown("## 🏆 TOP 6 Seleccionados")

        for rank, res in enumerate(top6, 1):
            is_top = rank == 1
            card_class = "result-card top" if is_top else "result-card"

            with st.container():
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

                # ── Encabezado ──────────────────────────────────────────────
                c1, c2, c3 = st.columns([0.5, 4, 1.5])
                with c1:
                    st.markdown(f'<div class="rank-badge">#{rank}</div>', unsafe_allow_html=True)
                with c2:
                    asset_class = "badge-etf" if res["type"] == "ETF" else "badge-stock"
                    trend_class = ("badge-up" if res["trend"] == "ALCISTA"
                                   else "badge-down" if res["trend"] == "BAJISTA"
                                   else "badge-lat")
                    gap_sign = "+" if res["gap_pct"] >= 0 else ""
                    st.markdown(f"""
                    <b style='font-size:1.2rem;color:#E0E0E0'>{res['symbol']}</b>
                    &nbsp;<span style='color:#607D8B;font-size:0.9rem'>{res['name']}</span><br>
                    <span class='badge {asset_class}'>{res['type']}</span>&nbsp;
                    <span class='badge {trend_class}'>📈 {res['trend']}</span>&nbsp;
                    <span class='badge' style='background:#1A237E;color:#90CAF9'>
                      GAP {gap_sign}{res['gap_pct']:.2f}%
                    </span>
                    """, unsafe_allow_html=True)
                with c3:
                    score_pct = int(res['score'] * 100)
                    color = "#4CAF50" if score_pct >= 65 else "#FFB800" if score_pct >= 45 else "#EF5350"
                    st.markdown(f"""
                    <div style='text-align:right'>
                      <div style='font-size:1.8rem;font-weight:700;color:{color}'>{score_pct}</div>
                      <div style='font-size:0.7rem;color:#607D8B'>SCORE</div>
                    </div>
                    """, unsafe_allow_html=True)

                # ── Métricas técnicas ────────────────────────────────────────
                st.markdown(f"""
                <div class='metric-row'>
                  <div class='metric-item'>
                    <div class='val'>{res['rsi']:.1f}</div>
                    <div class='lbl'>RSI · {res['rsi_signal']}</div>
                  </div>
                  <div class='metric-item'>
                    <div class='val' style='font-size:0.9rem'>{res['macd_signal']}</div>
                    <div class='lbl'>MACD</div>
                  </div>
                  <div class='metric-item'>
                    <div class='val' style='font-size:0.9rem'>{res['vwap_signal']}</div>
                    <div class='lbl'>VWAP ${res['vwap']:.2f}</div>
                  </div>
                  <div class='metric-item'>
                    <div class='val' style='font-size:0.9rem'>{res['cvd_signal']}</div>
                    <div class='lbl'>CVD</div>
                  </div>
                  <div class='metric-item'>
                    <div class='val'>${res['pre_price']:.2f}</div>
                    <div class='lbl'>Precio Actual</div>
                  </div>
                  <div class='metric-item'>
                    <div class='val'>{res['pre_volume']:,.0f}</div>
                    <div class='lbl'>Volumen</div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # ── Sentimiento IA ───────────────────────────────────────────
                sent_icon = {"MUY ALCISTA": "🟢", "ALCISTA": "🟡",
                             "NEUTRO": "⚪", "BAJISTA": "🟠",
                             "MUY BAJISTA": "🔴"}.get(res['sentiment_label'], "⚪")
                st.markdown(f"""
                <div class='sentiment-box'>
                  <b>🤖 IA Sentimiento:</b> {sent_icon} {res['sentiment_label']}
                  (confianza: {res['sentiment_confidence']}) —
                  {res['sentiment_summary']}<br>
                  <i style='color:#90A4AE'>💡 {res['sentiment_recommendation']}</i>
                </div>
                """, unsafe_allow_html=True)

                # ── Niveles de Trade ─────────────────────────────────────────
                direction_icon = "🟢 LONG" if res['direction'] == "LONG" else "🔴 SHORT"
                st.markdown(f"""
                <div class='trade-levels'>
                  <div><span style='color:#607D8B;font-size:0.8rem'>DIRECCIÓN</span><br>
                       <b>{direction_icon}</b></div>
                  <div style='width:1px;background:#1E3A5F'></div>
                  <div><span style='color:#607D8B;font-size:0.8rem'>ENTRADA</span><br>
                       <span class='level-entry'>${res['entry']:.4f}</span></div>
                  <div><span style='color:#607D8B;font-size:0.8rem'>STOP LOSS</span><br>
                       <span class='level-stop'>${res['stop_loss']:.4f}</span></div>
                  <div><span style='color:#607D8B;font-size:0.8rem'>TAKE PROFIT</span><br>
                       <span class='level-tp'>${res['take_profit']:.4f}</span></div>
                  <div><span style='color:#607D8B;font-size:0.8rem'>R/R RATIO</span><br>
                       <b style='color:#CFD8DC'>{res['risk_reward']:.1f}x</b></div>
                  <div><span style='color:#607D8B;font-size:0.8rem'>GANANCIA NETA</span><br>
                       <b style='color:#4CAF50'>{res['net_gain_pct']:.3f}%</b></div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)

            # ── Gráfico ──────────────────────────────────────────────────────
            with st.expander(f"📊 Ver gráfico de {res['symbol']}"):
                fig = make_price_rsi_chart(res)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("")

        # ── Tabla rechazados ─────────────────────────────────────────────────
        if rejected:
            with st.expander(f"🚫 Ver {len(rejected)} tickers rechazados"):
                df_rej = pd.DataFrame(rejected)
                st.dataframe(df_rej, use_container_width=True)

elif run_scan and not tickers:
    st.error("❌ No hay tickers para analizar. Subí un CSV o revisá la lista.")
else:
    # Estado inicial
    st.markdown("""
    <div style='text-align:center;padding:60px 20px;color:#37474F'>
      <div style='font-size:3rem'>📊</div>
      <div style='font-size:1.1rem;margin-top:12px'>
        Configurá tus parámetros en el sidebar<br>y presioná <b>EJECUTAR ANÁLISIS</b>
      </div>
    </div>
    """, unsafe_allow_html=True)
