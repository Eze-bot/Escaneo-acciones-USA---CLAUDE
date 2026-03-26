import plotly.graph_objects as go
from plotly.subplots import make_subplots


def make_price_rsi_chart(result: dict) -> go.Figure:
    price_s = result.get("price_series")
    rsi_s   = result.get("rsi_series")
    macd_df = result.get("macd_df")
    vwap_s  = result.get("vwap_series")
    symbol  = result.get("symbol", "")

    if price_s is None or price_s.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin datos suficientes", xref="paper", yref="paper",
                           x=0.5, y=0.5, showarrow=False, font=dict(size=14))
        return fig

    n       = min(78, len(price_s))
    price_s = price_s.iloc[-n:]
    rsi_s   = rsi_s.iloc[-n:]   if rsi_s   is not None else None
    vwap_s  = vwap_s.iloc[-n:]  if vwap_s  is not None else None
    macd_s  = macd_df.iloc[-n:] if macd_df is not None else None

    entry       = result.get("entry", 0)
    stop_loss   = result.get("stop_loss", 0)
    take_profit = result.get("take_profit", 0)
    x0, x1     = price_s.index[0], price_s.index[-1]

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        vertical_spacing=0.04, row_heights=[0.55, 0.22, 0.23],
                        subplot_titles=[f"{symbol} · Precio & VWAP", "MACD", "RSI"])

    # Precio
    fig.add_trace(go.Scatter(x=price_s.index, y=price_s.values, mode="lines",
                             name="Precio", line=dict(color="#00D4FF", width=2)), row=1, col=1)
    if vwap_s is not None:
        fig.add_trace(go.Scatter(x=vwap_s.index, y=vwap_s.values, mode="lines",
                                 name="VWAP", line=dict(color="#FFB800", width=1.5, dash="dot")), row=1, col=1)

    for level, color, label in [(entry, "#4CAF50", f"Entrada ${entry:.2f}"),
                                  (stop_loss, "#EF5350", f"Stop ${stop_loss:.2f}"),
                                  (take_profit, "#2196F3", f"TP ${take_profit:.2f}")]:
        if level:
            fig.add_shape(type="line", x0=x0, x1=x1, y0=level, y1=level,
                          line=dict(color=color, width=1.5, dash="dash"), row=1, col=1)
            fig.add_annotation(x=x1, y=level, text=f"  {label}", showarrow=False,
                               font=dict(color=color, size=10), xanchor="left", row=1, col=1)

    # MACD
    if macd_s is not None:
        colors = ["#26A69A" if v >= 0 else "#EF5350" for v in macd_s["Histogram"]]
        fig.add_trace(go.Bar(x=macd_s.index, y=macd_s["Histogram"],
                             name="Histograma", marker_color=colors, opacity=0.7), row=2, col=1)
        fig.add_trace(go.Scatter(x=macd_s.index, y=macd_s["MACD"], mode="lines",
                                 name="MACD", line=dict(color="#00D4FF", width=1.5)), row=2, col=1)
        fig.add_trace(go.Scatter(x=macd_s.index, y=macd_s["Signal"], mode="lines",
                                 name="Signal", line=dict(color="#FF6B35", width=1.5)), row=2, col=1)
        fig.add_hline(y=0, line=dict(color="gray", width=0.8, dash="dot"), row=2, col=1)

    # RSI
    if rsi_s is not None:
        fig.add_trace(go.Scatter(x=rsi_s.index, y=rsi_s.values, mode="lines",
                                 name="RSI", line=dict(color="#CE93D8", width=2),
                                 fill="tozeroy", fillcolor="rgba(206,147,216,0.1)"), row=3, col=1)
        for level, color in [(70, "#EF5350"), (30, "#26A69A")]:
            fig.add_hline(y=level, line=dict(color=color, width=1, dash="dot"), row=3, col=1)

    fig.update_layout(
        height=600, template="plotly_dark",
        paper_bgcolor="#0E1117", plot_bgcolor="#0E1117",
        font=dict(family="monospace", size=11, color="#E0E0E0"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=80, t=40, b=10), hovermode="x unified",
    )
    fig.update_yaxes(gridcolor="#1E1E2E", gridwidth=0.5)
    fig.update_xaxes(gridcolor="#1E1E2E", gridwidth=0.5, rangeslider_visible=False)
    return fig
