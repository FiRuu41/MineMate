import random
import time

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15",
]


class HttpClient:
    def __init__(self, delay_seconds: float = 1.5, max_retries: int = 3, timeout: float = 20.0) -> None:
        self.delay_seconds = delay_seconds
        self.max_retries = max(1, max_retries)
        self._client = httpx.Client(timeout=timeout, follow_redirects=True)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": random.choice(UAS), "Accept-Language": "zh-CN,zh;q=0.9"}

    def _sleep(self) -> None:
        if self.delay_seconds > 0:
            time.sleep(self.delay_seconds + random.random() * 0.5)

    def get(self, url: str) -> str:
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(min=1, max=10),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
        )
        def _do() -> str:
            self._sleep()
            r = self._client.get(url, headers=self._headers())
            r.raise_for_status()
            logger.debug("GET {} -> {}", url, r.status_code)
            return r.text

        return _do()

    def close(self) -> None:
        self._client.close()
