"""
Redis middleware / cache layer dla Mordzix AI.

Funkcje:
- bezpieczna, opcjonalna integracja z Redisem (jak brak, system działa dalej),
- globalny klient przez get_redis() używany m.in. przez LLM-cache,
- klasa RedisCache z prostymi metodami na cache + stats.

Jak działa:
- próbuje odczytać REDIS_URL z .env (np. redis://localhost:6379/0),
- jak Redis jest offline albo brak biblioteki, zwraca None i loguje WARNING,
- NIC nie wywala backendu, tylko wyłącza cache.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    import redis  # type: ignore
    _HAS_REDIS = True
except Exception:
    redis = None  # type: ignore
    _HAS_REDIS = False

from .helpers import log_info, log_warning, log_error


# ==============================
#  Globalny klient dla LLM / innych
# ==============================

_redis_client: Optional["redis.Redis"] = None
_redis_last_init_ts: float = 0.0
_REDIS_REINIT_INTERVAL = 60.0  # sekundy: co ile można ponawiać init po błędzie


def _build_redis_from_env() -> Optional["redis.Redis"]:
    """Próbuje zbudować klienta Redis na podstawie REDIS_URL z env."""
    if not _HAS_REDIS:
        log_warning("[REDIS] Pakiet 'redis' nie jest zainstalowany – cache wyłączony")
        return None

    redis_url = os.getenv("REDIS_URL", "").strip()
    if not redis_url:
        # fallback na localhost
        redis_url = "redis://localhost:6379/0"

    try:
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=1.0,
        )
        client.ping()
        log_info(f"[REDIS] Połączono z Redis: {redis_url}")
        return client
    except Exception as e:
        log_warning(f"[REDIS] Nie udało się połączyć z Redis ({redis_url}): {e}")
        return None


def get_redis(refresh: bool = False) -> Optional["redis.Redis"]:
    """
    Globalny accessor dla klienta Redis.

    Używany m.in. przez:
    - LLM cache,
    - health checki,
    - inne moduły chcące prostego dostępu do Redis.

    Jak brak / błąd – zwraca None, a system ma działać dalej.
    """
    global _redis_client, _redis_last_init_ts

    # Jak nie ma biblioteki, od razu kończymy
    if not _HAS_REDIS:
        return None

    now = time.time()

    # Wymuszony refresh
    if refresh:
        _redis_client = _build_redis_from_env()
        _redis_last_init_ts = now
        return _redis_client

    # Pierwsze wywołanie
    if _redis_client is None:
        _redis_client = _build_redis_from_env()
        _redis_last_init_ts = now
        return _redis_client

    # Co jakiś czas możemy spróbować odświeżyć połączenie jeśli wcześniej było martwe
    if _redis_client is None and now - _redis_last_init_ts > _REDIS_REINIT_INTERVAL:
        _redis_client = _build_redis_from_env()
        _redis_last_init_ts = now

    return _redis_client


# ==============================
#  Klasa RedisCache – warstwa wyżej
# ==============================

@dataclass
class RedisCache:
    """
    Wyższy wrapper na redis.Redis z:
    - serializacją JSON dla obiektów,
    - prostymi metodami: get/set/delete/incr/decr/expire,
    - pomocą do statystyk cache.

    Może używać:
    - istniejącego klienta (client),
    - albo zbudować własny z host/port/db/password.
    """

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 10
    decode_responses: bool = True
    client: Optional["redis.Redis"] = None

    def __post_init__(self) -> None:
        if not _HAS_REDIS:
            log_warning("[REDIS_CACHE] Pakiet 'redis' nie jest zainstalowany – cache wyłączony")
            self.client = None
            return

        # Jeżeli przekazano istniejącego klienta – użyj go
        if self.client is not None:
            try:
                self.client.ping()
                log_info("[REDIS_CACHE] Używam dostarczonego klienta Redis")
            except Exception as e:
                log_warning(f"[REDIS_CACHE] Dostarczony klient Redis nie odpowiada: {e}")
                self.client = None
            return

        # Inaczej budujemy własny klient
        try:
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=self.decode_responses,
            )
            self.client = redis.Redis(connection_pool=pool)
            self.client.ping()
            log_info(f"[REDIS_CACHE] Połączono z Redis {self.host}:{self.port}/{self.db}")
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Nie udało się zainicjalizować Redis: {e}")
            self.client = None

    # ---------- Serializacja ----------

    def _serialize(self, value: Any) -> str:
        """Serializacja wartości do stringa."""
        try:
            if isinstance(value, (dict, list, tuple)):
                return json.dumps(value, ensure_ascii=False)
            if isinstance(value, (int, float, bool)):
                return json.dumps(value)
            # wszystko inne jako string
            return str(value)
        except Exception as e:
            log_error(f"[REDIS_CACHE] Błąd serializacji wartości: {e}")
            return str(value)

    def _deserialize(self, value: Optional[str]) -> Any:
        """Deserializacja stringa z Redis do obiektu."""
        if value is None:
            return None
        try:
            # próbujemy JSON
            return json.loads(value)
        except Exception:
            # nie JSON, zwracamy surowy string
            return value

    # ---------- Podstawowe operacje ----------

    def get(self, key: str, default: Any = None) -> Any:
        if not self.client:
            return default
        try:
            v = self.client.get(key)
            if v is None:
                return default
            return self._deserialize(v)
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd get('{key}'): {e}")
            return default

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """
        Ustaw wartość w cache.

        ex – czas życia w sekundach (TTL), None = bez TTL.
        """
        if not self.client:
            return False
        try:
            payload = self._serialize(value)
            if ex is not None:
                return bool(self.client.set(key, payload, ex=ex))
            return bool(self.client.set(key, payload))
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd set('{key}'): {e}")
            return False

    def delete(self, *keys: str) -> int:
        if not self.client:
            return 0
        try:
            return int(self.client.delete(*keys))
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd delete{keys}: {e}")
            return 0

    def exists(self, *keys: str) -> int:
        if not self.client:
            return 0
        try:
            return int(self.client.exists(*keys))
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd exists{keys}: {e}")
            return 0

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        if not self.client:
            return None
        try:
            return int(self.client.incr(key, amount))
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd increment('{key}', {amount}): {e}")
            return None

    def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        if not self.client:
            return None
        try:
            return int(self.client.decr(key, amount))
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd decrement('{key}', {amount}): {e}")
            return None

    def expire(self, key: str, seconds: int) -> bool:
        if not self.client:
            return False
        try:
            return bool(self.client.expire(key, seconds))
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd expire('{key}', {seconds}): {e}")
            return False

    # ---------- Statystyki / zdrowie ----------

    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        hits = float(info.get("keyspace_hits", 0))
        misses = float(info.get("keyspace_misses", 0))
        total = hits + misses
        if total <= 0:
            return 0.0
        return hits / total

    def get_stats(self) -> Dict[str, Any]:
        """
        Zwraca podstawowe statystyki Redis:
        - online, version, used_memory_human, connected_clients, hit_rate itp.
        """
        if not self.client:
            return {"online": False, "reason": "no_client"}

        try:
            info = self.client.info()
            return {
                "online": True,
                "redis_version": info.get("redis_version"),
                "used_memory_human": info.get("used_memory_human"),
                "maxmemory_human": info.get("maxmemory_human"),
                "connected_clients": info.get("connected_clients"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
            }
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd pobierania stats: {e}")
            return {"online": False, "reason": str(e)}

    def healthcheck(self) -> bool:
        """Prosty healthcheck – zwraca True jak Redis odpowiada."""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Healthcheck fail: {e}")
            return False

    def flush_db(self) -> bool:
        """Czyści aktualną bazę Redis (UWAGA!)."""
        if not self.client:
            return False
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            log_warning(f"[REDIS_CACHE] Błąd flush_db: {e}")
            return False


# ==============================
#  Pomocnicza funkcja do stworzenia RedisCache z env
# ==============================

def get_redis_cache() -> RedisCache:
    """
    Zwraca RedisCache oparte na globalnym kliencie get_redis().

    Jak Redis nie działa / brak – RedisCache z client=None,
    który grzecznie robi no-op i nic nie wywala.
    """
    client = get_redis()
    return RedisCache(client=client)
