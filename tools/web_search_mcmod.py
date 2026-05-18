"""Real-time mcmod search + page fetch via Playwright (Chromium) with proxy rotation.

Why this design:
- mcmod.cn 用 yxd_token JS 跳转挑战做反爬，纯 HTTP 客户端（httpx/requests）无法绕过
- 部分 IP（如本机长期跑爬虫的）会被 mcmod 永久封禁
- 解法：Playwright 启动真实 Chromium 自动执行 JS + 每次取新代理 IP

Required .env config:
    PROXY_API_URL=<KDL or similar HTTP proxy pool API>
    PROXY_USER=<auth user>
    PROXY_PASS=<auth pass>
    PLAYWRIGHT_BROWSERS_PATH=D:/playwright-browsers   # 浏览器装哪（避免 C 盘）

Pre-flight:
    uv run playwright install chromium
"""
import os
import re
import time

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from config.settings import settings

# Set browser path BEFORE importing playwright
if settings.playwright_browsers_path:
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = settings.playwright_browsers_path

from playwright.sync_api import sync_playwright  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0"


def _get_proxy_ip() -> str | None:
    """Fetch one proxy IP from configured API. Returns None if not configured or failed."""
    if not settings.proxy_api_url:
        return None
    try:
        with httpx.Client(timeout=10) as c:
            ip = c.get(settings.proxy_api_url).text.strip()
        return ip if ":" in ip else None
    except Exception as e:
        logger.warning("proxy api fetch failed: {}", e)
        return None


def fetch_page(url: str) -> str | None:
    """Fetch a mcmod page via Playwright + rotating proxy IP.

    Returns None on any failure:
    - PROXY_API_URL not configured
    - proxy API call failed
    - proxy IP itself in mcmod banned list
    - Playwright launch / navigation failed
    - response too short (anti-bot challenge not bypassed)
    """
    ip = _get_proxy_ip()
    if not ip:
        logger.warning("no proxy IP available; mcmod web fallback unavailable")
        return None

    proxy_cfg = {
        "server": f"http://{ip}",
        "username": settings.proxy_user,
        "password": settings.proxy_pass,
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, proxy=proxy_cfg)
            try:
                context = browser.new_context(user_agent=UA, locale="zh-CN")
                page = context.new_page()
                page.goto(url, timeout=25000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)  # 等 yxd_token JS 跳转完成
                html = page.content()
                if "你已被系统封禁" in html or "已触发防火墙" in html:
                    logger.info("proxy ip {} is in mcmod banned list", ip)
                    return None
                return html if len(html) > 5000 else None
            finally:
                browser.close()
    except Exception as e:
        logger.warning("playwright fetch failed: {}", e)
        return None


def parse_page_intro(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.select_one(".class-title h3") or BeautifulSoup("", "lxml").new_tag("span")
    name_zh = title_el.get_text(strip=True)
    desc_parts = [
        p.get_text("\n", strip=True)
        for p in soup.select(".common-text p")
        if p.get_text(strip=True)
    ]
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
