from llama_index.core.node_parser import SentenceSplitter

from kb.schemas import Chunk, ChunkMetadata


def intro_to_chunks(text: str, metadata: ChunkMetadata, chunk_size: int = 512, chunk_overlap: int = 64) -> list[Chunk]:
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    pieces = splitter.split_text(text)
    return [Chunk(text=p, metadata=metadata) for p in pieces if p.strip()]
