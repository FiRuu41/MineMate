"""Async proxy-based bulk crawl. Reuses each IP for 20 requests.

Usage:
  python -m pipeline.proxy_crawl --start 13000 --end 26000
"""
import argparse
import asyncio
import json
import re
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from config.logging import new_trace_id, setup_logging
from pipeline.storage.db import SessionLocal
from pipeline.storage.mysql_writer import upsert_mod

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"
TOKEN_RE = re.compile(r"yxd_token=([a-f0-9]+)")
PROGRESS_FILE = Path("data/proxy_crawl_progress.json")

from config.settings import settings as _cfg
PROXY_API = _cfg.proxy_api_url
PROXY_USER = _cfg.proxy_user
PROXY_PASS = _cfg.proxy_pass

IP_REUSE = 25  # requests per IP before rotating
SEM = asyncio.Semaphore(8)  # concurrent workers, each with own IP

_proxy_ips: list[str] = []
import threading
_proxy_lock = threading.Lock()


def _refill_proxies_sync_legacy():
    """Fetch proxies synchronously (avoids asyncio DNS issues on Windows)."""
    global _proxy_ips
    try:
        import requests
        r = requests.get(PROXY_API, timeout=10)
        ips = r.json().get("data", {}).get("proxy_list", [])
        _proxy_ips.extend(ips)
        logger.debug("Refilled {} IPs", len(ips))
    except Exception as e:
        logger.warning("Proxy API failed: {}", e)


def _refill_proxies():
    """Fetch proxies synchronously (avoids asyncio DNS issues on Windows)."""
    global _proxy_ips
    with _proxy_lock:
        if _proxy_ips:
            return  # already filled
        try:
            import requests
            r = requests.get(PROXY_API, timeout=10)
            ips = r.json().get("data", {}).get("proxy_list", [])
            _proxy_ips.extend(ips)
            logger.debug("Refilled {} IPs", len(ips))
        except Exception as e:
            logger.warning("Proxy API failed: {}", e)


async def _get_session() -> httpx.AsyncClient | None:
    """Create a session with a fresh proxy IP."""
    if not _proxy_ips:
        _refill_proxies()
    if not _proxy_ips:
        return None
    with _proxy_lock:
        ip = _proxy_ips.pop() if _proxy_ips else ""
    proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{ip}"
    return httpx.AsyncClient(proxy=httpx.Proxy(url=proxy_url), timeout=25, follow_redirects=False)


