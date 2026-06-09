import sys
from loguru import logger
from backend.app.core.config import settings  # noqa: E402 — imported after logger bootstrap


def configure_logging() -> None:
    """Configure loguru for the application.

    In DEBUG mode the logger emits DEBUG-level records with a verbose format.
    In production only INFO+ records are emitted, formatted as structured JSON
    so they can be ingested by log-aggregation pipelines.
    """
    # Remove the default handler so we start from a clean slate.
    logger.remove()

    if settings.DEBUG:
        # Human-readable colourised output for local development.
        log_level = "DEBUG"
        fmt = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stderr,
            level=log_level,
            format=fmt,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Structured JSON output for production / container environments.
        log_level = "INFO"
        logger.add(
            sys.stderr,
            level=log_level,
            format="{time:YYYY-MM-DDTHH:mm:ss.SSSZ} | {level} | {name}:{function}:{line} | {message}",
            colorize=False,
            serialize=True,      # emits JSON records
            backtrace=False,
            diagnose=False,
        )

    # Also persist to a rotating file in both modes.
    logger.add(
        "logs/cybersentinel_{time:YYYY-MM-DD}.log",
        level=log_level,
        rotation="100 MB",
        retention="30 days",
        compression="gz",
        serialize=True,
        enqueue=True,        # thread/async-safe writes
    )

    logger.info(
        "Logging configured",
        app=settings.APP_NAME,
        debug=settings.DEBUG,
        level=log_level,
    )


# Run configuration immediately on import so that any module that does
#   from backend.app.core.logging import logger
# gets a fully configured logger.
configure_logging()

__all__ = ["logger", "configure_logging"]
