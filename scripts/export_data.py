"""Export MySQL + Qdrant data for distribution.

Creates:
  data/export/mods.sql.gz     — MySQL dump of mods table
  data/export/qdrant_snapshot — Qdrant collection snapshot

Users download these and run: minemate import-data
"""
import subprocess
from pathlib import Path

from loguru import logger

from config.settings import settings

EXPORT_DIR = Path("data/export")


def export_mysql():
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    sql_file = EXPORT_DIR / "mods.sql.gz"
    logger.info("Exporting MySQL mods table to {}", sql_file)
    cmd = [
        "docker", "exec", "mcmod-mysql",
        "mysqldump", "-u", settings.mysql_user, f"-p{settings.mysql_password}",
        settings.mysql_db, "mods",
    ]
    with sql_file.open("wb") as f:
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        f.write(r.stdout)
    logger.info("MySQL dump: {:.1f} KB", sql_file.stat().st_size / 1024)


def export_qdrant():
    """Create Qdrant snapshot."""
    from qdrant_client import QdrantClient
    client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    snap = client.create_snapshot(collection_name=settings.qdrant_collection)
    logger.info("Qdrant snapshot created: {}", snap.name)


def main():
    logger.info("Exporting data...")
    export_mysql()
    export_qdrant()
    logger.info("Done. Files in {}", EXPORT_DIR)


if __name__ == "__main__":
    main()
