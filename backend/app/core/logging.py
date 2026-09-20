from loguru import logger

from backend.app.core.paths import LOGS


LOGS.mkdir(exist_ok=True)


logger.add(
    LOGS / "application.log",
    rotation="10 MB",
    retention="10 days",
    level="INFO",
)


logger.add(
    LOGS / "errors.log",
    rotation="10 MB",
    retention="10 days",
    level="ERROR",
)


app_logger = logger
