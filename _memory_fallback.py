from typing import Any, Dict, List, Optional
import inspect

def _warn(msg: str) -> None:
    print(msg)

async def call_memory_wrapper(user_id: str,
                              messages: List[Dict[str, Any]],
                              req: Dict[str, Any],
                              default: Optional[str] = None) -> Optional[str]:
    """
    Uniwersalny adapter do 'memory_wrapper':
    - jeżeli istnieje metoda .process_message -> użyj jej
    - jeżeli to funkcja: spróbuj sensownych podpisów (async/sync)
    - w razie błędu/niezgodności -> zwróć 'default'
    """
    mw = globals().get("memory_wrapper")
    if mw is None:
        return default
    try:
        # Klasyczny wariant: obiekt z metodą
        if hasattr(mw, "process_message") and callable(mw.process_message):
            res = mw.process_message(user_id, messages, req)
            if inspect.isawaitable(res):
                res = await res
            return res

        # Wariant: zwykła funkcja z różnymi sygnaturami
        candidates = [
            {"user_id": user_id, "messages": messages, "req": req},
            {"user_id": user_id, "messages": messages},
            {"messages": messages, "req": req},
            {"messages": messages},
            {"req": req},
        ]
        for args in candidates:
            try:
                sig = inspect.signature(mw).parameters
                call_args = {k: v for k, v in args.items() if k in sig}
                res = mw(**call_args)
                if inspect.isawaitable(res):
                    res = await res
                return res
            except TypeError:
                continue

        _warn("[MEM] memory_wrapper callable, ale żaden podpis nie pasuje – zwracam default.")
        return default
    except Exception as e:
        _warn(f"[MEM] błąd w memory_wrapper: {e}")
        return default
