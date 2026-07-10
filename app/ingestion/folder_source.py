import json
from datetime import datetime
from pathlib import Path

from app.ingestion.base import CallSource, NormalizedCall, resolve_existing_file


AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


class FolderSource(CallSource):
    def __init__(self, folder: str | Path):
        self.folder = Path(folder)

    def fetch_new_calls(self) -> list[NormalizedCall]:
        calls: list[NormalizedCall] = []
        for metadata_path in sorted(self.folder.glob("*.metadata.json")):
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            stem = metadata_path.name.removesuffix(".metadata.json")
            audio_path = self._find_audio_for_stem(stem)
            calls.append(call_from_metadata(metadata, audio_path))
        return calls

    def get_audio(self, audio_ref: str) -> bytes:
        return resolve_existing_file(audio_ref).read_bytes()

    def _find_audio_for_stem(self, stem: str) -> Path:
        for extension in AUDIO_EXTENSIONS:
            candidate = self.folder / f"{stem}{extension}"
            if candidate.exists():
                return candidate
        raise FileNotFoundError(f"No audio file found for metadata stem: {stem}")


def call_from_metadata(metadata: dict, audio_path: str | Path) -> NormalizedCall:
    started_at_raw = metadata.get("started_at")
    started_at = datetime.fromisoformat(started_at_raw) if started_at_raw else None
    return NormalizedCall(
        external_call_id=metadata["external_call_id"],
        advisor_ref=metadata["advisor_ref"],
        customer_ref_hashed=metadata.get("customer_ref_hashed"),
        audio_ref=str(resolve_existing_file(audio_path)),
        started_at=started_at,
        duration_seconds=metadata.get("duration_seconds"),
        metadata=metadata,
    )
