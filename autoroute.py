
import re
from dataclasses import dataclass
from typing import Literal

Tool = Literal["chat","research"]

# Polish + generic time-sensitive/news/score/price triggers
_TIME_WORDS = [
    r"dzisiaj", r"dziś", r"wczoraj", r"jutro", r"teraz", r"obecnie", r"na żywo",
    r"aktualn\w*", r"ostatni\w*", r"najnowsz\w*", r"bieżąc\w*",
    r"wynik\w*", r"mecz\w*", r"tabela", r"liga", r"skład", r"transfer",
    r"kurs", r"cena", r"ile kosztuje", r"notowan\w*", r"walut\w*",
    r"premier\w*", r"release", r"harmonogram", r"rozkład", r"grafik",
    r"news", r"wiadomości", r"sprawdź", r"sprawdz", r"zweryfikuj", r"wyszukaj", r"w internecie"
]

_TIME_RE = re.compile("|".join(_TIME_WORDS), re.IGNORECASE)

@dataclass
class AutoRouteDecision:
    tool: Tool
    reason: str

def decide(text: str) -> AutoRouteDecision:
    # Very conservative heuristic: route to research on time-sensitive intents.
    t = (text or "").strip()
    if not t:
        return AutoRouteDecision(tool="chat", reason="empty")
    if _TIME_RE.search(t):
        return AutoRouteDecision(tool="research", reason="time_sensitive")
    # default to chat (writer/creative/coding prompts without /code)
    return AutoRouteDecision(tool="chat", reason="default")
