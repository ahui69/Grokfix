#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assistant_endpoint.py - Chat endpoint with Cognitive Engine (PHASE 6 - Full Security)

Features:
- Session ownership validation
- Rate limiting
- Attachments support
- Streaming with timeout
"""
from .response_adapter import adapt
from fastapi import APIRouter, Request, HTTPException, Depends
from .memory_store import save_message
from .autoroute import decide
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, json, asyncio, hashlib
from dataclasses import dataclass, asdict

# --- MAIN IMPORT: THE NEW COGNITIVE ENGINE ---
from core.cognitive_engine import cognitive_engine
from core.helpers import log_warning, log_info
from core.security import security_manager, get_client_ip

# Imports for memory saving (UnifiedMemorySystem)
try:
    from core.memory import get_memory_system
    memory_system = get_memory_system()
except ImportError:
    memory_system = None

# --- Pydantic Models ---
class Message(BaseModel):
    role: str
    content: str
    attachments: Optional[List[Dict[str, Any]]] = []

class ChatRequest(BaseModel):
    messages: List[Message]
    user_id: Optional[str] = "default"
    session_id: Optional[str] = None
    model: Optional[str] = None  # Model override from frontend
    use_memory: bool = True
    use_research: bool = True
    internet_allowed: Optional[bool] = True
    web_search: Optional[bool] = True  # Explicit web search toggle from frontend
    auto_learn: Optional[bool] = True
    use_batch_processing: Optional[bool] = True
    # Attachments to include with the message
    attachments: Optional[List[Dict[str, Any]]] = []

class ChatResponse(BaseModel):
    ok: bool
    answer: str
    sources: Optional[List[Dict]] = []
    metadata: Dict[str, Any] = {}

router = APIRouter(prefix="/api/chat")

# Auth configuration
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "__CHANGE_ME_AUTH_TOKEN__")

# Rate limits
RATE_LIMIT_CHAT = 60          # 60 chat requests per hour
RATE_LIMIT_CHAT_STREAM = 60   # 60 stream requests per hour

# Message validation constants
MAX_MESSAGE_LENGTH = 50000    # ~12k tokens max per message
MAX_MESSAGES_COUNT = 100      # Max messages in single request


def _get_user_id(req: Request) -> str:
    """Extract user ID from request (from token hash)"""
    auth_header = req.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    
    if token:
        return hashlib.sha256(token.encode()).hexdigest()[:16]
    
    return "default"


def _auth_with_rate_limit(req: Request, limit: int = RATE_LIMIT_CHAT):
    """Auth dependency with rate limiting"""
    client_ip = get_client_ip(req)
    endpoint = req.url.path
    
    # Check rate limit
    if not security_manager.check_rate_limit(client_ip, endpoint, limit):
        log_warning(f"[CHAT] Rate limit exceeded for {client_ip} on {endpoint}")
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please try again later."
        )
    
    # Check auth
    auth_header = req.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip() if auth_header.startswith("Bearer ") else ""
    
    if token != AUTH_TOKEN:
        security_manager.record_failed_attempt(client_ip)
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return _get_user_id(req)


def _validate_session_ownership(session_id: str, user_id: str):
    """Validate that user owns the session"""
    from .sessions import verify_session_ownership
    
    if session_id and not verify_session_ownership(session_id, user_id):
        raise HTTPException(
            status_code=403, 
            detail="Access denied: you don't own this session"
        )


async def _execute_auto_tool(endpoint: str, params: Dict[str, Any], user_message: str) -> Optional[str]:
    """
    Automatycznie wykonuje tool call na podstawie wykrytej intencji.
    Zwraca sformatowany wynik do wstrzyknięcia do kontekstu AI.
    """
    import httpx
    
    try:
        # Uzupełnij brakujące parametry domyślnymi dla różnych endpointów
        if endpoint.startswith('/api/fashion'):
            params.setdefault('brand', '')
            params.setdefault('item_type', '')
            params.setdefault('condition', 'bardzo dobry')
            params.setdefault('platform', 'vinted')
            params.setdefault('details', user_message)
            
        elif endpoint.startswith('/api/auction'):
            params.setdefault('title', user_message[:100])
            params.setdefault('description', user_message)
            params.setdefault('category', 'moda')
            
        elif endpoint.startswith('/api/travel'):
            params.setdefault('destination', '')
            params.setdefault('origin', 'Warszawa')
            
        elif endpoint.startswith('/api/hacker'):
            params.setdefault('target', '')
            params.setdefault('ports', 'common')
            
        elif endpoint.startswith('/api/legal'):
            params.setdefault('content', user_message)
            params.setdefault('document_type', 'pismo')
            
        elif endpoint.startswith('/api/negocjator'):
            params.setdefault('opis', user_message)
            params.setdefault('kwota', 0)
            
        elif endpoint.startswith('/api/programista'):
            params.setdefault('code', '')
            params.setdefault('language', 'python')
            params.setdefault('prompt', user_message)
            
        elif endpoint.startswith('/api/writing'):
            params.setdefault('topic', user_message)
            params.setdefault('tone', 'professional')
            
        elif endpoint.startswith('/api/nlp'):
            params.setdefault('text', user_message)
            
        elif endpoint.startswith('/api/memory'):
            params.setdefault('content', user_message)
            params.setdefault('query', user_message)
            
        elif endpoint.startswith('/api/media'):
            params.setdefault('prompt', user_message)
            
        elif endpoint.startswith('/api/research'):
            params.setdefault('query', user_message)
        
        # Walidacja - jeśli brakuje kluczowych parametrów, niech AI sobie poradzi naturalnie
        # Nie blokujemy - AI dopyta w odpowiedzi
        
        # Wykonaj request do lokalnego API
        async with httpx.AsyncClient(timeout=30.0) as client:
            base_url = "http://127.0.0.1:8080"
            response = await client.post(
                f"{base_url}{endpoint}",
                json=params,
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                return _format_tool_result(endpoint, data, user_message)
            elif response.status_code == 404:
                log_warning(f"[AUTO_TOOL] Endpoint not found: {endpoint}")
                return None
            else:
                log_warning(f"[AUTO_TOOL] API returned {response.status_code}: {response.text[:200]}")
                return None
                
    except Exception as e:
        log_warning(f"[AUTO_TOOL] Error executing {endpoint}: {e}")
        return None


def _format_tool_result(endpoint: str, data: Dict[str, Any], user_message: str = "") -> str:
    """Formatuje wynik tool call do czytelnej formy"""
    
    # ============ FASHION ============
    if '/fashion/description' in endpoint and data.get('success'):
        return f"""📝 WYGENEROWANY OPIS AUKCJI:

