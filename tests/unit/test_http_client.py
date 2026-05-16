import httpx
import respx

from pipeline.crawlers.http_client import HttpClient


@respx.mock
def test_get_success():
    respx.get("https://www.mcmod.cn/test").mock(return_value=httpx.Response(200, text="<html>ok</html>"))
    c = HttpClient(delay_seconds=0)
    assert c.get("https://www.mcmod.cn/test") == "<html>ok</html>"


@respx.mock
def test_get_retries_then_succeeds():
    route = respx.get("https://www.mcmod.cn/flaky")
    route.side_effect = [httpx.Response(500), httpx.Response(200, text="ok")]
    c = HttpClient(delay_seconds=0, max_retries=3)
    assert c.get("https://www.mcmod.cn/flaky") == "ok"


@respx.mock
def test_get_gives_up():
    respx.get("https://www.mcmod.cn/dead").mock(return_value=httpx.Response(500))
    c = HttpClient(delay_seconds=0, max_retries=2)
    try:
        c.get("https://www.mcmod.cn/dead")
        raise AssertionError("should have raised")
    except httpx.HTTPStatusError:
        pass
