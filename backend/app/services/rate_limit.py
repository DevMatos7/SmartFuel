import hashlib
import time

import redis.asyncio as redis

from app.core.config import settings
from app.core.exceptions import AppError


class LoginRateLimiter:
    def __init__(self) -> None:
        self._memory: dict[str, tuple[int, float]] = {}

    def _memory_check(self, key: str) -> None:
        now = time.time()
        count, expires = self._memory.get(key, (0, now + settings.login_rate_window_seconds))
        if now > expires:
            count = 0
            expires = now + settings.login_rate_window_seconds
        count += 1
        self._memory[key] = (count, expires)
        if count > settings.login_rate_limit:
            raise AppError(
                "Muitas tentativas de login. Tente novamente em instantes.",
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
            )

    async def check(self, *, ip_address: str, identifier: str) -> None:
        key = f"login:{ip_address}:{hashlib.sha256(identifier.encode()).hexdigest()}"
        try:
            client = redis.from_url(settings.redis_url, decode_responses=True)
            try:
                count = await client.incr(key)
                if count == 1:
                    await client.expire(key, settings.login_rate_window_seconds)
                if count > settings.login_rate_limit:
                    raise AppError(
                        "Muitas tentativas de login. Tente novamente em instantes.",
                        status_code=429,
                        code="RATE_LIMIT_EXCEEDED",
                    )
            finally:
                await client.aclose()
        except AppError:
            raise
        except Exception as exc:
            if settings.app_env == "production" and not settings.login_rate_allow_memory_fallback:
                raise AppError(
                    "Serviço temporariamente indisponível. Tente novamente.",
                    status_code=503,
                    code="RATE_LIMIT_UNAVAILABLE",
                ) from exc
            self._memory_check(key)


login_rate_limiter = LoginRateLimiter()
