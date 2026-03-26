"""
market_data.py
Obtiene precios, pre-mercado, volumen e información básica usando yfinance.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

def get_ticker_info(symbol: str, tipo_csv: str = None) -> dict:
    """
    Retorna info básica del ticker: nombre, tipo, sector.
    Si tipo_csv viene del CSV propio, lo usa directamente sin consultar yfinance.
    """
    try:
        t = yf.Ticker(symbol)
        info = t.info

        # Usar tipo del CSV si está disponible
        if tipo_csv:
            tipo_map = {
                "ACCION": "Acción",
                "ETF": "ETF",
                "ETF_APALANCADO": "ETF Apalancado",
                "ETF_INVERSO": "ETF Inverso",
            }
            asset_type = tipo_map.get(tipo_csv.upper(), tipo_csv)
        else:
            asset_type = "ETF" if info.get("quoteType", "").upper() == "ETF" else "Acción"

        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "type": asset_type,
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "currency": info.get("currency", "USD"),
        }
    except Exception as e:
        return {"symbol": symbol, "name": symbol, "type": tipo_csv or "Desconocido", "error": str(e)}


def get_premarket_data(symbol: str) -> dict:
    """
    Obtiene el precio pre-mercado, precio de cierre anterior y calcula el GAP.
    Retorna None si no hay datos de pre-mercado disponibles.
    """
    try:
        t = yf.Ticker(symbol)
        info = t.info

        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        pre_price = info.get("preMarketPrice")
        pre_volume = info.get("preMarketVolume", 0)
        regular_price = info.get("regularMarketPrice") or info.get("currentPrice")
        regular_volume = info.get("regularMarketVolume", 0)

        # Usar precio de apertura si no hay pre-mercado disponible
        current_price = pre_price or regular_price

        if not prev_close or not current_price:
            return None

        gap_pct = ((current_price - prev_close) / prev_close) * 100

        return {
            "symbol": symbol,
            "prev_close": round(prev_close, 4),
            "pre_price": round(current_price, 4),
            "pre_volume": pre_volume or regular_volume,
            "gap_pct": round(gap_pct, 3),
            "gap_direction": "UP" if gap_pct > 0 else "DOWN",
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_ohlcv(symbol: str, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    """
    Descarga datos OHLCV para cálculo de indicadores.
    Retorna DataFrame con columnas: Open, High, Low, Close, Volume
    """
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period, interval=interval, prepost=True)
        if df.empty:
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def get_daily_ohlcv(symbol: str, period: str = "90d") -> pd.DataFrame:
    """Datos diarios para tendencia y análisis de largo plazo."""
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=period, interval="1d")
        if df.empty:
            return pd.DataFrame()
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def get_news(symbol: str, max_items: int = 5) -> list:
    """Obtiene noticias recientes del ticker desde Yahoo Finance."""
    try:
        t = yf.Ticker(symbol)
        news = t.news or []
        result = []
        for item in news[:max_items]:
            result.append({
                "title": item.get("title", ""),
                "publisher": item.get("publisher", ""),
                "link": item.get("link", ""),
                "published": item.get("providerPublishTime", 0),
            })
        return result
    except Exception:
        return []


def load_tickers_from_csv(filepath, include_leveraged: bool = False, include_inverse: bool = False):
    """
    Carga lista de tickers desde un CSV.
    Columnas esperadas: symbol/ticker y opcionalmente tipo.
    Retorna lista de dicts con keys: symbol, tipo
    """
    try:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower() for c in df.columns]

        # Detectar columna de símbolo
        sym_col = next((c for c in ["symbol", "ticker", "symbols", "tickers"] if c in df.columns), df.columns[0])
        # Detectar columna de tipo (opcional)
        tipo_col = next((c for c in ["tipo", "type", "asset_type"] if c in df.columns), None)

        df[sym_col] = df[sym_col].str.replace(r"\.US$", "", regex=True).str.strip().str.upper()

        result = []
        for _, row in df.iterrows():
            sym = row[sym_col]
            if not sym:
                continue
            tipo = row[tipo_col].strip().upper() if tipo_col and pd.notna(row[tipo_col]) else "ACCION"

            # Filtrar apalancados e inversos según config
            if tipo == "ETF_APALANCADO" and not include_leveraged:
                continue
            if tipo == "ETF_INVERSO" and not include_inverse:
                continue

            result.append({"symbol": sym, "tipo": tipo})

        return result
    except Exception as e:
        raise ValueError(f"Error al leer CSV: {e}")


def detect_trend(daily_df: pd.DataFrame) -> str:
    """
    Detecta tendencia usando EMAs 20 y 50 días.
    Retorna: 'ALCISTA', 'BAJISTA' o 'LATERAL'
    """
    if daily_df is None or len(daily_df) < 50:
        return "INDEFINIDA"
    close = daily_df["Close"]
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    last_close = close.iloc[-1]

    if last_close > ema20 > ema50:
        return "ALCISTA"
    elif last_close < ema20 < ema50:
        return "BAJISTA"
    else:
        return "LATERAL"
