"""Test web_search_mcmod's Playwright + proxy plumbing (mocked, no network)."""
from unittest.mock import MagicMock, patch

from tools.web_search_mcmod import _get_proxy_ip, fetch_page


def test_get_proxy_ip_returns_none_when_unconfigured(monkeypatch):
    """无 PROXY_API_URL 时 _get_proxy_ip 返回 None（不抛异常）。"""
    from config.settings import settings as s
    monkeypatch.setattr(s, "proxy_api_url", "")
    assert _get_proxy_ip() is None


def test_fetch_page_returns_none_when_no_proxy(monkeypatch):
    """无代理 IP 可用时 fetch_page 返回 None，不尝试启动 Playwright。"""
    monkeypatch.setattr("tools.web_search_mcmod._get_proxy_ip", lambda: None)
    assert fetch_page("https://www.mcmod.cn/class/341.html") is None


def test_fetch_page_returns_none_on_banned_page(monkeypatch):
    """代理 IP 也在 mcmod 黑名单时返回 None，不返回封禁页 HTML。"""
    monkeypatch.setattr("tools.web_search_mcmod._get_proxy_ip", lambda: "1.2.3.4:5678")

    fake_browser = MagicMock()
    fake_page = MagicMock()
    fake_page.content.return_value = '<html><body><h3>1.2.3.4 你已被系统封禁</h3></body></html>'
    fake_browser.new_context.return_value.new_page.return_value = fake_page

    fake_pw = MagicMock()
    fake_pw.__enter__.return_value.chromium.launch.return_value = fake_browser

    with patch("tools.web_search_mcmod.sync_playwright", return_value=fake_pw):
        assert fetch_page("https://www.mcmod.cn/class/341.html") is None


def test_fetch_page_returns_html_on_success(monkeypatch):
    """成功路径：长 HTML 且无封禁标志 → 返回内容。"""
    monkeypatch.setattr("tools.web_search_mcmod._get_proxy_ip", lambda: "1.2.3.4:5678")

    real_page_html = '<html><body>' + ('<p>模组介绍</p>' * 500) + '</body></html>'
    fake_browser = MagicMock()
    fake_page = MagicMock()
    fake_page.content.return_value = real_page_html
    fake_browser.new_context.return_value.new_page.return_value = fake_page

    fake_pw = MagicMock()
    fake_pw.__enter__.return_value.chromium.launch.return_value = fake_browser

    with patch("tools.web_search_mcmod.sync_playwright", return_value=fake_pw):
        out = fetch_page("https://www.mcmod.cn/class/341.html")
        assert out is not None
        assert "模组介绍" in out
