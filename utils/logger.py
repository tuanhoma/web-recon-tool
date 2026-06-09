"""Logger — centralised logging configuration with Rich console + JSON file handler."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

_console = Console(stderr=True)


class _JsonFileHandler(logging.FileHandler):
    """Writes log records as newline-delimited JSON."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "name": record.name,
                "msg": self.format(record),
            }
            if record.exc_info:
                entry["exc"] = self.formatException(record.exc_info)
            with open(self.baseFilename, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            self.handleError(record)


def get_logger(
    name: str = "reconflow",
    level: str = "INFO",
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """Return a logger with Rich console handler and optional JSON file handler.

    Handlers are only attached to the root 'reconflow' logger to prevent
    duplicate output from child loggers (which propagate upward by default).
    """
    logger = logging.getLogger(name)

    # Child loggers (e.g. reconflow.adapter): just set level, rely on propagation
    root_logger = logging.getLogger("reconflow")
    if name != "reconflow" and root_logger.handlers:
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        return logger

    # Avoid duplicate handlers on repeated calls to the root logger
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Rich console handler
    rich_handler = RichHandler(
        console=_console,
        rich_tracebacks=True,
        show_path=False,
        markup=True,
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s", datefmt="[%X]"))
    logger.addHandler(rich_handler)

    # JSON file handler
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        json_handler = _JsonFileHandler(str(log_file), encoding="utf-8")
        json_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(json_handler)

    return logger


def make_progress() -> Progress:
    """Return a pre-configured Rich Progress bar for pipeline stages."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=_console,
        transient=False,
    )


# Module-level default logger (reconfigured by orchestrator on startup)
log = get_logger()
