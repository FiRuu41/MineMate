"""Import a minemate-data zip into local SQLite + Chroma paths.

Mirror of scripts/dev/package_data.py. Public — distributed in the wheel
so end users can run `minemate import-data <zip>` after `pipx install minemate`.

Layout (zip):
    manifest.json {created_at, mod_count, chunk_count, sha256_of_db, ...}
    minemate.db
    chroma/...
"""
import hashlib
import json
import sqlite3
import sys
import zipfile
from pathlib import Path


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _count_mods(db_path: Path) -> int:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT COUNT(*) FROM mods").fetchone()[0]
    finally:
        conn.close()


class ImportError_(Exception):
    """Raised on any import failure (zip corruption, hash mismatch, abort, etc.)."""


def import_data(
    zip_path: Path,
    sqlite_target: Path,
    chroma_target: Path,
    force: bool = False,
    echo=print,
) -> dict:
    """Import zip into the given targets. Returns manifest dict on success."""
    zip_path = Path(zip_path)
    sqlite_target = Path(sqlite_target)
    chroma_target = Path(chroma_target)

    if not zip_path.is_file():
        raise ImportError_(f"zip not found: {zip_path}")

    # Step 1: open zip + read manifest
    echo(f"[1/4] Reading zip manifest from {zip_path.name} ...")
    try:
        zf = zipfile.ZipFile(zip_path, "r")
    except zipfile.BadZipFile as e:
        raise ImportError_(f"corrupted zip: {e}") from e

    manifest = {}
    try:
        try:
            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            echo(
                f"        OK (created {manifest.get('created_at', '?')[:10]}, "
                f"{manifest.get('mod_count', '?')} mods, "
                f"{manifest.get('chunk_count', '?')} chunks)"
            )
        except KeyError:
            echo("        WARN: manifest.json missing — sha256 check will be skipped")

        # Step 2: check destinations
        echo("[2/4] Checking destination paths ...")
        sqlite_exists = sqlite_target.exists()
        chroma_exists = chroma_target.exists()
        echo(f"        SQLite -> {sqlite_target}   ({'exists' if sqlite_exists else 'new'})")
        echo(f"        Chroma -> {chroma_target}   ({'exists' if chroma_exists else 'new'})")
        if (sqlite_exists or chroma_exists) and not force:
            raise ImportError_(
                "data already present at destination. Use --force to overwrite."
            )

        # Step 3: extract
        echo("[3/4] Extracting ...")
        sqlite_target.parent.mkdir(parents=True, exist_ok=True)
        chroma_target.mkdir(parents=True, exist_ok=True)
        # SQLite file
        with zf.open("minemate.db") as src, sqlite_target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
        # Chroma subtree
        for name in zf.namelist():
            if name.startswith("chroma/") and not name.endswith("/"):
                rel = name[len("chroma/"):]
                dst_path = chroma_target / rel
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src, dst_path.open("wb") as dst:
                    while chunk := src.read(1024 * 1024):
                        dst.write(chunk)
        echo(f"        Extracted {zip_path.stat().st_size // 1024 // 1024} MB")

        # Step 4: verify
        echo("[4/4] Verifying ...")
        actual_count = _count_mods(sqlite_target)
        expected_count = manifest.get("mod_count")
        if expected_count is not None and actual_count != expected_count:
            raise ImportError_(
                f"mod_count mismatch: expected {expected_count}, got {actual_count}"
            )
        echo(f"        mod_count: {actual_count}   OK")

        expected_sha = manifest.get("sha256_of_db")
        if expected_sha:
            actual_sha = _sha256(sqlite_target)
            if actual_sha != expected_sha:
                raise ImportError_(f"sha256 mismatch: expected {expected_sha}, got {actual_sha}")
            echo("        sha256(db): match   OK")
    finally:
        zf.close()

    return manifest


if __name__ == "__main__":
    # Standalone usage: python -m scripts.import_data <zip> [--force]
    import argparse
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from config.settings import settings

    parser = argparse.ArgumentParser()
    parser.add_argument("zip_path")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        import_data(
            Path(args.zip_path),
            settings.resolved_sqlite_path,
            settings.resolved_chroma_path,
            force=args.force,
        )
        print("\nImport complete. Run 'minemate start' to launch.")
    except ImportError_ as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