**Tytuł:** {data.get('title', 'Brak')}

**Opis:**
{data.get('description', 'Brak')}

**Tagi:** {', '.join(data.get('tags', []))}
**Hashtagi:** {' '.join(data.get('hashtags', []))}"""

    elif '/fashion/price' in endpoint and data.get('success'):
        price = data.get('estimated_price', 0)
        range_data = data.get('price_range', {})
        return f"""💰 WYCENA PRZEDMIOTU:

**Szacowana cena:** {price} PLN
**Zakres:** {range_data.get('min', 0)} - {range_data.get('max', 0)} PLN

**Czynniki wpływające:**
{chr(10).join('• ' + str(f) for f in data.get('factors', []))}"""

    elif '/fashion/outfit' in endpoint and data.get('success'):
        outfit = data.get('outfit', {})
        items = outfit.get('suggested_items', [])
        return f"""👔 PROPOZYCJA STYLIZACJI:

**Okazja:** {outfit.get('occasion', 'Ogólna')}
**Styl:** {outfit.get('style', 'Casual')}

**Elementy:**
{chr(10).join('• ' + str(item) for item in items)}

**Paleta kolorów:** {', '.join(outfit.get('color_palette', []))}
**Tip:** {outfit.get('weather_tip', '')}"""

    # ============ AUCTION ============
    elif '/auction/analyze' in endpoint and data.get('success'):
        return f"""📊 ANALIZA AUKCJI:

**Ocena:** {data.get('grade', '?')} ({data.get('overall_score', 0)}/100 pkt)

**Tytuł:** {data.get('title_analysis', {}).get('score', 0)}/25 pkt
**Opis:** {data.get('description_analysis', {}).get('score', 0)}/35 pkt

