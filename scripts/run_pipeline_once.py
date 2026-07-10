import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.session import SessionLocal, create_all_tables
from app.ingestion.base import NormalizedCall
from app.ingestion.folder_source import call_from_metadata
from app.pipeline.orchestrator import (
    analyze_pipeline_result,
    process_and_store_call,
    run_pipeline_spine,
)
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
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run structured analysis after transcript generation.",
    )
    parser.add_argument(
        "--mock-analysis",
        action="store_true",
        help="Use deterministic local analysis even if OPENAI_API_KEY is configured.",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Persist call, transcript, analysis, tags, and events to the database.",
    )
    args = parser.parse_args()

    if not args.mock and not args.audio_path:
        parser.error("--audio-path is required unless --mock is set")
    if args.persist and not args.analyze:
        parser.error("--persist requires --analyze")

    configure_logging()
    metadata = load_metadata(args.metadata_path)
    normalized_call = (
        call_from_metadata(metadata, args.audio_path)
        if args.audio_path
        else NormalizedCall(
            external_call_id=metadata["external_call_id"],
            advisor_ref=metadata["advisor_ref"],
            customer_ref_hashed=metadata.get("customer_ref_hashed"),
            audio_ref="mock://fixture",
            started_at=None,
            duration_seconds=metadata.get("duration_seconds"),
            metadata=metadata,
        )
    )

    if args.persist:
        create_all_tables()
        with SessionLocal() as db:
            pipeline_result = process_and_store_call(
                db,
                normalized_call,
                mock=args.mock,
                analyze=True,
                mock_analysis=args.mock_analysis,
            )
    else:
        pipeline_result = run_pipeline_spine(args.audio_path, mock=args.mock)
        if args.analyze:
            pipeline_result = analyze_pipeline_result(
                pipeline_result,
                mock_analysis=args.mock_analysis,
                duration_seconds=normalized_call.duration_seconds,
            )

    output = {"call": normalized_call.__dict__, "pipeline": pipeline_result}
    print(json.dumps(output, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