def _parse_intro(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    name_zh = (soup.select_one(".class-title h3") or BeautifulSoup("", "lxml").new_tag("span")).get_text(strip=True)
    name_en_el = soup.select_one(".class-title h4")
    name_en = name_en_el.get_text(strip=True) if name_en_el else None
    mcver_li = soup.select_one(".class-info li.mcver")
    mc_versions = []
    if mcver_li:
        mc_versions = [v.get_text(strip=True) for v in mcver_li.select("ul li") if v.get_text(strip=True)]

    def _info_val(label):
        for li in soup.select(".class-info li"):
            head = li.select_one("div")
            if head and label in head.get_text():
                full = li.get_text(" ", strip=True)
                for sep in (":", "："):
                    idx = full.find(sep)
                    if idx >= 0:
                        return full[idx + 1:].strip()
        return None

    loader = _info_val("运作方式")
    author = _info_val("MOD作者")
    desc = "\n\n".join(p.get_text("\n", strip=True) for p in soup.select(".common-text p") if p.get_text(strip=True))
    # Clean HTML entities and special chars
    import html as _html
    desc = _html.unescape(desc)
    desc = desc.replace("↓", "").replace("\xbb", "").replace("\xa0", " ")
    return {"name_zh": name_zh, "name_en": name_en, "mc_versions": mc_versions,
            "loader": loader, "author": author, "description": desc}


async def _fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r1 = await client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
        m = TOKEN_RE.search(r1.text)
        if m and len(r1.text) < 500:
            client.cookies.set("yxd_token", m.group(1), domain=".mcmod.cn", path="/")
        await client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
        await asyncio.sleep(0.2)
        r3 = await client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
        if len(r3.text) < 500 or "yxd_token" in r3.text:
            await asyncio.sleep(0.2)
            r3 = await client.get(url, headers={"User-Agent": UA, "Referer": "https://www.mcmod.cn/"})
        return r3.text if len(r3.text) > 500 else None
    except Exception:
        return None


async def crawl_one(cid: int) -> dict | None:
    async with SEM:
        # Reuse session across multiple requests
        session = await _get_session()
        if not session:
            return None
        try:
            html = await _fetch(session, f"https://www.mcmod.cn/class/{cid}.html")
            if not html:
                return None
            info = _parse_intro(html)
            desc = info.get("description", "")
            if not desc or len(desc) < 20:
                return None
            return {
                "mod_id": str(cid), "name_zh": info["name_zh"], "name_en": info.get("name_en"),
                "mcmod_url": f"https://www.mcmod.cn/class/{cid}.html",
                "loader": info.get("loader"), "mc_versions": info.get("mc_versions") or [],
                "author": info.get("author"), "description": desc,
            }
        finally:
            await session.aclose()


async def _crawl_batch(ids: list[int]) -> list[dict | None]:
    """Crawl a batch using session reuse within each worker."""
    # For session reuse: one session per worker, processing multiple IDs sequentially
    results = []
    # Get one session and reuse it for IP_REUSE requests
    session = await _get_session()
    if not session:
        return [None] * len(ids)

    count = 0
    for cid in ids:
        if count >= IP_REUSE:
            await session.aclose()
            session = await _get_session()
            if not session:
                results.append(None)
                continue
            count = 0
        try:
            html = await _fetch(session, f"https://www.mcmod.cn/class/{cid}.html")
            if html:
                info = _parse_intro(html)
                desc = info.get("description", "")
                if desc and len(desc) >= 20:
                    results.append({
                        "mod_id": str(cid), "name_zh": info["name_zh"], "name_en": info.get("name_en"),
                        "mcmod_url": f"https://www.mcmod.cn/class/{cid}.html",
                        "loader": info.get("loader"), "mc_versions": info.get("mc_versions") or [],
                        "author": info.get("author"), "description": desc,
                    })
                else:
                    results.append(None)
            else:
                results.append(None)
        except Exception:
            results.append(None)
        count += 1
    await session.aclose()
    return results


async def main_async(start: int, end: int):
    total, stored = 0, 0
    batch_size = 200  # 8 workers * ~25 each
    for batch_start in range(start, end, batch_size):
        ids = list(range(batch_start, min(batch_start + batch_size, end)))
        # Process all chunks concurrently with asyncio.gather
        chunks = [ids[i:i + IP_REUSE] for i in range(0, len(ids), IP_REUSE)]
        tasks = [_crawl_batch(chunk) for chunk in chunks]
        chunk_results_list = await asyncio.gather(*tasks)

        batch_stored = 0
        for chunk_results in chunk_results_list:
            for data in chunk_results:
                total += 1
                if data:
                    try:
                        with SessionLocal() as s:
                            upsert_mod(s, **data)
                            s.commit()
                        stored += 1
                        batch_stored += 1
                    except Exception:
                        pass
        pct = 100 * stored / total if total else 0
        logger.info("[{}-{}] scanned {}, saved {} ({:.1f}%), total: {}",
                    batch_start, batch_start + batch_size, batch_size, batch_stored, pct, stored)
        PROGRESS_FILE.write_text(json.dumps({"last_cid": batch_start + batch_size, "time": time.time()}), encoding="utf-8")
        await asyncio.sleep(0.2)
    logger.info("Done. Scanned {}, saved {}", total, stored)


async def main_async_reverse(start: int, end: int):
    """Crawl from end-1 down to start (newest mods first)."""
    total, stored = 0, 0
    batch_size = 200
    for batch_end in range(end, start, -batch_size):
        batch_start = max(batch_end - batch_size, start)
        ids = list(range(batch_end - 1, batch_start - 1, -1))
        chunks = [ids[i:i + IP_REUSE] for i in range(0, len(ids), IP_REUSE)]
        tasks = [_crawl_batch(chunk) for chunk in chunks]
        chunk_results_list = await asyncio.gather(*tasks)
        batch_stored = 0
        for chunk_results in chunk_results_list:
            for data in chunk_results:
                total += 1
                if data:
                    try:
                        with SessionLocal() as s:
                            upsert_mod(s, **data)
                            s.commit()
                        stored += 1
                        batch_stored += 1
                    except Exception:
                        pass
        pct = 100 * stored / total if total else 0
        logger.info("[{}-{}] scanned {}, saved {} ({:.1f}%), total: {}",
                    batch_start, batch_end, batch_size, batch_stored, pct, stored)
        PROGRESS_FILE.write_text(json.dumps({"last_cid": batch_start, "time": time.time()}), encoding="utf-8")
        await asyncio.sleep(0.2)
    logger.info("Done. Scanned {}, saved {}", total, stored)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=13000)
    parser.add_argument("--end", type=int, default=26000)
    parser.add_argument("--reverse", action="store_true", help="crawl from high to low (newest first)")
    args = parser.parse_args()
    setup_logging()
    new_trace_id()
    if args.reverse:
        # Crawl from end-1 down to start (newest first)
        logger.info("KDL crawl REVERSE [{}, {}), {} reuse/IP", args.end - 1, args.start, IP_REUSE)
        asyncio.run(main_async_reverse(args.start, args.end))
    else:
        logger.info("KDL crawl [{}, {}), {} reuse/IP", args.start, args.end, IP_REUSE)
        asyncio.run(main_async(args.start, args.end))


if __name__ == "__main__":
    main()
