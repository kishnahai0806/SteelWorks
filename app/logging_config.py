"""Application logging configuration helpers."""

from __future__ import annotations

import logging
import os

DEFAULT_LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"


def _resolve_level(level_name: str) -> int:
    return getattr(logging, level_name.upper(), logging.INFO)


def configure_logging() -> None:
    """
    Configure root logging once while allowing runtime level overrides.

    Streamlit can rerun scripts multiple times in one process. We avoid adding
    duplicate handlers by reusing existing handlers when present.
    """
    configured_level = _resolve_level(os.getenv("APP_LOG_LEVEL", DEFAULT_LOG_LEVEL))
    root_logger = logging.getLogger()

    if root_logger.handlers:
        root_logger.setLevel(configured_level)
        return

    logging.basicConfig(level=configured_level, format=LOG_FORMAT)
