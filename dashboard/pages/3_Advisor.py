import streamlit as st

from dashboard import data
from dashboard.style import configure_page

configure_page("Advisor")
st.title("Advisor")
st.caption("Personal call quality, coaching notes, and flag contests.")

with data.get_session() as db:
    advisors = data.list_advisors(db)
    if not advisors:
        st.info("No advisors yet. Run `python scripts/seed_demo_data.py`.")
        st.stop()

    advisor = st.sidebar.selectbox("Advisor", advisors, format_func=lambda item: item.name)
    summary = data.advisor_summary(db, advisor.user_id)

    cols = st.columns(3)
    cols[0].metric("Average score", summary["average_score"] or "N/A")
    cols[1].metric("Calls", len(summary["calls"]))
    cols[2].metric("Active flags", len(summary["active_tags"]))

    st.subheader("Recent calls")
    st.dataframe(
        [
            {
                "Call": str(call.call_id),
                "Status": call.status.value,
                "Score": call.analysis.overall_score if call.analysis else None,
                "Summary": call.analysis.call_summary if call.analysis else "",
            }
            for call in summary["calls"][:10]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Coaching notes")
    for note in summary["coaching_notes"]:
        st.markdown(f"- {note}")

    st.subheader("Active flags")
    if not summary["active_tags"]:
        st.info("No active flags.")
    for tag in summary["active_tags"]:
        st.markdown(f"**{tag.tag_type}** ({tag.severity}) - {tag.reason}")
        st.caption(f"Quote: {tag.quoted_line}")
        reason = st.text_input("Contest reason", key=f"reason-{tag.tag_id}")
        if st.button("Contest flag", key=f"contest-{tag.tag_id}") and reason:
            data.contest_tag(db, tag.call_id, tag.tag_id, advisor.user_id, reason)
            st.rerun()

    st.subheader("Resolved contest history")
    st.dataframe(
        [
            {
                "Contest": str(contest.contest_id),
                "Tag": str(contest.tag_id),
                "Status": contest.status.value,
            }
            for contest in summary["resolved_contests"]
        ],
        use_container_width=True,
        hide_index=True,
    )
