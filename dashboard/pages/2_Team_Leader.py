import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import data
from dashboard.style import configure_page

configure_page("Team Leader")
st.title("Team Leader")
st.caption("Team coaching, issue distribution, and human review queue.")

with data.get_session() as db:
    teams = data.list_teams(db)
    if not teams:
        st.info("No teams yet. Run `python scripts/seed_demo_data.py`.")
        st.stop()

    selected = st.sidebar.selectbox("Team", teams, format_func=lambda team: team.name)
    summary = data.team_summary(db, selected.team_id)

    cols = st.columns(3)
    cols[0].metric("Team average", summary["average_score"] or "N/A")
    cols[1].metric("Calls reviewed", len(summary["calls"]))
    cols[2].metric("Pending contests", len(summary["pending_contests"]))

    st.subheader("Advisor roster")
    st.dataframe(summary["advisor_rows"], use_container_width=True, hide_index=True)

    st.subheader("Active tag distribution")
    if summary["tag_distribution"]:
        st.dataframe(
            [{"Tag / severity": key, "Count": value} for key, value in summary["tag_distribution"].items()],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No active tags for this team.")

    st.subheader("Pending contests")
    if not summary["pending_contests"]:
        st.info("No pending contests.")
    for contest in summary["pending_contests"]:
        tag = contest.tag
        call = tag.call
        st.markdown(
            f"**{tag.tag_type}** on call `{str(call.call_id)[:8]}`  \n"
            f"Quote: _{tag.quoted_line}_  \n"
            f"Advisor reason: {contest.contest_reason}"
        )
        col_a, col_b = st.columns(2)
        if col_a.button("Uphold", key=f"uphold-{contest.contest_id}"):
            data.resolve_tag(db, tag.tag_id, contest.advisor_id, "upheld")
            st.rerun()
        if col_b.button("Dismiss", key=f"dismiss-{contest.contest_id}"):
            data.resolve_tag(db, tag.tag_id, contest.advisor_id, "dismissed")
            st.rerun()
