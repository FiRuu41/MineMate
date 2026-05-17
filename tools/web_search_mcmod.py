"""Real-time mcmod search + page fetch.

Tries direct connection first. Falls back to proxy pool if configured.
Most users don't need a proxy.
"""
import re
import time

import httpx
from bs4 import BeautifulSoup
from loguru import logger

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"
TOKEN_RE = re.compile(r"yxd_token['\"]?\s*[=:']\s*['\"]?([a-f0-9]+)", re.I)

# KDL private proxy API (optional — only used if direct fails)
PROXY_API = ("https://dps.kdlapi.com/api/getdps/"
             "?secret_id=oaoslyfdfto82bsa6ks0"
             "&signature=wjjgi4ikqjol7fwwglml7y76ttpvq0v8"
             "&num=3&format=json&sep=1")
PROXY_USER = "d2645551915"
PROXY_PASS = "vby8n2ny"
_proxy_ips: list[str] = []


def _get_proxy() -> str | None:
    global _proxy_ips
    if not _proxy_ips:
        try:
            import requests as req
            r = req.get(PROXY_API, timeout=10)
            _proxy_ips = r.json().get("data", {}).get("proxy_list", [])
            logger.debug("Fetched {} proxy IPs", len(_proxy_ips))
        except Exception as e:
            logger.warning("Proxy API failed: {}", e)
            return None
    return _proxy_ips.pop() if _proxy_ips else None


def _tryfetch_page(url: str, proxy: str | None = None) -> str | None:
    """One attempt to fetch URL, with or without proxy."""
    try:
        client_kwargs = {"timeout": 25, "follow_redirects": False}
        if proxy:
            client_kwargs["proxy"] = proxy
        with httpx.Client(**client_kwargs) as c:
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
            if len(r3.text) < 500:
                return None
            return r3.text
    except Exception as e:
        logger.debug("fetch failed (proxy={}): {}", bool(proxy), e)
        return None


def fetch_page(url: str) -> str | None:
    """Fetch URL, trying direct first, then proxy."""
    # Try direct
    html = _tryfetch_page(url, proxy=None)
    if html:
        return html
    # Try proxy
    ip = _get_proxy()
    if ip:
        proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{ip}"
        logger.info("Direct failed, trying proxy {}", ip)
        return _tryfetch_page(url, proxy=proxy_url)
    return None


def parse_page_intro(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    name = (soup.select_one(".class-title h3") or soup.new_tag("span")).get_text(strip=True)
    desc = "\n".join(p.get_text("\n", strip=True) for p in soup.select(".common-text p") if p.get_text(strip=True))
    return f"模组：{name}\n{desc[:3000]}"


def web_search_mcmod(query: str, top_k: int = 2, fetch_pages: bool = True) -> list[dict]:
    try:
        html = fetch_page(f"https://search.mcmod.cn/s?key={query}")
        if not html:
            return [{"error": "search failed - network error or banned"}]

        results = []
        seen = set()
        for m in re.finditer(r'/class/(\d+)\.html', html):
            cid = m.group(1)
            if cid in seen:
                continue
            seen.add(cid)
            results.append({"class_id": cid, "url": f"https://www.mcmod.cn/class/{cid}.html",
                           "snippet": f"mcmod class {cid}"})
            if len(results) >= top_k:
                break

        if fetch_pages and results:
            for r in results[:2]:
                page_html = fetch_page(r["url"])
                if page_html:
                    r["page_content"] = parse_page_intro(page_html)
                time.sleep(0.5)

        return results[:top_k]
    except Exception as e:
        logger.exception("web_search_mcmod failed")
        return [{"error": str(e)}]
