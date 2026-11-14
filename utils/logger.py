"""Logging padronizado. Todos os módulos usam `get_logger(__name__)`."""

import logging

from utils.config import get_settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    level = getattr(logging, get_settings().log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format=_FORMAT)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)
