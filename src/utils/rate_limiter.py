import time
import threading
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Token bucket rate limiter — thread-safe."""
    requests_per_day: int
    min_delay_seconds: float
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _last_request: float = field(default=0.0, init=False, repr=False)
    _requests_today: int = field(default=0, init=False, repr=False)

    def acquire(self) -> None:
        with self._lock:
            if self._requests_today >= self.requests_per_day:
                raise RuntimeError(
                    f"Daily limit of {self.requests_per_day} requests reached"
                )
            elapsed = time.monotonic() - self._last_request
            wait = self.min_delay_seconds - elapsed
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            self._requests_today += 1


# Limitadores pré-configurados por fonte
LIMITERS: dict[str, RateLimiter] = {
    "amadeus":   RateLimiter(requests_per_day=50,  min_delay_seconds=0.5),
    "airlines":  RateLimiter(requests_per_day=25,  min_delay_seconds=5.0),
    "booking":   RateLimiter(requests_per_day=20,  min_delay_seconds=4.0),
    "trivago":   RateLimiter(requests_per_day=10,  min_delay_seconds=5.0),
    "cruises":   RateLimiter(requests_per_day=10,  min_delay_seconds=6.0),
    "packages":  RateLimiter(requests_per_day=10,  min_delay_seconds=6.0),
}
