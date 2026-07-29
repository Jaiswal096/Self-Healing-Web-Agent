"""
logger.py — Structured, colored console logger using Python's logging + rich.

Usage:
    from src.utils.logger import get_logger
    log = get_logger("MyModule")
    log.info("Hello!")
"""

import logging
import sys
from pathlib import Path

try:
    from rich.logging import RichHandler
    from rich.console import Console

    _console = Console(stderr=True)
    _RICH_AVAILABLE = True
except ImportError:
    _RICH_AVAILABLE = False

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_DIR.mkdir(exist_ok=True)

_FILE_HANDLER = logging.FileHandler(_LOG_DIR / "agent.log", encoding="utf-8")
_FILE_HANDLER.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
)

_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Return (or create) a named logger with rich console + file output."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        # Console handler
        if _RICH_AVAILABLE:
            rich_handler = RichHandler(
                console=_console,
                show_path=False,
                rich_tracebacks=True,
            )
            rich_handler.setLevel(level)
            logger.addHandler(rich_handler)
        else:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
                )
            )
            logger.addHandler(stream_handler)

        # File handler (always)
        logger.addHandler(_FILE_HANDLER)

    logger.propagate = False
    _loggers[name] = logger
    return logger
