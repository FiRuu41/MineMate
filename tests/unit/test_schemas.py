from kb.schemas import Chunk, ChunkMetadata, ModSeed


def test_chunk_roundtrip():
    md = ChunkMetadata(
        mod_id="create",
        mod_name_zh="机械动力",
        section="intro",
        mc_version="1.20.1",
        source_url="https://www.mcmod.cn/class/2261.html",
        title="简介",
    )
    c = Chunk(text="hello world", metadata=md)
    assert c.metadata.mod_id == "create"
    d = c.model_dump()
    assert d["metadata"]["section"] == "intro"


def test_mod_seed():
    seed = ModSeed(mod_id="create", name_zh="机械动力", mcmod_url="https://...")
    assert seed.name_en is None
