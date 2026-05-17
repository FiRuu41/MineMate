"""Real-time mcmod search + page fetch via proxy pool.

When local KB misses, this tool searches mcmod.cn, fetches the top result page,
and extracts the mod introduction for the LLM to use.
"""
import re
import time

import httpx
from bs4 import BeautifulSoup
from loguru import logger

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"
PROXY_URL = "http://d2645551915:vby8n2ny@k773.kdltps.com:15818"
TOKEN_RE = re.compile(r"yxd_token['\"]?\s*[=:']\s*['\"]?([a-f0-9]+)", re.I)


def _fetch(url: str) -> str | None:
    """Fetch with cookie bypass via proxy."""
    with httpx.Client(proxy=httpx.Proxy(url=PROXY_URL), timeout=25, follow_redirects=False) as c:
        try:
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
        except Exception as e:
            logger.warning("fetch failed for {}: {}", url, e)
            return None


def _parse_intro(html: str) -> str:
    """Extract intro description from a mod class page."""
    soup = BeautifulSoup(html, "lxml")
    name_zh = (soup.select_one(".class-title h3") or BeautifulSoup("", "lxml").new_tag("span")).get_text(strip=True)
    desc_parts = [p.get_text("\n", strip=True) for p in soup.select(".common-text p") if p.get_text(strip=True)]
    description = "\n\n".join(desc_parts)
    return f"模组：{name_zh}\n{description[:3000]}"


def web_search_mcmod(query: str, top_k: int = 3, fetch_pages: bool = True) -> list[dict]:
    """Search mcmod.cn and optionally fetch top result pages.

    Returns list of dicts with url, title, snippet, and page_content (if fetched).
    """
    try:
        # Step 1: search
        search_url = f"https://search.mcmod.cn/s?key={query}"
        html = _fetch(search_url)
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

        # Step 2: fetch top result pages for detailed content
        if fetch_pages and results:
            logger.info("web_search fetching {} pages", min(2, len(results)))
            for r in results[:2]:
                page_html = _fetch(r["url"])
                if page_html:
                    r["page_content"] = _parse_intro(page_html)
                time.sleep(0.5)

        return results[:top_k]
    except Exception as e:
        logger.exception("web_search_mcmod failed")
        return [{"error": str(e)}]
