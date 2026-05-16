"""Initialize MySQL schema by creating all tables."""
from loguru import logger

from config.logging import setup_logging
from pipeline.storage.db import Base, engine
from pipeline.storage.models import ItemAlias, Mod  # noqa: F401  (register models)


def main() -> None:
    setup_logging()
    logger.info("Creating tables on {}", engine.url)
    Base.metadata.create_all(engine)
    logger.info("Done.")


if __name__ == "__main__":
    main()
