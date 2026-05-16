from kb.schemas import ChunkMetadata
from pipeline.structure import intro_to_chunks


def test_intro_to_chunks_one_per_paragraph_block():
    md = ChunkMetadata(
        mod_id="create",
        mod_name_zh="机械动力",
        section="intro",
        mc_version="1.20.1",
        source_url="https://...",
        title="简介",
    )
    text = "段落一。" + ("。".join(["这是机械动力模组"] * 80))
    chunks = intro_to_chunks(text, md, chunk_size=200, chunk_overlap=40)
    assert len(chunks) >= 2
    assert all(c.metadata.section == "intro" for c in chunks)
    assert all(c.text for c in chunks)
