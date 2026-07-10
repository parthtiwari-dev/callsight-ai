from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class NormalizedCall:
    external_call_id: str
    advisor_ref: str
    customer_ref_hashed: str | None
    audio_ref: str
    started_at: datetime | None
    duration_seconds: int | None
    metadata: dict


class CallSource(ABC):
    @abstractmethod
    def fetch_new_calls(self) -> list[NormalizedCall]:
        """Return source-specific calls normalized into the pipeline contract."""

    @abstractmethod
    def get_audio(self, audio_ref: str) -> bytes:
        """Return audio bytes for a normalized call payload."""


def resolve_existing_file(path: str | Path) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"File does not exist: {resolved}")
    return resolved
