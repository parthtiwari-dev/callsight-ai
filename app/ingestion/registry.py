from app.ingestion.base import CallSource
from app.ingestion.folder_source import FolderSource
from app.ingestion.generic_webhook_source import GenericWebhookSource
from app.ingestion.stub_exotel_source import StubExotelSource

SOURCE_REGISTRY: dict[str, type[CallSource]] = {
    "folder": FolderSource,
    "generic_webhook": GenericWebhookSource,
    "exotel_stub": StubExotelSource,
}


def get_source_class(source_type: str) -> type[CallSource]:
    try:
        return SOURCE_REGISTRY[source_type]
    except KeyError as exc:
        available = ", ".join(sorted(SOURCE_REGISTRY))
        raise ValueError(f"Unknown source_type '{source_type}'. Available: {available}") from exc
