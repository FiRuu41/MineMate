"""Async proxy-based bulk crawl. 5 concurrent requests via proxy pool.

Usage:
  python -m pipeline.proxy_crawl --start 4500 --end 15000
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
PROXY_URL = "http://t17900430677647:974tonyg@k773.kdltps.com:15818"
TOKEN_RE = re.compile(r"yxd_token=([a-f0-9]+)")
PROGRESS_FILE = Path("data/proxy_crawl_progress.json")
SEM = asyncio.Semaphore(5)  # 5 concurrent


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
    return {"name_zh": name_zh, "name_en": name_en, "mc_versions": mc_versions,
            "loader": loader, "author": author, "description": desc}


async def _fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        r1 = await client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
        m = TOKEN_RE.search(r1.text)
        if m and len(r1.text) < 500:
            client.cookies.set("yxd_token", m.group(1), domain=".mcmod.cn", path="/")
        await client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
        await asyncio.sleep(0.3)
        r3 = await client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN"})
        if len(r3.text) < 500 or "yxd_token" in r3.text:
            await asyncio.sleep(0.3)
            r3 = await client.get(url, headers={"User-Agent": UA, "Referer": "https://www.mcmod.cn/"})
        return r3.text if len(r3.text) > 500 else None
    except Exception:
        return None


async def crawl_one(cid: int) -> dict | None:
    async with SEM:
        proxy = httpx.Proxy(url=PROXY_URL)
        async with httpx.AsyncClient(proxy=proxy, timeout=25, follow_redirects=False) as client:
            html = await _fetch(client, f"https://www.mcmod.cn/class/{cid}.html")
            if not html:
                return None
            try:
                info = _parse_intro(html)
            except Exception:
                return None
            desc = info.get("description", "")
            if not desc or len(desc) < 20:
                return None
            return {
                "mod_id": str(cid), "name_zh": info["name_zh"], "name_en": info.get("name_en"),
                "mcmod_url": f"https://www.mcmod.cn/class/{cid}.html",
                "loader": info.get("loader"), "mc_versions": info.get("mc_versions") or [],
                "author": info.get("author"), "description": desc,
            }


async def main_async(start: int, end: int):
    total, stored = 0, 0
    batch_size = 100
    for batch_start in range(start, end, batch_size):
        ids = list(range(batch_start, min(batch_start + batch_size, end)))
        tasks = [crawl_one(cid) for cid in ids]
        results = await asyncio.gather(*tasks)
        batch_stored = 0
        for data in results:
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
        PROGRESS_FILE.write_text(json.dumps({"last_cid": batch_start + batch_size, "time": time.time()}), encoding="utf-8")
        pct = 100 * stored / total if total else 0
        logger.info("[{}-{}] {} scanned, {} saved ({:.1f}%), total stored: {}",
                    batch_start, batch_start + batch_size, batch_size, batch_stored, pct, stored)
        await asyncio.sleep(0.5)
    logger.info("Done. Scanned {}, saved {}", total, stored)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=4500)
    parser.add_argument("--end", type=int, default=15000)
    args = parser.parse_args()
    setup_logging()
    new_trace_id()
    logger.info("Async proxy crawl [{}, {}) with 5 concurrency", args.start, args.end)
    asyncio.run(main_async(args.start, args.end))


if __name__ == "__main__":
    main()
