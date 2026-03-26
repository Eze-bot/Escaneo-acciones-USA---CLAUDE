import anthropic
import json
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL


def analyze_sentiment(symbol: str, news_items: list, trend: str) -> dict:
    _no_key = {"score": 0.5, "label": "SIN API KEY", "summary": "Configurá tu API Key de Anthropic en Streamlit Secrets.", "recommendation": "", "confidence": "BAJA"}
    _no_news = {"score": 0.5, "label": "SIN NOTICIAS", "summary": "No se encontraron noticias recientes.", "recommendation": "Analizá manualmente el contexto.", "confidence": "BAJA"}

    if not ANTHROPIC_API_KEY:
        return _no_key
    if not news_items:
        return _no_news

    news_text = "\n".join([f"- [{n.get('publisher','')}] {n.get('title','')}" for n in news_items])
    prompt = f"""Eres un analista financiero experto en day trading en USA.
Analizá las siguientes noticias del ticker {symbol} con tendencia {trend}:

{news_text}

Respondé ÚNICAMENTE con JSON válido (sin markdown):
{{"score":<0.0-1.0>,"label":"<MUY ALCISTA|ALCISTA|NEUTRO|BAJISTA|MUY BAJISTA>","summary":"<1 oración>","recommendation":"<1-2 oraciones para day trading>","confidence":"<ALTA|MEDIA|BAJA>"}}"""

    try:
        client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg     = client.messages.create(model=CLAUDE_MODEL, max_tokens=400,
                                          messages=[{"role": "user", "content": prompt}])
        raw     = msg.content[0].text.strip().strip("```json").strip("```").strip()
        result  = json.loads(raw)
        return {
            "score":          float(result.get("score", 0.5)),
            "label":          result.get("label", "NEUTRO"),
            "summary":        result.get("summary", ""),
            "recommendation": result.get("recommendation", ""),
            "confidence":     result.get("confidence", "MEDIA"),
        }
    except Exception as e:
        return {"score": 0.5, "label": "ERROR", "summary": str(e)[:80], "recommendation": "", "confidence": "BAJA"}
