"""CLI: crawl mods listed in data/mod_list.json (or a subset)."""
import argparse
import json
from pathlib import Path

from loguru import logger

from config.logging import new_trace_id, setup_logging
from config.settings import settings
from kb.schemas import ModSeed
from pipeline.crawlers.http_client import HttpClient
from pipeline.crawlers.mcmod_mod import fetch_intro
from pipeline.storage.db import SessionLocal
from pipeline.storage.mysql_writer import upsert_mod
from pipeline.storage.raw_cache import RawCache


def load_mod_list(path: str = "data/mod_list.json") -> list[ModSeed]:
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    return [ModSeed(**i) for i in items]


def crawl_one(seed: ModSeed, client: HttpClient, cache: RawCache) -> None:
    intro = fetch_intro(seed.mod_id, seed.mcmod_url, client, cache)
    with SessionLocal() as session:
        upsert_mod(
            session,
            mod_id=seed.mod_id,
            name_zh=intro.name_zh or seed.name_zh,
            name_en=intro.name_en or seed.name_en,
            mcmod_url=intro.source_url,
            loader=intro.loader,
            mc_versions=intro.mc_versions or seed.mc_versions,
            author=intro.author,
            description=intro.description,
        )
        session.commit()
    logger.info("[{}] crawled & upserted", seed.mod_id)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mods", nargs="*", help="mod_id list to crawl (default: all in mod_list.json)")
    parser.add_argument("--mod-list", default="data/mod_list.json")
    args = parser.parse_args()

    setup_logging()
    new_trace_id()

    seeds = load_mod_list(args.mod_list)
    if args.mods:
        seeds = [s for s in seeds if s.mod_id in args.mods]
    logger.info("crawling {} mods", len(seeds))

    client = HttpClient(delay_seconds=settings.crawl_delay_seconds)
    cache = RawCache()
    try:
        for seed in seeds:
            try:
                crawl_one(seed, client, cache)
            except Exception as e:
                logger.error("[{}] failed: {}", seed.mod_id, e)
    finally:
        client.close()


if __name__ == "__main__":
    main()
