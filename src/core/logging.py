import logging
import sys

from pythonjsonlogger.json import JsonFormatter

# Loggers that should only show WARNING or above (suppress noise)
_SUPPRESSED_LOGGERS = (
    "httpx",
    "httpcore",
    "watchfiles",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "asyncio",
    "agentscope",
)


def configure_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for the application.

    Only application loggers (src.*) emit at the configured level.
    Framework/library loggers are suppressed to WARNING to keep terminal clean.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.WARNING)  # default: only warnings from libs

    # Application loggers get the configured level
    app_logger = logging.getLogger("src")
    app_logger.setLevel(level)

    # Suppress noisy library loggers
    for name in _SUPPRESSED_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