**Sugestie:**
{chr(10).join('• ' + str(s) for s in data.get('title_analysis', {}).get('suggestions', [])[:5])}"""

    # ============ TRAVEL ============
    elif '/travel' in endpoint:
        results = data.get('results', [data]) if data.get('results') else [data]
        if results:
            r = results[0]
            return f"""✈️ PROPOZYCJA PODRÓŻY:

**Destynacja:** {r.get('destination', r.get('name', 'Nieznana'))}
**Cena:** {r.get('price', r.get('estimated_price', 'N/A'))} PLN
**Czas trwania:** {r.get('duration', '7 dni')}

{r.get('description', '')}"""

    # ============ HACKER ============
    elif '/hacker/portscan' in endpoint and data.get('success'):
        ports = data.get('open_ports', [])
        port_list = '\n'.join(f"  • Port {p.get('port')}: {p.get('service', '?')}" for p in ports[:10])
        return f"""🔍 WYNIK SKANOWANIA PORTÓW:

**Target:** {data.get('target', '?')}
**Czas skanowania:** {data.get('scan_time', '?')}s

**Otwarte porty:**
{port_list if ports else '  Brak otwartych portów'}"""

    elif '/hacker/recon' in endpoint and data.get('success'):
        return f"""🕵️ REKONESANS:

**Target:** {data.get('target', '?')}
**DNS:** {data.get('dns', {})}
**WHOIS:** {str(data.get('whois', {}))[:300]}
**Tech Stack:** {', '.join(data.get('tech_stack', []))}"""

    elif '/hacker/headers' in endpoint and data.get('success'):
        return f"""🛡️ ANALIZA NAGŁÓWKÓW:

**URL:** {data.get('url', '?')}
**Score:** {data.get('score', 0)}/100

**Nagłówki:**
{chr(10).join(f"  • {k}: {'✓' if v.get('present') else '✗'}" for k, v in data.get('headers', {}).items())}"""

    # ============ LEGAL ============
    elif '/legal/generate' in endpoint and data.get('success'):
        return f"""⚖️ WYGENEROWANE PISMO:

{data.get('response', data.get('content', 'Brak treści'))}"""

    elif '/legal/analyze' in endpoint and data.get('success'):
        return f"""📋 ANALIZA PISMA:

**Typ:** {data.get('document_type', '?')}
**Nadawca:** {data.get('sender', '?')}
**Termin:** {data.get('deadline', 'Brak')}

**Podsumowanie:**
{data.get('summary', data.get('analysis', 'Brak analizy'))}"""

    elif '/legal/deadline' in endpoint:
        return f"""⏰ OBLICZONY TERMIN:

**Termin:** {data.get('deadline', data.get('date', '?'))}
**Dni do terminu:** {data.get('days_left', '?')}"""

    # ============ NEGOCJATOR ============
    elif '/negocjator/przedawnienie' in endpoint:
        return f"""📅 ANALIZA PRZEDAWNIENIA:

**Status:** {data.get('status', '?')}
**Data przedawnienia:** {data.get('data_przedawnienia', '?')}
**Czy przedawniony:** {'TAK ✓' if data.get('przedawniony') else 'NIE ✗'}

{data.get('opis', '')}"""

    elif '/negocjator/ugody' in endpoint:
        return f"""🤝 PROPOZYCJA UGODY:

{data.get('propozycja', data.get('content', 'Brak propozycji'))}"""

    elif '/negocjator/szanse' in endpoint:
        return f"""⚖️ OCENA SZANS:

**Szanse na wygraną:** {data.get('szanse', '?')}%
**Rekomendacja:** {data.get('rekomendacja', '?')}

{data.get('uzasadnienie', '')}"""

    # ============ PROGRAMISTA ============
    elif '/programista/execute' in endpoint:
        return f"""💻 WYNIK WYKONANIA:

```
{data.get('output', data.get('result', data.get('stdout', 'Brak wyniku')))}
```
{'**Błąd:** ' + str(data.get('error', data.get('stderr', ''))) if data.get('error') or data.get('stderr') else ''}"""

    elif '/programista/analyze' in endpoint or '/programista/explain' in endpoint:
        return f"""🔍 ANALIZA KODU:

