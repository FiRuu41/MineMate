"""Real-time mcmod search + page fetch.

Direct connection by default. Set PROXY_API_URL / PROXY_USER / PROXY_PASS
in .env to enable proxy pool fallback when direct is blocked.
"""
import random
import re
import time

import httpx
import requests
from bs4 import BeautifulSoup
from loguru import logger

from config.settings import settings

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"
TOKEN_RE = re.compile(r"yxd_token['\"]?\s*[=:']\s*['\"]?([a-f0-9]+)", re.I)
_proxy_ips: list[str] = []


def _get_proxy() -> str | None:
    """Get one proxy IP from API, or None if not configured."""
    global _proxy_ips
    if not settings.proxy_api_url:
        return None
    if not _proxy_ips:
        try:
            r = requests.get(settings.proxy_api_url, timeout=10)
            _proxy_ips = r.json().get("data", {}).get("proxy_list", [])
            logger.debug("Fetched {} proxies", len(_proxy_ips))
        except Exception as e:
            logger.warning("Proxy API failed: {}", e)
            return None
    return _proxy_ips.pop() if _proxy_ips else None


def _try_fetch(url: str) -> str | None:
    """Direct HTTP fetch."""
    try:
        with httpx.Client(timeout=20, follow_redirects=False) as c:
            r1 = c.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
            m = TOKEN_RE.search(r1.text)
            if m and len(r1.text) < 500:
                c.cookies.set("yxd_token", m.group(1), domain=".mcmod.cn", path="/")
            c.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
            time.sleep(0.3)
            r3 = c.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
            if len(r3.text) < 500 or "yxd_token" in r3.text:
                time.sleep(0.3)
                r3 = c.get(url, headers={"User-Agent": UA, "Referer": "https://www.mcmod.cn/"})
            return r3.text if len(r3.text) > 500 else None
    except Exception:
        return None


def _try_fetch_proxy(url: str, ip: str) -> str | None:
    """Fetch via proxy IP."""
    proxy_url = f"http://{settings.proxy_user}:{settings.proxy_pass}@{ip}"
    try:
        with httpx.Client(proxy=proxy_url, timeout=25, follow_redirects=False) as c:
            r1 = c.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
            m = TOKEN_RE.search(r1.text)
            if m and len(r1.text) < 500:
                c.cookies.set("yxd_token", m.group(1), domain=".mcmod.cn", path="/")
            c.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
            time.sleep(0.3)
            r3 = c.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
            if len(r3.text) < 500 or "yxd_token" in r3.text:
                time.sleep(0.3)
                r3 = c.get(url, headers={"User-Agent": UA, "Referer": "https://www.mcmod.cn/"})
            return r3.text if len(r3.text) > 500 else None
    except Exception:
        return None


def fetch_page(url: str) -> str | None:
    """Fetch a page — direct first, proxy fallback."""
    # Try direct
    html = _try_fetch(url)
    if html:
        return html
    # Try proxy
    ip = _get_proxy()
    if ip:
        logger.info("Direct failed, trying proxy {}", ip)
        return _try_fetch_proxy(url, ip)
    return None


def parse_page_intro(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    name_zh = (soup.select_one(".class-title h3") or BeautifulSoup("", "lxml").new_tag("span")).get_text(strip=True)
    desc_parts = [p.get_text("\n", strip=True) for p in soup.select(".common-text p") if p.get_text(strip=True)]
    return f"模组：{name_zh}\n{''.join(desc_parts)[:3000]}"


def web_search_mcmod(query: str, top_k: int = 2, fetch_pages: bool = True) -> list[dict]:
    try:
        search_url = f"https://search.mcmod.cn/s?key={query}"
        html = fetch_page(search_url)
        if not html:
            return [{"error": "search failed"}]

        results = []
        seen = set()
        for m in re.finditer(r'/class/(\d+)\.html', html):
            cid = m.group(1)
            if cid in seen:
                continue
            seen.add(cid)
            url = f"https://www.mcmod.cn/class/{cid}.html"
            results.append({"class_id": cid, "url": url, "snippet": f"mcmod class {cid}"})
            if len(results) >= top_k:
                break

        if fetch_pages and results:
            logger.info("Fetching {} result pages", min(2, len(results)))
            for r in results[:2]:
                page_html = fetch_page(r["url"])
                if page_html:
                    r["page_content"] = parse_page_intro(page_html)
                time.sleep(0.5)

        return results[:top_k]
    except Exception as e:
        logger.exception("web_search_mcmod failed")
        return [{"error": str(e)}]
