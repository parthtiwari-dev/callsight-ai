import logging
from pathlib import Path


def configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        Path("logs").mkdir(exist_ok=True)
        handlers.append(logging.FileHandler("logs/pipeline.log", encoding="utf-8"))
    except PermissionError:
        pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=handlers,
        force=True,
    )
