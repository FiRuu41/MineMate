from pathlib import Path


class RawCache:
    def __init__(self, root: Path | str = "data/raw") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, mod_id: str, page_type: str, page_id: str) -> Path:
        d = self.root / mod_id / page_type
        d.mkdir(parents=True, exist_ok=True)
        safe_id = page_id.replace("/", "_").replace("?", "_")
        return d / f"{safe_id}.html"

    def save(self, mod_id: str, page_type: str, page_id: str, html: str) -> None:
        self._path(mod_id, page_type, page_id).write_text(html, encoding="utf-8")

    def load(self, mod_id: str, page_type: str, page_id: str) -> str:
        return self._path(mod_id, page_type, page_id).read_text(encoding="utf-8")

    def exists(self, mod_id: str, page_type: str, page_id: str) -> bool:
        return self._path(mod_id, page_type, page_id).exists()
