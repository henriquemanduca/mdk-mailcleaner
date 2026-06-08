import logging
import os

from dotenv import load_dotenv

load_dotenv()


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def get_env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def get_request_queue() -> str:
    return os.getenv("REQUEST_QUEUE", "mailcleaner:requests")
