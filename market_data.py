import yfinance as yf
import pandas as pd


def get_ticker_info(symbol: str, tipo_csv: str = None) -> dict:
    try:
        t = yf.Ticker(symbol)
        info = t.info
        if tipo_csv:
            tipo_map = {
                "ACCION": "Acción", "ETF": "ETF",
                "ETF_APALANCADO": "ETF Apalancado", "ETF_INVERSO": "ETF Inverso",
            }
            asset_type = tipo_map.get(tipo_csv.upper(), tipo_csv)
        else:
            asset_type = "ETF" if info.get("quoteType", "").upper() == "ETF" else "Acción"
        return {
            "symbol": symbol,
            "name": info.get("longName") or info.get("shortName", symbol),
            "type": asset_type,
            "sector": info.get("sector", "N/A"),
        }
    except Exception as e:
        return {"symbol": symbol, "name": symbol, "type": tipo_csv or "Desconocido", "error": str(e)}


def get_premarket_data(symbol: str) -> dict:
    try:
        t = yf.Ticker(symbol)
        info = t.info
        prev_close  = info.get("previousClose") or info.get("regularMarketPreviousClose")
        pre_price   = info.get("preMarketPrice")
        pre_volume  = info.get("preMarketVolume", 0)
        reg_price   = info.get("regularMarketPrice") or info.get("currentPrice")
        reg_volume  = info.get("regularMarketVolume", 0)
        current     = pre_price or reg_price
        if not prev_close or not current:
            return None
        gap_pct = ((current - prev_close) / prev_close) * 100
        return {
            "symbol":        symbol,
            "prev_close":    round(prev_close, 4),
            "pre_price":     round(current, 4),
            "pre_volume":    pre_volume or reg_volume,
            "gap_pct":       round(gap_pct, 3),
            "gap_direction": "UP" if gap_pct > 0 else "DOWN",
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_ohlcv(symbol: str, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval, prepost=True)
        if df.empty:
            return pd.DataFrame()
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def get_daily_ohlcv(symbol: str, period: str = "90d") -> pd.DataFrame:
    try:
        df = yf.Ticker(symbol).history(period=period, interval="1d")
        if df.empty:
            return pd.DataFrame()
        return df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def get_news(symbol: str, max_items: int = 5) -> list:
    try:
        news = yf.Ticker(symbol).news or []
        return [{"title": n.get("title", ""), "publisher": n.get("publisher", "")}
                for n in news[:max_items]]
    except Exception:
        return []


def load_tickers_from_csv(filepath, include_leveraged=False, include_inverse=False):
    try:
        df = pd.read_csv(filepath)
        df.columns = [c.strip().lower() for c in df.columns]
        sym_col  = next((c for c in ["symbol","ticker","symbols","tickers"] if c in df.columns), df.columns[0])
        tipo_col = next((c for c in ["tipo","type","asset_type"] if c in df.columns), None)
        df[sym_col] = df[sym_col].astype(str).str.replace(r"\.US$", "", regex=True).str.strip().str.upper()
        result = []
        for _, row in df.iterrows():
            sym  = row[sym_col]
            tipo = row[tipo_col].strip().upper() if tipo_col and pd.notna(row.get(tipo_col)) else "ACCION"
            if tipo == "ETF_APALANCADO" and not include_leveraged:
                continue
            if tipo == "ETF_INVERSO" and not include_inverse:
                continue
            result.append({"symbol": sym, "tipo": tipo})
        return result
    except Exception as e:
        raise ValueError(f"Error al leer CSV: {e}")


def detect_trend(daily_df: pd.DataFrame) -> str:
    if daily_df is None or len(daily_df) < 50:
        return "INDEFINIDA"
    close  = daily_df["Close"]
    ema20  = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50  = close.ewm(span=50, adjust=False).mean().iloc[-1]
    last   = close.iloc[-1]
    if last > ema20 > ema50:
        return "ALCISTA"
    elif last < ema20 < ema50:
        return "BAJISTA"
    return "LATERAL"
