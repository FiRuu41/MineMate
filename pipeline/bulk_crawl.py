"""Bulk crawl: scan all mcmod class IDs and store mod intros.

Strategy:
- Scan class IDs in [start, end) range
- 3 concurrent workers, ~0.5s delay each -> ~100 mods/min
- Resume from last processed ID (check MySQL)
- Skip if already cached (raw HTML) or already in MySQL with desc
"""
import argparse
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from loguru import logger

from config.logging import new_trace_id, setup_logging
from config.settings import settings
from pipeline.crawlers.mcmod_mod import parse_intro_html
from pipeline.storage.db import SessionLocal
from pipeline.storage.mysql_writer import upsert_mod
from pipeline.storage.raw_cache import RawCache

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
YXD_RE = re.compile(r"yxd_token['\"]?\s*[=:']\s*['\"]?([a-f0-9]+)", re.I)
PROGRESS_FILE = Path("data/bulk_crawl_progress.json")
CHECKPOINT_EVERY = 100


def _fetch(client: httpx.Client, url: str) -> httpx.Response:
    r = client.get(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    # Handle anti-scrape bootstrap
    if "yxd_token" in r.text and len(r.text) < 2000:
        m = YXD_RE.search(r.text)
        if m:
            token = m.group(1)
            r = client.get(url, headers={"User-Agent": UA, "Cookie": f"yxd_token={token}", "Referer": url})
    return r


def _get_name_en(soup) -> str | None:
    h4 = soup.select_one(".class-title h4")
    return h4.get_text(strip=True) if h4 else None


def crawl_one(cid: int, cache: RawCache) -> dict | None:
    """Fetch intro for one class ID. Returns mod data dict or None."""
    url = f"https://www.mcmod.cn/class/{cid}.html"
    mod_id = str(cid)

    if not cache.exists(mod_id, "intro", "page1"):
        try:
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                r = _fetch(client, url)
                r.raise_for_status()
                cache.save(mod_id, "intro", "page1", r.text)
        except Exception:
            return None
        time.sleep(settings.crawl_delay_seconds)

    html = cache.load(mod_id, "intro", "page1")
    if len(html) < 500:
        return None  # bootstrap, filter, or error page

    try:
        info = parse_intro_html(html)
    except Exception:
        return None

    if not info.get("description") or len(info["description"]) < 20:
        return None

    return {
        "mod_id": mod_id,
        "name_zh": info["name_zh"],
        "name_en": info.get("name_en"),
        "mcmod_url": url,
        "loader": info.get("loader"),
        "mc_versions": info.get("mc_versions") or [],
        "author": info.get("author"),
        "description": info["description"],
    }


def save_progress(cid: int) -> None:
    PROGRESS_FILE.write_text(json.dumps({"last_cid": cid, "time": time.time()}), encoding="utf-8")


def load_progress() -> int:
    if PROGRESS_FILE.exists():
        data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return data.get("last_cid", 1)
    return 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=None, help="Start class ID")
    parser.add_argument("--end", type=int, default=30000, help="End class ID (exclusive)")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent workers")
    parser.add_argument("--delay", type=float, default=0.6, help="Delay between requests per worker")
    args = parser.parse_args()

    setup_logging()
    new_trace_id()

    start = args.start if args.start is not None else load_progress()
    end = args.end
    cache = RawCache()

    logger.info("Bulk crawl classes [{}, {}) with {} workers", start, end, args.workers)

    total, stored = 0, 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        batch = list(range(start, end))
        for i in range(0, len(batch), args.workers * 10):
            chunk = batch[i : i + args.workers * 10]
            futures = {pool.submit(crawl_one, cid, cache): cid for cid in chunk}
            for fut in as_completed(futures):
                cid = futures[fut]
                total += 1
                try:
                    data = fut.result()
                except Exception:
                    data = None
                if data:
                    try:
                        with SessionLocal() as session:
                            upsert_mod(session, **data)
                            session.commit()
                        stored += 1
                    except Exception:
                        pass  # dup key etc
                if total % CHECKPOINT_EVERY == 0:
                    save_progress(cid)
                    logger.info("Progress: scanned={}, saved={}, last_cid={}", total, stored, cid)
            if args.delay:
                time.sleep(args.delay * len(chunk) / args.workers)

    save_progress(end)
    logger.info("Done. scanned={}, saved={}", total, stored)


if __name__ == "__main__":
    main()
