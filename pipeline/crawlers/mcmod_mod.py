from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag
from loguru import logger

from pipeline.crawlers.http_client import HttpClient
from pipeline.storage.raw_cache import RawCache


@dataclass
class IntroData:
    name_zh: str
    name_en: str | None
    mc_versions: list[str]
    loader: str | None
    author: str | None
    description: str
    raw_html: str
    source_url: str


def parse_intro_html(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    name_zh_el = soup.select_one(".class-title h3")
    name_zh = name_zh_el.get_text(strip=True) if name_zh_el else ""
    name_en_el = soup.select_one(".class-title h4")
    name_en = name_en_el.get_text(strip=True) if name_en_el else None

    mc_versions: list[str] = []
    mcver_li = soup.select_one(".class-info li.mcver")
    if mcver_li:
        for v in mcver_li.select("ul li"):
            t = v.get_text(strip=True)
            if t:
                mc_versions.append(t)

    loader = _info_value(soup, "运作方式")
    author = _info_value(soup, "MOD作者")

    desc_parts = [p.get_text("\n", strip=True) for p in soup.select(".common-text p")]
    description = "\n\n".join(p for p in desc_parts if p)

    return {
        "name_zh": name_zh,
        "name_en": name_en,
        "mc_versions": mc_versions,
        "loader": loader,
        "author": author,
        "description": description,
    }


def _info_value(soup: BeautifulSoup, label: str) -> str | None:
    for li in soup.select(".class-info li"):
        head = li.select_one("div")
        if head and label in head.get_text():
            full = li.get_text(" ", strip=True)
            idx = full.find(":")
            if idx == -1:
                idx = full.find("：")
            return full[idx + 1:].strip() if idx >= 0 else None
    return None


def fetch_intro(mod_id: str, url: str, client: HttpClient, cache: RawCache) -> IntroData:
    if cache.exists(mod_id, "intro", "page1"):
        logger.info("[{}] intro cache hit", mod_id)
        html = cache.load(mod_id, "intro", "page1")
    else:
        logger.info("[{}] fetching intro {}", mod_id, url)
        html = client.get(url)
        cache.save(mod_id, "intro", "page1", html)
    parsed = parse_intro_html(html)
    return IntroData(**parsed, raw_html=html, source_url=url)
