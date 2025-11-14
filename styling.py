import streamlit as st

def inject_custom_css():
    """Inject custom CSS for the Ohh Crumbs bakery theme"""
    st.markdown(
        """
        <style>
        /* Import Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Baloo+2:wght@400;600;700;800&display=swap');

        /* Page background & padding */
        .stApp {
            background: #fff7f2;
        }

        /* Main title "Ohh Crumbs" */
        .ohh-crumbs-title {
            font-family: "Baloo 2", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            font-size: 2.8rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            color: #2c1735;
            text-align: center;
        }

        .ohh-crumbs-subtitle {
            font-size: 0.95rem;
            color: #6b4a6f;
            text-align: center;
            letter-spacing: 2px;
        }

        /* Section cards */
        .oc-card {
            border-radius: 18px;
            padding: 1.25rem 1.4rem;
            background: #ffe9f4;
            box-shadow: 0 10px 30px rgba(0,0,0,0.04);
            border: 1px solid rgba(255, 184, 214, 0.7);
            margin-bottom: 1rem;
        }

        .oc-card.dark {
            background: #fce6ff;
        }

        .oc-card h3 {
            margin-bottom: 0.25rem;
            font-size: 1.1rem;
            font-weight: 700;
            color: #2c1735;
        }

        .oc-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.2rem 0.7rem;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            background: #a6e3cf;
            color: #184235;
        }

        .oc-pill.pink {
            background: #f29bb2;
            color: #2c1735;
        }

        .oc-pill.warning {
            background: #ffd4a3;
            color: #5c3a1e;
        }

        .oc-pill.success {
            background: #a6e3cf;
            color: #184235;
        }

        /* Buttons */
        .stButton>button {
            border-radius: 999px;
            border: none;
            padding: 0.45rem 1.2rem;
            font-weight: 600;
            background: linear-gradient(135deg, #f29bb2, #ffb4c9);
            color: #2c1735;
            box-shadow: 0 8px 18px rgba(242, 155, 178, 0.35);
            transition: all 0.2s ease;
        }

        .stButton>button:hover {
            filter: brightness(1.04);
            transform: translateY(-1px);
            box-shadow: 0 10px 25px rgba(242, 155, 178, 0.45);
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.6rem;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 999px;
            padding: 0.35rem 0.9rem;
            background: #ffe4f2;
            color: #6b4a6f;
            font-weight: 500;
        }

        .stTabs [aria-selected="true"] {
            background: #f29bb2 !important;
            color: #2c1735 !important;
            font-weight: 600;
        }

        /* Metric styling */
        [data-testid="stMetricValue"] {
            font-size: 2rem;
            font-weight: 700;
            color: #2c1735;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.8rem;
            color: #6b4a6f;
            font-weight: 600;
        }

        [data-testid="stMetricDelta"] {
            font-size: 0.85rem;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: #ffe4f2;
        }

        [data-testid="stSidebar"] h1 {
            color: #2c1735;
            font-family: "Baloo 2", sans-serif;
            font-weight: 800;
        }

        /* Radio buttons (navigation) */
        .stRadio > label {
            background: transparent !important;
        }

        .stRadio [role="radiogroup"] label {
            padding: 0.5rem 1rem;
            border-radius: 12px;
            background: #fff7f2;
            margin-bottom: 0.3rem;
            transition: all 0.2s ease;
        }

        .stRadio [role="radiogroup"] label:hover {
            background: #ffe9f4;
            transform: translateX(3px);
        }

        .stRadio [role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
            background-color: #f29bb2;
        }

        /* Input fields */
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            border-radius: 12px;
            border: 2px solid #ffe4f2;
            background: #fff7f2;
            color: #2c1735;
        }

        .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
            border-color: #f29bb2;
            box-shadow: 0 0 0 1px #f29bb2;
        }

        /* Dataframes */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
        }

        /* Expanders */
        .streamlit-expanderHeader {
            background: #ffe9f4;
            border-radius: 12px;
            color: #2c1735;
            font-weight: 600;
        }

        .streamlit-expanderHeader:hover {
            background: #ffd4eb;
        }

        /* Success/Error/Warning boxes */
        .stSuccess {
            background: #e8f7f0;
            border-left: 4px solid #a6e3cf;
            border-radius: 8px;
        }

        .stError {
            background: #ffe9f4;
            border-left: 4px solid #f29bb2;
            border-radius: 8px;
        }

        .stWarning {
            background: #fff3e6;
            border-left: 4px solid #ffd4a3;
            border-radius: 8px;
        }

        .stInfo {
            background: #ffe4f2;
            border-left: 4px solid #f29bb2;
            border-radius: 8px;
        }

        /* Dividers */
        hr {
            border-color: rgba(242, 155, 178, 0.2);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_page_header(title, subtitle=""):
    """Render a styled page header"""
    st.markdown(f'<div class="ohh-crumbs-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="ohh-crumbs-subtitle">{subtitle}</div>', unsafe_allow_html=True)
    st.write("")  # spacer

def render_card(content, dark=False):
    """Render a styled card"""
    card_class = "oc-card dark" if dark else "oc-card"
    st.markdown(f'<div class="{card_class}">{content}</div>', unsafe_allow_html=True)

def render_pill(text, style="success"):
    """Render a styled pill badge"""
    return f'<span class="oc-pill {style}">{text}</span>'
