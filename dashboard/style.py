import streamlit as st


LIGHT = {
    "bg": "#f7fbff",
    "panel": "#ffffff",
    "panel_alt": "#eef7ff",
    "text": "#102033",
    "muted": "#5b7088",
    "border": "#d8e8f6",
    "accent": "#38a6ff",
    "accent_soft": "#e6f5ff",
    "button_text": "#ffffff",
    "danger": "#d92d20",
    "warning": "#b54708",
    "success": "#027a48",
}

DARK = {
    "bg": "#050506",
    "panel": "#111316",
    "panel_alt": "#171b20",
    "text": "#eef6ff",
    "muted": "#9fb2c5",
    "border": "#28313a",
    "accent": "#4db8ff",
    "accent_soft": "#102536",
    "button_text": "#04111c",
    "danger": "#ff6b6b",
    "warning": "#ffb020",
    "success": "#49d17d",
}


def configure_page(title: str) -> dict:
    st.set_page_config(page_title=f"{title} | FitNova Callsight AI", layout="wide")
    if "fitnova_theme" not in st.session_state:
        st.session_state.fitnova_theme = "Light"
    st.session_state["_fitnova_theme_widget"] = st.session_state.fitnova_theme

    def persist_theme() -> None:
        st.session_state.fitnova_theme = st.session_state["_fitnova_theme_widget"]

    theme_name = st.sidebar.radio(
        "Theme",
        ["Light", "Dark"],
        horizontal=True,
        key="_fitnova_theme_widget",
        on_change=persist_theme,
    )
    st.session_state.fitnova_theme = theme_name
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
            --fit-accent-soft: {theme["accent_soft"]};
            --fit-button-text: {theme["button_text"]};
            --fit-danger: {theme["danger"]};
            --fit-warning: {theme["warning"]};
            --fit-success: {theme["success"]};
        }}
        .stApp {{
            background: var(--fit-bg);
            color: var(--fit-text);
        }}
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {{
            background: var(--fit-bg);
        }}
        h1, h2, h3, h4, h5, h6, p, label,
        [data-testid="stMarkdownContainer"],
        [data-testid="stCaptionContainer"] {{
            color: var(--fit-text);
        }}
        [data-testid="stCaptionContainer"] p,
        .fit-muted {{
            color: var(--fit-muted);
        }}
        section[data-testid="stSidebar"] {{
            background: var(--fit-panel);
            border-right: 1px solid var(--fit-border);
        }}
        section[data-testid="stSidebar"] * {{
            color: var(--fit-text);
        }}
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {{
            border-radius: 8px;
            color: var(--fit-text);
        }}
        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {{
            background: var(--fit-panel-alt);
        }}
        div[data-testid="stMetric"] {{
            background: var(--fit-panel);
            border: 1px solid var(--fit-border);
            border-radius: 8px;
            padding: 14px 16px;
        }}
        div[data-testid="stMetric"] label,
        div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
            color: var(--fit-text);
        }}
        div[data-testid="stDataFrame"] {{
            border: 1px solid var(--fit-border);
            border-radius: 8px;
            background: var(--fit-panel);
        }}
        input, textarea,
        [data-baseweb="input"] input,
        [data-baseweb="textarea"] textarea {{
            background: var(--fit-panel) !important;
            color: var(--fit-text) !important;
            caret-color: var(--fit-accent) !important;
        }}
        [data-baseweb="input"],
        [data-baseweb="textarea"],
        [data-baseweb="select"] > div {{
            background: var(--fit-panel) !important;
            border-color: var(--fit-border) !important;
            color: var(--fit-text) !important;
        }}
        [data-baseweb="select"] span,
        [data-baseweb="popover"] li,
        [data-baseweb="menu"] li {{
            color: var(--fit-text) !important;
        }}
        [data-baseweb="popover"] ul,
        [data-baseweb="menu"] ul {{
            background: var(--fit-panel) !important;
            border: 1px solid var(--fit-border) !important;
        }}
        div[role="radiogroup"] label {{
            background: var(--fit-panel);
            border-radius: 999px;
            padding: 2px 8px;
        }}
        div[role="radiogroup"] label:hover {{
            background: var(--fit-panel-alt);
        }}
        .stButton > button {{
            border-radius: 8px;
            border: 1px solid var(--fit-border);
            background: var(--fit-panel);
            color: var(--fit-text);
        }}
        .stButton > button:hover {{
            border-color: var(--fit-accent);
            color: var(--fit-accent);
        }}
        .stButton > button[kind="primary"] {{
            background: var(--fit-accent);
            border-color: var(--fit-accent);
            color: var(--fit-button-text);
        }}
        [data-testid="stFileUploader"] section {{
            background: var(--fit-panel);
            border-color: var(--fit-border);
        }}
        [data-testid="stFileUploader"] small,
        [data-testid="stFileUploader"] span {{
            color: var(--fit-muted);
        }}
        [data-testid="stAlert"] {{
            background: var(--fit-panel-alt);
            border: 1px solid var(--fit-border);
            color: var(--fit-text);
        }}
        [data-testid="stAlert"] * {{
            color: var(--fit-text);
        }}
        code, pre,
        [data-testid="stCodeBlock"] {{
            background: var(--fit-panel-alt) !important;
            color: var(--fit-text) !important;
            border-color: var(--fit-border) !important;
        }}
        .fit-panel {{
            background: var(--fit-panel);
            border: 1px solid var(--fit-border);
            border-radius: 8px;
            padding: 16px;
            margin: 10px 0;
            color: var(--fit-text);
        }}
        .fit-panel * {{
            color: inherit;
        }}
        .fit-tag {{
            display: inline-block;
            border-radius: 999px;
            padding: 3px 9px;
            border: 1px solid var(--fit-border);
            margin: 2px 4px 2px 0;
            font-size: 12px;
            font-weight: 600;
        }}
        .fit-accent {{ color: var(--fit-accent); }}
        .fit-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
            margin: 12px 0;
        }}
        .fit-card {{
            background: var(--fit-panel);
            border: 1px solid var(--fit-border);
            border-radius: 8px;
            padding: 14px;
        }}
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
