from config import (
    MIN_PRICE, MAX_PRICE, MIN_GAP_PCT, MAX_GAP_PCT, MIN_VOLUME,
    WEIGHT_RSI, WEIGHT_MACD, WEIGHT_VWAP, WEIGHT_CVD,
    WEIGHT_GAP, WEIGHT_SENTIMENT, STOP_LOSS_PCT,
    BROKER_FEE_PCT, TARGET_PROFIT_PCT, TOP_N,
)


def passes_filters(premarket: dict, price: float) -> tuple:
    if not premarket or "error" in premarket:
        return False, "Sin datos de mercado"
    gap    = abs(premarket.get("gap_pct", 0))
    volume = premarket.get("pre_volume", 0)
    p      = premarket.get("pre_price", 0)
    if p < MIN_PRICE:   return False, f"Precio ${p:.2f} < mínimo ${MIN_PRICE}"
    if p > MAX_PRICE:   return False, f"Precio ${p:.2f} > máximo ${MAX_PRICE}"
    if gap < MIN_GAP_PCT: return False, f"GAP {gap:.2f}% < mínimo {MIN_GAP_PCT}%"
    if gap > MAX_GAP_PCT: return False, f"GAP {gap:.2f}% > máximo {MAX_GAP_PCT}%"
    if volume < MIN_VOLUME: return False, f"Volumen {volume:,} < mínimo {MIN_VOLUME:,}"
    return True, "OK"


def _gap_score(gap_pct: float) -> float:
    g = abs(gap_pct)
    if g < MIN_GAP_PCT:  return 0.0
    if g <= 5.0:         return (g - MIN_GAP_PCT) / (5.0 - MIN_GAP_PCT)
    if g <= 10.0:        return 1.0
    return max(0.0, 1.0 - (g - 10.0) / 5.0)


def calc_total_score(signals: dict, sentiment: dict, gap_pct: float) -> float:
    return round(
        signals.get("rsi_score",  0.5) * WEIGHT_RSI
        + signals.get("macd_score", 0.5) * WEIGHT_MACD
        + signals.get("vwap_score", 0.5) * WEIGHT_VWAP
        + signals.get("cvd_score",  0.5) * WEIGHT_CVD
        + _gap_score(gap_pct)            * WEIGHT_GAP
        + sentiment.get("score",    0.5) * WEIGHT_SENTIMENT,
        4
    )


def calc_trade_levels(entry: float, gap_dir: str) -> dict:
    b = BROKER_FEE_PCT / 100
    if gap_dir == "UP":
        sl = entry * (1 - STOP_LOSS_PCT / 100)
        tp = entry * (1 + TARGET_PROFIT_PCT / 100 + b * 2)
    else:
        sl = entry * (1 + STOP_LOSS_PCT / 100)
        tp = entry * (1 - TARGET_PROFIT_PCT / 100 - b * 2)
    return {
        "entry":        round(entry, 4),
        "stop_loss":    round(sl, 4),
        "take_profit":  round(tp, 4),
        "risk_reward":  round(TARGET_PROFIT_PCT / STOP_LOSS_PCT, 2),
        "net_gain_pct": round(TARGET_PROFIT_PCT - b * 2 * 100, 3),
        "direction":    "LONG" if gap_dir == "UP" else "SHORT",
    }


def build_result(ticker_info, premarket, signals, sentiment, trend) -> dict:
    entry   = premarket.get("pre_price", 0)
    gap_pct = premarket.get("gap_pct", 0)
    gap_dir = premarket.get("gap_direction", "UP")
    score   = calc_total_score(signals, sentiment, gap_pct)
    trade   = calc_trade_levels(entry, gap_dir)
    return {
        "symbol":                  ticker_info.get("symbol", ""),
        "name":                    ticker_info.get("name", ""),
        "type":                    ticker_info.get("type", "Acción"),
        "sector":                  ticker_info.get("sector", "N/A"),
        "trend":                   trend,
        "prev_close":              premarket.get("prev_close", 0),
        "pre_price":               entry,
        "pre_volume":              premarket.get("pre_volume", 0),
        "gap_pct":                 gap_pct,
        "gap_direction":           gap_dir,
        "rsi":                     signals.get("rsi", 50),
        "rsi_signal":              signals.get("rsi_signal", "NEUTRO"),
        "macd":                    signals.get("macd", 0),
        "macd_signal":             signals.get("macd_signal", "NEUTRO"),
        "vwap":                    signals.get("vwap", 0),
        "vwap_signal":             signals.get("vwap_signal", "NEUTRO"),
        "cvd":                     signals.get("cvd", 0),
        "cvd_signal":              signals.get("cvd_signal", "NEUTRO"),
        "rsi_series":              signals.get("rsi_series"),
        "price_series":            signals.get("price_series"),
        "macd_df":                 signals.get("macd_df"),
        "vwap_series":             signals.get("vwap_series"),
        "sentiment_score":         sentiment.get("score", 0.5),
        "sentiment_label":         sentiment.get("label", "NEUTRO"),
        "sentiment_summary":       sentiment.get("summary", ""),
        "sentiment_recommendation":sentiment.get("recommendation", ""),
        "sentiment_confidence":    sentiment.get("confidence", "BAJA"),
        "entry":                   trade["entry"],
        "stop_loss":               trade["stop_loss"],
        "take_profit":             trade["take_profit"],
        "risk_reward":             trade["risk_reward"],
        "net_gain_pct":            trade["net_gain_pct"],
        "direction":               trade["direction"],
        "score":                   score,
    }


def rank_and_select(candidates: list) -> list:
    valid = [c for c in candidates if c.get("score", 0) > 0]
    return sorted(valid, key=lambda x: x["score"], reverse=True)[:TOP_N]
