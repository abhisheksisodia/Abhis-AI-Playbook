"""Logging helpers with Rich formatting."""

from __future__ import annotations

import logging
from typing import Optional

from rich.logging import RichHandler


def setup_logger(name: str = "newsletter_agent", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    handler = RichHandler(rich_tracebacks=True, show_level=True)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    base = logging.getLogger("newsletter_agent")
    if not base.handlers:
        setup_logger()
    return base if name is None else base.getChild(name)
