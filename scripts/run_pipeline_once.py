import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ingestion.folder_source import call_from_metadata
from app.pipeline.orchestrator import run_pipeline_spine
from app.utils.logging import configure_logging


def load_metadata(metadata_path: str | None) -> dict:
    if metadata_path is None:
        return {
            "external_call_id": "mock-call-001",
            "advisor_ref": "advisor-001",
            "customer_ref_hashed": "customer-demo-hash",
            "started_at": "2026-07-10T13:40:00+05:30",
            "duration_seconds": 180,
        }
    return json.loads(Path(metadata_path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 1 pipeline spine once.")
    parser.add_argument("--audio-path", help="Path to an audio file for real speech mode.")
    parser.add_argument("--metadata-path", help="Path to matching metadata JSON.")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use fixture transcript data and skip speech model dependencies.",
    )
    args = parser.parse_args()

    if not args.mock and not args.audio_path:
        parser.error("--audio-path is required unless --mock is set")

    configure_logging()
    metadata = load_metadata(args.metadata_path)
    normalized_call = None
    if args.audio_path:
        normalized_call = call_from_metadata(metadata, args.audio_path)

    pipeline_result = run_pipeline_spine(args.audio_path, mock=args.mock)
    output = {
        "call": (
            normalized_call.__dict__
            if normalized_call
            else {
                **metadata,
                "audio_ref": None,
            }
        ),
        "pipeline": pipeline_result,
    }
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
