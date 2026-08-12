import time
from dataclasses import dataclass
from typing import Callable

from fastapi import HTTPException, Request, status


@dataclass
class TokenBucket:
    capacity: int
    refill_rate: float
    tokens: float
    last_refill: float


class RateLimiter:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.buckets: dict[str, TokenBucket] = {}

    def _get_bucket(self, key: str) -> TokenBucket:
        now = time.monotonic()

        bucket = self.buckets.get(key)

        if bucket is None:
            bucket = TokenBucket(
                capacity=self.capacity,
                refill_rate=self.refill_rate,
                tokens=float(self.capacity),
                last_refill=now,
            )
            self.buckets[key] = bucket
            return bucket

        elapsed = now - bucket.last_refill

        if elapsed > 0:
            bucket.tokens = min(
                self.capacity,
                bucket.tokens + elapsed * self.refill_rate,
                )
            bucket.last_refill = now

        return bucket

    def check(self, key: str) -> None:
        bucket = self._get_bucket(key)

        if bucket.tokens >= 1:
            bucket.tokens -= 1
            return

        retry_after = max(
            1,
            int((1 - bucket.tokens) / self.refill_rate),
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host

    return "unknown"


def create_rate_limiter(
        capacity: int,
        refill_rate: float,
        key_builder: Callable[[Request], str] = get_client_ip,
):
    limiter = RateLimiter(capacity, refill_rate)

    async def rate_limit_dependency(request: Request):
        key = key_builder(request)
        limiter.check(key)

    return rate_limit_dependency