"""Process-local rate limiter.

Phase 1 does not run Redis. Limits reset when the API process restarts and
are not shared across multiple API processes. The deployment note in the
security model says to put a shared limiter in front before horizontal scaling.
"""

import time

from app.core.errors import AppError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = {}

    def reset(self) -> None:
        self._hits.clear()

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        recent = [stamp for stamp in self._hits.get(key, []) if now - stamp < window_seconds]
        if len(recent) >= limit:
            raise AppError(
                429,
                "rate_limited",
                "Too many attempts. Wait and try again.",
            )
        recent.append(now)
        self._hits[key] = recent


class SharedRateLimiter:
    """Atomic PostgreSQL windows survive worker/process replacement.

    Counter writes use a separate, tiny transaction so a rejected login cannot
    roll back its abuse counter or commit unrelated business changes. Production
    fails closed with the normal database-unavailable response on DB failure.
    """

    def __init__(self, engine, pepper: str) -> None:
        self.engine = engine
        self.pepper = pepper

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        from sqlalchemy import text

        from app.core.security import hash_secret

        if limit < 1 or window_seconds < 1:
            raise ValueError("Rate-limit bounds must be positive.")
        digest = hash_secret(key, self.pepper)
        with self.engine.begin() as connection:
            hits = connection.scalar(
                text("""
                INSERT INTO rate_limit_buckets (key_hash,hits,expires_at)
                VALUES (:key,1,statement_timestamp()+make_interval(secs => :window))
                ON CONFLICT (key_hash) DO UPDATE SET
                    hits = CASE WHEN rate_limit_buckets.expires_at <= statement_timestamp()
                        THEN 1 ELSE least(rate_limit_buckets.hits + 1,:ceiling) END,
                    expires_at = CASE WHEN rate_limit_buckets.expires_at <= statement_timestamp()
                        THEN statement_timestamp()+make_interval(secs => :window)
                        ELSE rate_limit_buckets.expires_at END
                RETURNING hits
            """),
                {"key": digest, "window": window_seconds, "ceiling": limit + 1},
            )
            # Bounded housekeeping excludes active windows and skips locked rows.
            connection.execute(
                text("""
                DELETE FROM rate_limit_buckets WHERE key_hash IN (
                    SELECT key_hash FROM rate_limit_buckets
                    WHERE expires_at < statement_timestamp()-interval '1 day'
                    ORDER BY key_hash LIMIT 100 FOR UPDATE SKIP LOCKED
                )
            """)
            )
        if hits > limit:
            raise AppError(429, "rate_limited", "Too many attempts. Wait and try again.")
