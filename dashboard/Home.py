import streamlit as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import data
from dashboard.style import configure_page, panel

theme = configure_page("Home")
st.title("FitNova Callsight AI")
st.caption("Sales-call intelligence for quality, coaching, and defensible QA review.")

with data.get_session() as db:
    summary = data.org_summary(db)
    calls = data.list_recent_calls(db, 8)

cols = st.columns(4)
cols[0].metric("Calls processed", summary["calls_processed"])
cols[1].metric("Average score", summary["average_overall_score"] or "N/A")
cols[2].metric("Critical flags", summary["unresolved_critical_flag_count"])
cols[3].metric("Teams", len(summary["team_leaderboard"]))

panel(
    "<b>Demo flow</b><br>"
    "Open Process Call, run a mock demo call, inspect it in Call Detail, contest a flag, "
    "and resolve it from the Team Leader view."
)

st.subheader("Recent calls")
if calls:
    st.dataframe(
        [
            {
                "Call": str(call.call_id)[:8],
                "Advisor": call.advisor.name if call.advisor else "Unknown",
                "Status": call.status.value,
                "Score": call.analysis.overall_score if call.analysis else None,
                "Active flags": data.crud.count_active_flags(call),
            }
            for call in calls
        ],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No calls yet. Run `python scripts/seed_demo_data.py` to populate the demo.")
