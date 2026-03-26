import streamlit as st

def _secret(key, fallback):
    try:
        return st.secrets[key]
    except Exception:
        return fallback

# API
ANTHROPIC_API_KEY  = _secret("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL       = "claude-sonnet-4-20250514"

# Filtros
MIN_PRICE          = 5.0
MAX_PRICE          = 500.0
MIN_GAP_PCT        = 0.5
MAX_GAP_PCT        = 15.0
MIN_VOLUME         = 500_000

# Riesgo
BROKER_FEE_PCT     = 0.50
STOP_LOSS_PCT      = 1.5
TARGET_PROFIT_PCT  = 2.0

# Indicadores
RSI_PERIOD         = 14
RSI_OVERSOLD       = 30
RSI_OVERBOUGHT     = 70
MACD_FAST          = 12
MACD_SLOW          = 26
MACD_SIGNAL        = 9

# Scoring
WEIGHT_RSI         = 0.20
WEIGHT_MACD        = 0.20
WEIGHT_VWAP        = 0.20
WEIGHT_CVD         = 0.15
WEIGHT_GAP         = 0.10
WEIGHT_SENTIMENT   = 0.15

# General
TOP_N              = 6
PREMARKET_PERIOD   = "5d"
INTRADAY_INTERVAL  = "5m"
