import streamlit as st


LIGHT = {
    "bg": "#f7fbff",
    "panel": "#ffffff",
    "panel_alt": "#eef7ff",
    "text": "#102033",
    "muted": "#5b7088",
    "border": "#d8e8f6",
    "accent": "#38a6ff",
}

DARK = {
    "bg": "#050506",
    "panel": "#111316",
    "panel_alt": "#171b20",
    "text": "#eef6ff",
    "muted": "#9fb2c5",
    "border": "#28313a",
    "accent": "#4db8ff",
}


def configure_page(title: str) -> dict:
    st.set_page_config(page_title=f"{title} | FitNova Callsight AI", layout="wide")
    theme_name = st.sidebar.radio("Theme", ["Light", "Dark"], horizontal=True)
    theme = LIGHT if theme_name == "Light" else DARK
    apply_theme(theme)
    st.sidebar.caption("FitNova Callsight AI")
    return theme


def apply_theme(theme: dict) -> None:
    st.markdown(
        f"""
        <style>
        :root {{
            --fit-bg: {theme["bg"]};
            --fit-panel: {theme["panel"]};
            --fit-panel-alt: {theme["panel_alt"]};
            --fit-text: {theme["text"]};
            --fit-muted: {theme["muted"]};
            --fit-border: {theme["border"]};
            --fit-accent: {theme["accent"]};
        }}
        .stApp {{
            background: var(--fit-bg);
            color: var(--fit-text);
        }}
        h1, h2, h3, h4, h5, h6, p, label, span {{
            color: var(--fit-text);
        }}
        section[data-testid="stSidebar"] {{
            background: var(--fit-panel);
            border-right: 1px solid var(--fit-border);
        }}
        div[data-testid="stMetric"] {{
            background: var(--fit-panel);
            border: 1px solid var(--fit-border);
            border-radius: 8px;
            padding: 14px 16px;
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--fit-border);
            border-radius: 8px;
        }}
        .fit-panel {{
            background: var(--fit-panel);
            border: 1px solid var(--fit-border);
            border-radius: 8px;
            padding: 16px;
            margin: 10px 0;
        }}
        .fit-muted {{ color: var(--fit-muted); }}
        .fit-tag {{
            display: inline-block;
            border-radius: 999px;
            padding: 3px 9px;
            border: 1px solid var(--fit-border);
            margin: 2px 4px 2px 0;
            font-size: 12px;
        }}
        .fit-accent {{ color: var(--fit-accent); }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def severity_color(severity: str, status: str = "active") -> str:
    if status == "dismissed":
        return "#7a8793"
    return {
        "critical": "#e5484d",
        "high": "#f97316",
        "medium": "#38a6ff",
        "low": "#33a06f",
    }.get(severity, "#7a8793")


def panel(markdown: str) -> None:
    st.markdown(f"<div class='fit-panel'>{markdown}</div>", unsafe_allow_html=True)