{data.get('analysis', data.get('explanation', data.get('result', 'Brak analizy')))}"""

    elif '/programista/debug' in endpoint:
        return f"""🐛 DEBUGOWANIE:

**Problem:** {data.get('issue', data.get('problem', '?'))}
**Rozwiązanie:** {data.get('solution', data.get('fix', '?'))}

**Poprawiony kod:**
```
{data.get('fixed_code', '')}
```"""

    elif '/programista/generate' in endpoint:
        return f"""💻 WYGENEROWANY KOD:

```{data.get('language', '')}
{data.get('code', data.get('result', 'Brak kodu'))}
```"""

    # ============ WRITING ============
    elif '/writing' in endpoint:
        return f"""✍️ WYGENEROWANY TEKST:

{data.get('content', data.get('text', data.get('result', 'Brak tekstu')))}"""

    # ============ NLP ============
    elif '/nlp/sentiment' in endpoint:
        return f"""😊 ANALIZA SENTYMENTU:

**Wynik:** {data.get('sentiment', '?')}
**Score:** {data.get('score', '?')}
**Emocje:** {', '.join(data.get('emotions', []))}"""

    elif '/nlp/summarize' in endpoint:
        return f"""📝 STRESZCZENIE:

{data.get('summary', data.get('result', 'Brak streszczenia'))}"""

    elif '/lang/translate' in endpoint:
        return f"""🌍 TŁUMACZENIE:

{data.get('translation', data.get('result', data.get('text', 'Brak tłumaczenia')))}"""

    # ============ MEMORY ============
    elif '/memory/add' in endpoint:
        return f"""💾 ZAPISANO DO PAMIĘCI:

{data.get('message', 'Zapisano pomyślnie')}"""

    elif '/memory/search' in endpoint:
        results = data.get('results', [])
        if results:
            return f"""🧠 ZNALEZIONE WSPOMNIENIA:

{chr(10).join('• ' + str(r.get('content', r))[:200] for r in results[:5])}"""
        return "Nie znaleziono pasujących wspomnień."

    # ============ MEDIA ============
    elif '/media/generate' in endpoint and data.get('success'):
        return f"""🎨 WYGENEROWANO OBRAZ:

**URL:** {data.get('url', data.get('image_url', '?'))}
**Prompt:** {data.get('prompt', user_message)[:100]}"""

    # ============ VISION ============
    elif '/vision/analyze' in endpoint:
        return f"""👁️ ANALIZA OBRAZU:

{data.get('description', data.get('analysis', data.get('result', 'Brak opisu')))}"""

    # ============ RESEARCH ============
    elif '/research/search' in endpoint:
        results = data.get('results', [])
        if results:
            return f"""🔍 WYNIKI WYSZUKIWANIA:

{chr(10).join(f"• **{r.get('title', '?')}**: {r.get('snippet', '')[:150]}" for r in results[:5])}"""
        return "Brak wyników wyszukiwania."

    # ============ ML ============
    elif '/ml/predict' in endpoint:
        return f"""📈 PREDYKCJA:

**Wynik:** {data.get('prediction', data.get('result', '?'))}
**Pewność:** {data.get('confidence', '?')}%"""

    # ============ PSYCHE ============
    elif '/psyche/analyze' in endpoint:
        return f"""🧠 ANALIZA PSYCHOLOGICZNA:

{data.get('analysis', data.get('result', 'Brak analizy'))}"""

    # ============ TTS ============
    elif '/tts/speak' in endpoint:
        return f"""🔊 AUDIO WYGENEROWANE:

