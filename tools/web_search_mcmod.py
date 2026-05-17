"""Fallback real-time mcmod search when local KB misses."""
import re

import httpx
from loguru import logger

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"

YXD_RE = re.compile(r"yxd_token['\"]?\s*[=:']\s*['\"]?([a-f0-9]+)", re.I)


def web_search_mcmod(query: str, top_k: int = 5) -> list[dict]:
    try:
        with httpx.Client(timeout=20, follow_redirects=True) as client:
            r = client.get(
                f"https://search.mcmod.cn/s?key={query}",
                headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
            )
            # Bootstrap
            if "yxd_token" in r.text and len(r.text) < 2000:
                m = YXD_RE.search(r.text)
                if m:
                    token = m.group(1)
                    r = client.get(
                        f"https://search.mcmod.cn/s?key={query}",
                        headers={"User-Agent": UA, "Cookie": f"yxd_token={token}", "Referer": r.url},
                    )
            # Extract class links from search results
            results = []
            seen = set()
            for m in re.finditer(r'/class/(\d+)\.html', r.text):
                cid = m.group(1)
                if cid not in seen:
                    seen.add(cid)
                    results.append({
                        "class_id": cid,
                        "url": f"https://www.mcmod.cn/class/{cid}.html",
                        "snippet": f"mcmod class {cid}",
                    })
            return results[:top_k]
    except Exception as e:
        logger.exception("web_search_mcmod failed")
        return [{"error": str(e)}]
