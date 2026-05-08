from __future__ import annotations

"""HTTP helpers for cwsreviews (requests Session + retries/backoff)."""

import random
import time
from typing import Callable, Optional, Tuple, TypeVar

import dataclasses
import requests


UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)


class RetryableError(RuntimeError):
    pass


T = TypeVar("T")


@dataclasses.dataclass(frozen=True)
class RetryConfig:
    retries: int = 5
    base_delay_s: float = 0.6
    max_delay_s: float = 10.0


def _sleep_backoff(attempt: int, *, base: float, cap: float) -> None:
    # exponential backoff with jitter
    delay = min(cap, base * (2**attempt))
    delay = delay * (0.7 + random.random() * 0.6)
    time.sleep(delay)


def with_retries(fn: Callable[[], T], cfg: RetryConfig) -> T:
    last_exc: Optional[BaseException] = None
    for attempt in range(cfg.retries + 1):
        try:
            return fn()
        except (requests.RequestException, RetryableError) as e:
            last_exc = e
            if attempt >= cfg.retries:
                raise
            _sleep_backoff(attempt, base=cfg.base_delay_s, cap=cfg.max_delay_s)
    assert last_exc is not None
    raise last_exc


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"user-agent": UA})
    return s


def get_text(
    s: requests.Session,
    url: str,
    *,
    timeout_s: int,
    retry_cfg: Optional[RetryConfig] = None,
) -> Tuple[str, str]:
    """
    GET a URL and return (text, final_url_after_redirects).
    Retries on 429/5xx as transient.
    """

    def _do() -> Tuple[str, str]:
        r = s.get(url, timeout=timeout_s, allow_redirects=True)
        if r.status_code == 429 or 500 <= r.status_code <= 599:
            raise RetryableError(f"GET {url} status={r.status_code}")
        r.raise_for_status()
        return r.text, r.url

    return with_retries(_do, retry_cfg or RetryConfig())


def post_form_text(
    s: requests.Session, url: str, *, data: dict, timeout_s: int, retry_cfg: RetryConfig
) -> str:
    """
    POST application/x-www-form-urlencoded and return response text.
    Retries on 429/5xx as transient.
    """

    def _do() -> str:
        r = s.post(url, data=data, timeout=timeout_s)
        if r.status_code == 429 or 500 <= r.status_code <= 599:
            raise RetryableError(f"POST {url} status={r.status_code}")
        r.raise_for_status()
        return r.text

    return with_retries(_do, retry_cfg)
