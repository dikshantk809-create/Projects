"""Structured logging used across edge + backend."""
from __future__ import annotations
import sys
from loguru import logger

_configured = False

def get_logger(name: str = "aicam", level: str = "INFO"):
    global _configured
    if not _configured:
        logger.remove()
        logger.add(
            sys.stderr,
            level=level,
            serialize=False,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
                   "| <level>{level: <8}</level> | <cyan>{extra[ctx]}</cyan> | {message}",
        )
        _configured = True
    return logger.bind(ctx=name)
