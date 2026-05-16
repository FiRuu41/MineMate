from pipeline.storage.raw_cache import RawCache


def test_save_and_load(tmp_path):
    cache = RawCache(root=tmp_path)
    cache.save("create", "intro", "page1", "<html>hi</html>")
    assert cache.exists("create", "intro", "page1")
    assert cache.load("create", "intro", "page1") == "<html>hi</html>"


def test_not_exists(tmp_path):
    cache = RawCache(root=tmp_path)
    assert not cache.exists("create", "intro", "missing")
