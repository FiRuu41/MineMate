import sys
import uuid
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

from config.settings import settings

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def new_trace_id() -> str:
    tid = uuid.uuid4().hex[:12]
    trace_id_var.set(tid)
    return tid


def setup_logging() -> None:
    logger.remove()

    def _patch(record):
        record["extra"]["trace_id"] = trace_id_var.get()

    logger.configure(patcher=_patch, extra={"trace_id": "-"})

    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<7}</level> | "
        "<cyan>trace={extra[trace_id]}</cyan> | <level>{message}</level>"
    )
    logger.add(sys.stderr, level=settings.log_level, format=fmt)

    log_path = Path(settings.log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path / "{time:YYYY-MM-DD}.log",
        level=settings.log_level,
        format=fmt,
        rotation="00:00",
        retention="14 days",
    )
