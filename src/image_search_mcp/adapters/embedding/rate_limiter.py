"""Adaptive cross-thread rate limiter for embedding API calls.

Designed for APIs with RPM + concurrency limits (e.g. Jina free: 100 RPM,
2 concurrent).  A single instance should be shared across all embedding
clients that use the same API key.
"""

from __future__ import annotations

import asyncio
import logging
import random
import threading
import time

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """Serialises API requests across threads and event loops.

    Parameters
    ----------
    rpm:
        Steady-state requests-per-minute budget.
    max_concurrency:
        Hard cap on simultaneous in-flight requests.
    """

    def __init__(self, rpm: int = 100, max_concurrency: int = 2) -> None:
        self._base_interval = 60.0 / rpm
        self._min_interval = self._base_interval
        self._max_concurrency = max_concurrency

        self._lock = threading.Lock()
        self._concurrency_sem = threading.Semaphore(max_concurrency)
        self._rate_limit_until: float = 0.0
        self._last_slot_at: float = 0.0

    # -- public API -----------------------------------------------------------

    def acquire_slot(self) -> float:
        """Reserve the next time-slot.  Returns seconds to wait."""
        with self._lock:
            now = time.monotonic()
            earliest = max(
                self._rate_limit_until,
                self._last_slot_at + self._min_interval,
            )
            wait = max(0.0, earliest - now) + random.uniform(0, 0.1)
            self._last_slot_at = now + wait
            return wait

    async def acquire_concurrency(self) -> None:
        """Wait until a concurrency slot is free (non-blocking for the loop)."""
        await asyncio.to_thread(self._concurrency_sem.acquire)

    def release_concurrency(self) -> None:
        self._concurrency_sem.release()

    def on_success(self) -> None:
        """Ease interval back toward the base after a successful call."""
        with self._lock:
            self._min_interval = max(
                self._min_interval * 0.9, self._base_interval
            )

    def on_rate_limited(self, backoff: float) -> None:
        """Widen interval and set a cooldown after a 429."""
        with self._lock:
            self._rate_limit_until = max(
                self._rate_limit_until,
                time.monotonic() + backoff,
            )
            self._min_interval = min(self._min_interval * 2.0, 30.0)
            logger.info(
                "Rate limiter tightened: min_interval=%.1fs, cooldown=%.1fs",
                self._min_interval,
                backoff,
            )

    # -- convenience properties -----------------------------------------------

    @property
    def rpm(self) -> float:
        return 60.0 / self._min_interval

    @property
    def max_concurrency(self) -> int:
        return self._max_concurrency
