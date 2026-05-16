import random
import re
import time

import httpx
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15",
]

# mcmod.cn anti-scrape: first response is a JS snippet that sets a cookie and
# reloads the page. Detect, parse the token, inject the cookie, then retry once.
YXD_TOKEN_RE = re.compile(r"yxd_token\s*=\s*['\"]?([a-fA-F0-9]+)")


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

    def _maybe_handle_mcmod_bootstrap(self, url: str, text: str) -> str | None:
        """If response is the mcmod anti-scrape bootstrap, inject cookie and refetch.

        Returns refetched body on bootstrap path; None otherwise.
        """
        if "yxd_token" not in text or len(text) > 2000:
            return None
        m = YXD_TOKEN_RE.search(text)
        if not m:
            return None
        token = m.group(1)
        logger.info("mcmod bootstrap detected, injected yxd_token, refetching {}", url)
        self._sleep()
        headers = {**self._headers(), "Cookie": f"yxd_token={token}", "Referer": url}
        r = self._client.get(url, headers=headers)
        r.raise_for_status()
        return r.text

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
            real = self._maybe_handle_mcmod_bootstrap(url, r.text)
            return real if real is not None else r.text

        return _do()

    def close(self) -> None:
        self._client.close()
