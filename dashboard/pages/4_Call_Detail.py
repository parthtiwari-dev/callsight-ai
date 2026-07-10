import streamlit as st
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import data
from dashboard.style import configure_page, severity_color

configure_page("Call Detail")
st.title("Call Detail")
st.caption("Transcript, score evidence, coaching notes, and issue flags.")

with data.get_session() as db:
    calls = data.list_recent_calls(db, 100)
    if not calls:
        st.info("No calls yet. Run `python scripts/seed_demo_data.py`.")
        st.stop()
    call = st.sidebar.selectbox(
        "Call",
        calls,
        format_func=lambda item: f"{item.external_call_id} / {item.advisor.name if item.advisor else 'Unknown'}",
    )
    call = data.get_call(db, call.call_id)

    if call is None:
        st.error("Call not found.")
        st.stop()

    if call.analysis:
        cols = st.columns(6)
        cols[0].metric("Overall", call.analysis.overall_score)
        cols[1].metric("Discovery", call.analysis.needs_discovery_score)
        cols[2].metric("Product", call.analysis.product_knowledge_score)
        cols[3].metric("Objections", call.analysis.objection_handling_score)
        cols[4].metric("Compliance", call.analysis.compliance_score)
        cols[5].metric("Next step", call.analysis.next_step_booking_score)

        st.subheader("Summary")
        st.write(call.analysis.call_summary)

        st.subheader("Coaching notes")
        for note in call.analysis.coaching_notes:
            st.markdown(f"- {note}")

    if call.raw_audio_path and Path(call.raw_audio_path).exists():
        st.audio(call.raw_audio_path)

    st.subheader("Issue flags")
    if not call.issue_tags:
        st.info("No issue tags.")
    for tag in call.issue_tags:
        color = severity_color(tag.severity, tag.status.value)
        st.markdown(
            f"<span class='fit-tag' style='border-color:{color}; color:{color}'>{tag.severity} / {tag.status.value}</span> "
            f"**{tag.tag_type}** - {tag.reason}",
            unsafe_allow_html=True,
        )
        st.caption(f"Quote: {tag.quoted_line} | Confidence: {tag.confidence}")

    st.subheader("Transcript")
    for segment in sorted(call.transcript_segments, key=lambda item: item.start_time):
        st.markdown(
            f"**{segment.speaker_label.title()}** "
            f"`{segment.start_time:.1f}s-{segment.end_time:.1f}s`  \n"
            f"{segment.text}"
        )
