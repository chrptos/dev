"""利用者ごとの簡易な回数制限（RateLimiter の実装）。

インスタンスごとにメモリで数えるだけなので、インスタンスが増えると上限も増える。
利用者が増えたら Memorystore などで共有する仕組みに移す。
"""

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self, per_minute: int, window_seconds: float = 60.0) -> None:
        self._limit = per_minute
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if len(hits) >= self._limit:
            return False
        hits.append(now)
        return True
