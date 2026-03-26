import pandas as pd
import numpy as np
from config import RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL


def calc_rsi(df: pd.DataFrame, period: int = RSI_PERIOD) -> pd.Series:
    close  = df["Close"]
    delta  = close.diff()
    gain   = delta.clip(lower=0)
    loss   = -delta.clip(upper=0)
    ag     = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    al     = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs     = ag / al.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).rename("RSI")


def calc_macd(df: pd.DataFrame) -> pd.DataFrame:
    close      = df["Close"]
    ema_fast   = close.ewm(span=MACD_FAST, adjust=False).mean()
    ema_slow   = close.ewm(span=MACD_SLOW, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal     = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
    return pd.DataFrame({"MACD": macd_line, "Signal": signal,
                         "Histogram": macd_line - signal}, index=df.index)


def calc_vwap(df: pd.DataFrame) -> pd.Series:
    tp   = (df["High"] + df["Low"] + df["Close"]) / 3
    return ((tp * df["Volume"]).cumsum() / df["Volume"].cumsum()).rename("VWAP")


def calc_cvd(df: pd.DataFrame) -> pd.Series:
    direction = df["Close"] - df["Open"]
    delta     = df["Volume"] * direction.apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return delta.cumsum().rename("CVD")


def get_signals(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 30:
        return {}
    rsi     = calc_rsi(df)
    macd_df = calc_macd(df)
    vwap    = calc_vwap(df)
    cvd     = calc_cvd(df)
    last    = df.iloc[-1]
    rsi_val = rsi.iloc[-1]
    hist    = macd_df["Histogram"].iloc[-1]
    hist_p  = macd_df["Histogram"].iloc[-2] if len(macd_df) > 1 else 0
    macd_v  = macd_df["MACD"].iloc[-1]
    sig_v   = macd_df["Signal"].iloc[-1]
    vwap_v  = vwap.iloc[-1]
    cvd_v   = cvd.iloc[-1]
    cvd_p   = cvd.iloc[-2] if len(cvd) > 1 else cvd_v
    close   = last["Close"]

    if rsi_val < 30:
        rsi_sig, rsi_sc = "SOBREVENDIDO", 1.0
    elif rsi_val < 45:
        rsi_sig, rsi_sc = "NEUTRO-COMPRA", 0.65
    elif rsi_val < 55:
        rsi_sig, rsi_sc = "NEUTRO", 0.5
    elif rsi_val < 70:
        rsi_sig, rsi_sc = "NEUTRO-VENTA", 0.35
    else:
        rsi_sig, rsi_sc = "SOBRECOMPRADO", 0.0

    macd_cross  = macd_v > sig_v and hist > hist_p
    above_vwap  = close > vwap_v
    cvd_rising  = cvd_v > cvd_p

    return {
        "rsi": round(float(rsi_val), 2),
        "rsi_signal": rsi_sig, "rsi_score": rsi_sc,
        "macd": round(float(macd_v), 4),
        "macd_signal_line": round(float(sig_v), 4),
        "macd_histogram": round(float(hist), 4),
        "macd_signal": "ALCISTA" if macd_cross else "BAJISTA",
        "macd_score": 1.0 if macd_cross else 0.0,
        "vwap": round(float(vwap_v), 4),
        "vwap_signal": "SOBRE VWAP" if above_vwap else "BAJO VWAP",
        "vwap_score": 1.0 if above_vwap else 0.0,
        "cvd": round(float(cvd_v), 0),
        "cvd_signal": "COMPRADORES" if cvd_rising else "VENDEDORES",
        "cvd_score": 1.0 if cvd_rising else 0.0,
        "close": round(float(close), 4),
        "rsi_series": rsi,
        "macd_df": macd_df,
        "vwap_series": vwap,
        "price_series": df["Close"],
    }
