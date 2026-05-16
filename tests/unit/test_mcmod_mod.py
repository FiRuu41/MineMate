from pathlib import Path

from pipeline.crawlers.mcmod_mod import parse_intro_html

FIXTURE = Path(__file__).parent.parent / "fixtures" / "sample_mcmod_html" / "create_intro.html"


def test_parse_intro_html():
    html = FIXTURE.read_text(encoding="utf-8")
    info = parse_intro_html(html)
    assert info["name_zh"] == "机械动力"
    assert info["name_en"] == "Create"
    assert "1.20.1" in info["mc_versions"]
    assert info["loader"] == "Forge / Fabric"
    assert info["author"] == "simibubi"
    assert "机械动力是一个" in info["description"]
