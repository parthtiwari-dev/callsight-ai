import streamlit as st

from dashboard import data
from dashboard.style import configure_page

configure_page("Sales Director")
st.title("Sales Director")
st.caption("Org-level call quality, risk, and coaching visibility.")

with data.get_session() as db:
    summary = data.org_summary(db)
    teams = data.list_teams(db)
    selected_team = st.sidebar.selectbox(
        "Team filter",
        ["All teams"] + [team.name for team in teams],
    )
    team_id = next((team.team_id for team in teams if team.name == selected_team), None)
    recent_calls = data.list_recent_calls(db, 20, team_id)

cols = st.columns(3)
cols[0].metric("Calls processed", summary["calls_processed"])
cols[1].metric("Average quality", summary["average_overall_score"] or "N/A")
cols[2].metric("Unresolved critical flags", summary["unresolved_critical_flag_count"])

left, right = st.columns([1, 1])
with left:
    st.subheader("Top issue tags")
    if summary["top_issue_tags"]:
        st.dataframe(summary["top_issue_tags"], use_container_width=True, hide_index=True)
    else:
        st.info("No active issue tags.")

with right:
    st.subheader("Team leaderboard")
    if summary["team_leaderboard"]:
        st.dataframe(summary["team_leaderboard"], use_container_width=True, hide_index=True)
    else:
        st.info("No team scores yet.")

st.subheader("Recent scored calls")
st.dataframe(
    [
        {
            "Call": str(call.call_id),
            "Advisor": call.advisor.name if call.advisor else "Unknown",
            "Team": call.advisor.team.name if call.advisor and call.advisor.team else "Unknown",
            "Status": call.status.value,
            "Score": call.analysis.overall_score if call.analysis else None,
            "Active flags": data.crud.count_active_flags(call),
        }
        for call in recent_calls
    ],
    use_container_width=True,
    hide_index=True,
)
