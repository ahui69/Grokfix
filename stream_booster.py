from __future__ import annotations
import re, asyncio, time
from typing import Optional, Tuple

_HARD_ON = {
    "sprawdź w internecie","sprawdz w internecie","sprawdź w necie","sprawdz w necie",
    "sprawdź w sieci","znajdź","znajdz","wyszukaj","googluj","wyszukaj w internecie",
    "szukaj w necie","check the internet","search the web","web search","look up",
    "google it","search online","fetch from web","aktualny","dzisiaj","dziś","today",
    "teraz","na żywo","na zywo","live","breaking","news"
}
_PATTERNS = [
    r"\bwynik\b.*\b(meczu|mecz)\b",
    r"\bkurs\b.*\b(usd|eur|btc|pln|walut|euro|dolar)\b",
    r"\bcena\b.*\b(akcji|bitcoina|ropy|złota|zlota)\b",
    r"\bpogod[aeyi]\b|\bweather\b|\bforecast\b",
    r"\b(Juventus|Real|Barcelona|Legia|Arsenal|F1|NBA|NHL|Ekstraklasa)\b",
    r"\bwczoraj\b|\bdzisiaj\b|\bjutro\b|\bdziś\b",
    r"\b(kiedy|ile|która|ktore|o której|o ktorej)\b",
]
def _contains_trigger(text: str) -> bool:
    t = (text or "").lower()
    if any(kw in t for kw in _HARD_ON):
        return True
    return any(re.search(p, t, flags=re.I) for p in _PATTERNS)

def should_web_search_boost(
    user_text: str,
    frontend_toggle: Optional[bool],
    internet_allowed: Optional[bool],
    intent_wants_web: bool,
) -> Tuple[bool, str]:
    if internet_allowed is False:
        return False, "internet_disallowed"
    if frontend_toggle is True:
        return True, "frontend_true"
    if intent_wants_web:
        return True, "intent_detector"
    if _contains_trigger(user_text):
        return True, "trigger_phrase"
    if frontend_toggle is None:
        return False, "default_off"
    return bool(frontend_toggle), "frontend_value"

async def stream_first_or_fallback(
    llm_messages: list,
    stream_model: Optional[str] = None,
    timeout_s: int = 120,
) -> str:
    """Zbiera strumień z LLM do pełnego tekstu (bez SSE)."""
    from .llm import call_llm_stream_with_fallback  # lazy import
    chunks: list[str] = []
    start = time.time()
    try:
        async for tok in call_llm_stream_with_fallback(
            llm_messages, temperature=0.7, model_override=stream_model
        ):
            chunks.append(tok)
            if time.time() - start > timeout_s:
                chunks.append("\n[timeout]")
                break
    except Exception as e:
        chunks.append(f"\n[stream_error: {e}]")
    return "".join(chunks)
