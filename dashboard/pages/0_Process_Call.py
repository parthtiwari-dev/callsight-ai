import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from dashboard import data
from dashboard.style import configure_page, panel

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg"}


def parse_started_at(value: str) -> datetime | None:
    if not value.strip():
        return None
    return datetime.fromisoformat(value.strip())


configure_page("Process Call")
st.title("Process Call")
st.caption("Run the full ingestion, transcript, analysis, guardrail, and persistence loop.")

panel(
    "<b>Reliable demo path</b><br>"
    "Use Mock demo call for the take-home walkthrough. It needs no API keys, audio models, "
    "or external downloads, but still writes real calls, transcripts, scores, and flags to Postgres."
)

default_id = f"streamlit-demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
mode = st.radio("Mode", ["Mock demo call", "Upload audio"], horizontal=True, key="process_mode")

left, right = st.columns([1, 1])
with left:
    external_call_id = st.text_input("External call id", value=default_id)
    advisor_ref = st.text_input("Advisor ref", value="advisor-streamlit-001")
with right:
    customer_ref_hashed = st.text_input("Customer hash", value="customer-streamlit-demo")
    duration_seconds = st.number_input("Duration seconds", min_value=1, value=180, step=15)
started_at_text = st.text_input("Started at (optional ISO timestamp)", value="")

audio_ref = "mock://fixture"
mock = mode == "Mock demo call"

if mode == "Upload audio":
    settings = get_settings()
    st.warning(
        "Real audio mode requires `pip install -r requirements-speech.txt`. "
        "Diarization also requires Hugging Face model access. If `OPENAI_API_KEY` is absent, "
        "analysis falls back to the deterministic mock analyzer."
    )
    if not settings.huggingface_access_token:
        st.info("HUGGINGFACE_ACCESS_TOKEN is not set, so diarization will not run successfully yet.")
    uploaded = st.file_uploader(
        "Audio file",
        type=[extension.removeprefix(".") for extension in sorted(SUPPORTED_AUDIO_EXTENSIONS)],
    )
    if uploaded is not None:
        suffix = Path(uploaded.name).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
            st.error("Unsupported file type. Use wav, mp3, m4a, flac, or ogg.")
        else:
            upload_dir = ROOT / "sample_calls" / "uploads"
            upload_dir.mkdir(parents=True, exist_ok=True)
            destination = upload_dir / uploaded.name
            destination.write_bytes(uploaded.getbuffer())
            audio_ref = str(destination)

button_label = "Process mock call" if mock else "Process uploaded audio"
disabled = mode == "Upload audio" and audio_ref == "mock://fixture"

if st.button(button_label, type="primary", disabled=disabled):
    try:
        started_at = parse_started_at(started_at_text)
        with data.get_session() as db:
            result = data.process_dashboard_call(
                db,
                external_call_id=external_call_id,
                advisor_ref=advisor_ref,
                customer_ref_hashed=customer_ref_hashed or None,
                duration_seconds=int(duration_seconds),
                started_at=started_at,
                audio_ref=audio_ref,
                mock=mock,
                mock_analysis=mock,
            )
        st.success("Call processed and stored.")
        cols = st.columns(5)
        cols[0].metric("Created", str(result["created"]))
        cols[1].metric("Status", result["final_status"])
        cols[2].metric("Score", result["overall_score"] or "N/A")
        cols[3].metric("Flags", result["active_flag_count"])
        cols[4].metric("Segments", result["segment_count"])
        st.code(result["call_id"], language="text")
        st.info("Open Call Detail and select this call to inspect the transcript, scores, and flags.")
    except ValueError as exc:
        st.error(f"Invalid input: {exc}")
    except RuntimeError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Processing failed: {exc}")
