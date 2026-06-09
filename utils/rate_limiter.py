"""Rate limiter — asyncio token-bucket for per-tool request throttling."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TokenBucket:
    """
    Async token-bucket rate limiter.

    Args:
        rate:  tokens added per second
        burst: maximum tokens that can accumulate (bucket capacity)
    """

    rate: float          # tokens / second
    burst: float         # max tokens
    _tokens: float = field(init=False)
    _last: float = field(init=False)
    _lock: asyncio.Lock = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = self.burst
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, n: float = 1.0) -> None:
        """Block until *n* tokens are available, then consume them."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
                self._last = now

                if self._tokens >= n:
                    self._tokens -= n
                    return

                wait = (n - self._tokens) / self.rate
                await asyncio.sleep(wait)


class RateLimiter:
    """
    Central rate-limiter registry.

    Usage::

        rl = RateLimiter(global_rps=10)
        rl.add_tool("arjun", rps=2, burst=2)

        async with rl.tool("subfinder"):
            ...
    """

    def __init__(self, global_rps: float = 10, global_burst: Optional[float] = None) -> None:
        burst = global_burst or global_rps * 2
        self._global = TokenBucket(rate=global_rps, burst=burst)
        self._tools: Dict[str, TokenBucket] = {}

    def add_tool(self, name: str, rps: float, burst: Optional[float] = None) -> None:
        """Register a per-tool bucket."""
        self._tools[name] = TokenBucket(rate=rps, burst=burst or rps * 2)

    async def acquire(self, tool: str | None = None) -> None:
        """Acquire from global bucket (and per-tool bucket if registered)."""
        await self._global.acquire()
        if tool and tool in self._tools:
            await self._tools[tool].acquire()