**URL:** {data.get('audio_url', data.get('url', '?'))}"""

    # ============ FALLBACK ============
    # Jeśli jest sukces ale nieznany format
    if data.get('success') or data.get('ok'):
        # Próbuj wyciągnąć główną treść
        for key in ['result', 'content', 'data', 'response', 'output', 'text']:
            if data.get(key):
                return f"✅ **Wynik:**\n\n{str(data[key])[:1500]}"
    
    # Ostateczny fallback - surowe JSON
    return json.dumps(data, indent=2, ensure_ascii=False)[:1000]


# --- MAIN CHAT ENDPOINT ---
@router.post("/assistant", response_model=ChatResponse)
async def chat_assistant(body: ChatRequest, req: Request):
    from .config import MEMORY_ENABLED
    from .memory import memory_add_conversation
    from .sessions import add_conversation_pair
    
    # Auth with rate limiting
    user_id = _auth_with_rate_limit(req, RATE_LIMIT_CHAT)
    
    # Validate message count and length
    if len(body.messages) > MAX_MESSAGES_COUNT:
        raise HTTPException(400, f"Too many messages (max {MAX_MESSAGES_COUNT})")
    
    for msg in body.messages:
        if len(msg.content) > MAX_MESSAGE_LENGTH:
            raise HTTPException(413, f"Message too long (max {MAX_MESSAGE_LENGTH} chars)")
    
    session_id = body.session_id
    
    # Validate session ownership
    _validate_session_ownership(session_id, user_id)

    # --- Memory: save last user message ---
    try:
        last_user_msg = ""
        for m in reversed(body.messages):
            if m.role == "user" and (m.content or "").strip():
                last_user_msg = m.content.strip()
                break
        if last_user_msg:
            save_message(user_id, "user", last_user_msg, tags=["chat"])
    except Exception:
        pass

    # Get attachments from request
    attachments = body.attachments or []
    
    # Extract last user message
    plain_last_user = next((m.content for m in reversed(body.messages) if m.role == "user"), "")
    
    # Delegate to cognitive engine
    result = await cognitive_engine.process_message(user_id, [m.dict() for m in body.messages], req)

    # Save to UNIFIED MEMORY
    if MEMORY_ENABLED and plain_last_user and result.get("answer"):
        try:
            memory_add_conversation(
                user_id=user_id,
                user_msg=plain_last_user,
                assistant_msg=result["answer"],
                intent=result.get("metadata", {}).get("intent", "chat")
            )
            log_info(f"[MEMORY] Conversation saved for user {user_id}")
        except Exception as e:
            log_warning(f"[WARN] Error during unified memory save: {e}")
    
    # Save to session (with attachments)
    if session_id and plain_last_user and result.get("answer"):
        try:
            add_conversation_pair(
                session_id, 
                plain_last_user, 
                result["answer"],
                user_attachments=attachments,
                user_id=user_id
            )
            log_info(f"[SESSION] Conversation pair saved to session {session_id}")
        except PermissionError as e:
            log_warning(f"[SESSION] Permission denied: {e}")
        except Exception as e:
            log_warning(f"[SESSION] Failed to save conversation pair: {e}")

    return ChatResponse(
        ok=True,
        answer=result.get("answer", "Error processing response."),
        sources=result.get("sources", []),
        metadata={**result.get("metadata", {}), "session_id": session_id}
    )


# --- STREAMING ENDPOINT ---
@router.post("/assistant/stream")
async def chat_assistant_stream(body: ChatRequest, req: Request):
    """
    TRUE streaming endpoint - streams tokens directly from LLM as they arrive.
    
    SSE Format:
    - data: {"type": "start"}
    - data: {"type": "chunk", "content": "token"}
    - data: {"type": "complete", "answer": "full text", "metadata": {...}}
    - data: {"type": "error", "message": "error description"}
    """
    from .config import MEMORY_ENABLED, MORDZIX_SYSTEM_PROMPT
    from .memory import memory_add_conversation
    from .llm import call_llm_stream_with_fallback
    from .sessions import add_conversation_pair
    from .intent_detector import detect_intent, get_mode_prompt_addon
    
    # Auth with rate limiting
    user_id = _auth_with_rate_limit(req, RATE_LIMIT_CHAT_STREAM)
    
    # Validate message count and length
    if len(body.messages) > MAX_MESSAGES_COUNT:
        raise HTTPException(400, f"Too many messages (max {MAX_MESSAGES_COUNT})")
    
    for msg in body.messages:
        if len(msg.content) > MAX_MESSAGE_LENGTH:
            raise HTTPException(413, f"Message too long (max {MAX_MESSAGE_LENGTH} chars)")
    
    session_id = body.session_id
    
    # Validate session ownership
    _validate_session_ownership(session_id, user_id)
    
    # Get attachments
    attachments = body.attachments or []
    
    # Extract last user message
    plain_last_user = next((m.content for m in reversed(body.messages) if m.role == "user"), "")
    
    # ====== LOAD ATTACHMENT CONTENTS ======
    attachment_context = ""
    if attachments:
        try:
            import os
            from pathlib import Path
            
            # Ścieżka do uploads zgodna z files_endpoint.py
            workspace = Path(os.getenv("WORKSPACE", "."))
            uploads_dir = workspace / "uploads"
            
            for att in attachments:
                file_id = att.get("id", "")  # np. "default/20251205/abc123.txt"
                file_name = att.get("name", att.get("filename", "plik"))
                file_url = att.get("url", "")
                
                # Zbuduj ścieżkę do pliku
                if file_id:
                    file_path = uploads_dir / file_id
                elif file_url and file_url.startswith("/api/files/"):
                    # Extract path from URL: /api/files/tenant/day/name -> tenant/day/name
                    rel_path = file_url.replace("/api/files/", "")
                    file_path = uploads_dir / rel_path
                else:
                    file_path = None
                
                log_info(f"[STREAM] Processing attachment: {file_name}, path: {file_path}")
                
                # Try to read file content
                if file_path and file_path.exists():
                    try:
                        ext = file_path.suffix.lower()
                        text_extensions = ['.txt', '.md', '.json', '.csv', '.xml', '.html', '.py', '.js', '.ts', '.css', '.log', '.yaml', '.yml', '.ini', '.cfg', '.conf']
                        
                        if ext in text_extensions:
                            content = file_path.read_text(encoding='utf-8', errors='ignore')[:15000]
                            attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]:\n```\n{content}\n```\n"
                            log_info(f"[STREAM] Loaded text attachment: {file_name} ({len(content)} chars)")
                        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
                            attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: [OBRAZ] Użytkownik przesłał obraz. Jeśli masz możliwość analizy obrazów, opisz co widzisz.\n"
                            log_info(f"[STREAM] Image attachment: {file_name}")
                        elif ext == '.pdf':
                            # Try to extract text from PDF
                            try:
                                import fitz  # PyMuPDF
                                doc = fitz.open(str(file_path))
                                pdf_text = ""
                                for page in doc[:10]:  # Max 10 pages
                                    pdf_text += page.get_text()[:3000]
                                doc.close()
                                if pdf_text.strip():
                                    attachment_context += f"\n\n📎 ZAŁĄCZNIK PDF [{file_name}]:\n```\n{pdf_text[:10000]}\n```\n"
                                    log_info(f"[STREAM] Extracted PDF text: {file_name} ({len(pdf_text)} chars)")
                                else:
                                    attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: [PDF] Plik PDF bez możliwości odczytu tekstu.\n"
                            except ImportError:
                                attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: [PDF] Przesłano dokument PDF.\n"
                            except Exception as pdf_err:
                                log_warning(f"[STREAM] PDF read error: {pdf_err}")
                                attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: [PDF] Przesłano dokument PDF.\n"
                        else:
                            attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: [PLIK {ext.upper()}] Przesłano plik typu {ext}.\n"
                            log_info(f"[STREAM] Binary attachment: {file_name}")
                    except Exception as e:
                        log_warning(f"[STREAM] Failed to read attachment {file_name}: {e}")
                        attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: (nie udało się odczytać zawartości)\n"
                else:
                    # File path not found - use metadata only
                    mime = att.get("mime", "")
                    kind = att.get("kind", "file")
                    if "image" in mime or kind == "image":
                        attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: [OBRAZ] Użytkownik przesłał obraz.\n"
                    elif "pdf" in mime:
                        attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: [PDF] Przesłano dokument PDF.\n"
                    else:
                        attachment_context += f"\n\n📎 ZAŁĄCZNIK [{file_name}]: Użytkownik przesłał plik.\n"
                    log_info(f"[STREAM] Attachment file not found, using metadata: {file_name}")
                    
        except Exception as e:
            log_warning(f"[STREAM] Attachment processing error: {e}")
    
    async def generate():
        full_answer = ""
        error_occurred = False
        web_context = ""
        
        try:
            # Send start event
            yield f"data: {json.dumps({'type': 'start'})}\n\n"
            
            # Build messages for LLM with dynamic persona
            intent_result = detect_intent(plain_last_user)
            mode_addon = get_mode_prompt_addon(intent_result.mode)
            
            # Check if web search should be performed (frontend toggle OR intent detection)
            should_web_search = (body.web_search and body.internet_allowed) or intent_result.needs_web_search
            log_info(f"[STREAM] Mode: {intent_result.mode}, Web search: frontend={body.web_search}, intent={intent_result.needs_web_search}, final={should_web_search}")
            
            # ====== AUTO TOOL CALL - WYKONAJ AUTOMATYCZNIE NARZĘDZIA ======
            tool_result_context = ""
            if intent_result.tool_call:
                log_info(f"[STREAM] Auto tool call detected: {intent_result.tool_call}")
                try:
                    tool_result = await _execute_auto_tool(intent_result.tool_call, intent_result.tool_params or {}, plain_last_user)
                    if tool_result:
                        tool_result_context = f"\n\n🔧 WYNIK NARZĘDZIA ({intent_result.tool_description}):\n{tool_result}\n\n⚡ Wykorzystaj powyższe dane w odpowiedzi dla użytkownika, sformatuj je ładnie."
                        log_info(f"[STREAM] Tool executed successfully: {intent_result.tool_call}")
                except Exception as e:
                    log_warning(f"[STREAM] Auto tool call failed: {e}")
            
            # ====== WEB SEARCH - REAL TIME DATA ======
            if should_web_search:
                try:
                    from .research_policy import smart_web_search
                    log_info(f"[STREAM] Executing web search for: {plain_last_user[:100]}...")
                    
                    # Dodaj datę do query dla aktualnych wyników
                    from datetime import datetime
                    current_date = datetime.now().strftime("%Y")
                    enhanced_query = f"{plain_last_user} {current_date}"
                    
                    search_results = await smart_web_search(enhanced_query, max_results=8)
                    
                    if search_results:
                        web_snippets = []
                        today = datetime.now().strftime("%d.%m.%Y")
                        for r in search_results[:8]:
                            title = r.get("title", "")
                            snippet = r.get("snippet", "")[:400]
                            url = r.get("url", "")
                            web_snippets.append(f"• {title}: {snippet} (źródło: {url})")
                        
                        web_context = f"\n\n🔍 AKTUALNE INFORMACJE Z INTERNETU (DZISIEJSZA DATA: {today}):\n" + "\n".join(web_snippets) + "\n\n⚠️ KRYTYCZNE: Powyższe dane są AKTUALNE z internetu. MUSISZ używać TYLKO tych danych! NIE WOLNO CI wymyślać dat, wyników ani faktów. Jeśli dane są nieaktualne lub sprzeczne, POWIEDZ że nie masz pewnych informacji. Twoja wiedza treniniowa jest STARA - ufaj TYLKO wynikom wyszukiwania!"
                        log_info(f"[STREAM] Web search returned {len(search_results)} results")
                    else:
                        web_context = "\n\n⚠️ Nie znaleziono aktualnych wyników w internecie. Poinformuj użytkownika, że nie masz dostępu do aktualnych danych."
                        log_info("[STREAM] Web search returned no results")
                        
                except Exception as e:
                    log_warning(f"[STREAM] Web search failed: {e}")
                    web_context = "\n\n⚠️ Wyszukiwanie w internecie nie powiodło się. Poinformuj użytkownika o braku aktualnych danych."
            
            # BUILD SYSTEM PROMPT WITH WEB SEARCH DATA
            system_content = MORDZIX_SYSTEM_PROMPT + "\n\n" + mode_addon + tool_result_context + attachment_context
            
            # INJECT WEB SEARCH DIRECTLY INTO SYSTEM PROMPT - model MUST use it
            if web_context and should_web_search:
                system_content += f"\n\n=== AKTUALNE DANE Z INTERNETU (UŻYJ ICH!) ===\n{web_context}\n=== KONIEC DANYCH Z INTERNETU ===\n\nUŻYWAJ POWYŻSZYCH DANYCH jako źródła prawdy. NIE mów że nie masz dostępu do internetu!"
            
            llm_messages = [{"role": "system", "content": system_content}]
            
            # Add ALL messages including last one
            for m in body.messages:
                llm_messages.append({"role": m.role, "content": m.content})
            
            # Stream with timeout tracking
            import time as time_module
            start_time = time_module.time()
            STREAM_TIMEOUT = 120  # 2 minutes
            
            # Stream tokens from LLM (use model from frontend if provided)
            stream_model = body.model if body.model else None
            async for chunk in call_llm_stream_with_fallback(llm_messages, temperature=0.7, model_override=stream_model):
                # Check timeout
                if time_module.time() - start_time > STREAM_TIMEOUT:
                    error_occurred = True
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Stream timeout after 120s'})}\n\n"
                    log_warning(f"[STREAM] Timeout for user {user_id}")
                    break
                
                if chunk.startswith("[ERROR]"):
                    error_occurred = True
                    yield f"data: {json.dumps({'type': 'error', 'message': chunk})}\n\n"
                    break
                
                full_answer += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # Send complete event
            if not error_occurred:
                yield f"data: {json.dumps({'type': 'complete', 'answer': full_answer, 'metadata': {'streaming': True, 'user_id': user_id, 'session_id': session_id}})}\n\n"
            
            # Save to UNIFIED MEMORY
            if MEMORY_ENABLED and plain_last_user and full_answer and not error_occurred:
                try:
                    memory_add_conversation(
                        user_id=user_id,
                        user_msg=plain_last_user,
                        assistant_msg=full_answer,
                        intent="chat"
                    )
                    log_info(f"[MEMORY] Stream conversation saved for user {user_id}")
                except Exception as e:
                    log_warning(f"[WARN] Error during unified memory save: {e}")
            
            # Save to session (with attachments)
            if session_id and plain_last_user and full_answer and not error_occurred:
                try:
                    add_conversation_pair(
                        session_id, 
                        plain_last_user, 
                        full_answer,
                        user_attachments=attachments,
                        user_id=user_id
                    )
                    log_info(f"[SESSION] Conversation pair saved to session {session_id}")
                except PermissionError as e:
                    log_warning(f"[SESSION] Permission denied: {e}")
                except Exception as e:
                    log_warning(f"[SESSION] Failed to save conversation pair: {e}")
                    
        except Exception as e:
            log_warning(f"[STREAM] Error in stream generation: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# --- AUTO-LEARN ENDPOINT ---
class AutoLearnRequest(BaseModel):
    query: str
    user_id: Optional[str] = "default"
    force_learn: bool = True

@router.post("/auto", response_model=ChatResponse)
async def force_auto_learn(body: AutoLearnRequest, req: Request):
    from core.research import autonauka
    
    # Auth with rate limiting (lower limit for expensive operation)
    user_id = _auth_with_rate_limit(req, limit=20)
    
    try:
        result = await autonauka(body.query, topk=8, deep_research=body.force_learn, user_id=user_id)
        
        context = result.get("context", "")
        facts = result.get("facts", [])
        sources = result.get("sources", [])
        
        answer = f"Wykonałem autonaukę dla zapytania: '{body.query}'\n\n"
        
        if facts:
            answer += "📚 Najważniejsze fakty:\n\n"
            for i, fact in enumerate(facts[:5], 1):
                answer += f"{i}. {fact}\n\n"
        
        if sources:
            answer += "📑 Źródła:\n\n"
            for i, source in enumerate(sources[:5], 1):
                title = source.get("title") or "Źródło"
                url = source.get("url") or "#"
                answer += f"{i}. {title} - {url}\n"
        
        answer += f"\nZnaleziono {result.get('source_count', 0)} źródeł. Wiedza została zapisana w pamięci długoterminowej."
        
        return ChatResponse(
            ok=True,
            answer=answer,
            sources=sources[:5],
            metadata={
                "auto_learned": True,
                "source_count": result.get("source_count", 0),
                "facts_count": len(facts),
                "query": body.query,
                "deep_research": body.force_learn,
                "powered_by": result.get("powered_by", "unknown"),
                "hierarchical_memory": result.get("hierarchical_memory", {}),
                "hierarchical_confidence": result.get("hierarchical_confidence", 0)
            }
        )
    except Exception as e:
        log_warning(f"[WARN] Error during force auto-learn: {e}")
        return ChatResponse(
            ok=False,
            answer=f"Błąd podczas autonauki: {str(e)}",
            metadata={"error": str(e)}
        )
