import streamlit as st

# ---------------------------------------------------------------------------
# Brand palette
# Cool, analogous blue-violet range sampled from the Ohh Crumbs brand board.
# Anchor on SLATE; use PLUM / PERIWINKLE / SKY as secondary accents.
# ---------------------------------------------------------------------------
PALETTE = {
    "lilac": "#D8C9E1",       # light lavender
    "periwinkle": "#9093B6",  # muted blue-violet
    "slate": "#566385",       # deep slate navy — primary anchor
    "soft": "#AEB3CF",        # light blue-grey
    "plum": "#7D7BA4",        # muted purple
    "sky": "#C0D5E5",         # pale blue
    # Supporting neutrals
    "ink": "#2C3144",         # primary text
    "muted": "#6B7088",       # secondary text
    "surface": "#FFFFFF",     # card / chart surface
    "bg": "#F7F8FB",          # app background
    "panel": "#EEF0F6",       # sidebar / panel
    "grid": "#E7E9F2",        # recessive chart grid
    "border": "#E2E5EF",      # hairline borders
}

# Categorical charts: lead with the most lightness-separated members and pair
# with direct labels (the brand palette is analogous, so colour alone is never
# the only cue). Ordered dark -> light for maximum separation.
CHART_SEQUENCE = ["#566385", "#7D7BA4", "#C0D5E5", "#D8C9E1", "#9093B6", "#AEB3CF"]

# Magnitude / heat: one hue, light -> dark (replaces the old rainbow scale).
SEQUENTIAL_SCALE = [[0.0, "#EEF0F6"], [0.5, "#9093B6"], [1.0, "#3E4A66"]]

FONT_STACK = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"


def style_fig(fig, legend=False):
    """Apply the sleek brand theme to a Plotly figure.

    Transparent surface, ink text, recessive grid, brand colourway. Call this
    on any chart instead of hand-setting pink backgrounds.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=PALETTE["ink"], family=FONT_STACK, size=13),
        title_font=dict(color=PALETTE["ink"], family=FONT_STACK, size=16),
        colorway=CHART_SEQUENCE,
        margin=dict(t=56, r=16, b=40, l=56),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(color=PALETTE["muted"], size=12),
        ),
        hoverlabel=dict(bgcolor=PALETTE["surface"], font_size=12,
                        font_family=FONT_STACK, bordercolor=PALETTE["border"]),
    )
    fig.update_xaxes(gridcolor=PALETTE["grid"], zeroline=False,
                     linecolor=PALETTE["border"], tickfont=dict(color=PALETTE["muted"]),
                     title_font=dict(color=PALETTE["muted"], size=12))
    fig.update_yaxes(gridcolor=PALETTE["grid"], zeroline=False,
                     linecolor=PALETTE["border"], tickfont=dict(color=PALETTE["muted"]),
                     title_font=dict(color=PALETTE["muted"], size=12))
    return fig


def inject_custom_css():
    """Inject the sleek Ohh Crumbs theme (shared across every page)."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"], .stApp, [data-testid="stSidebar"] {
            font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
        }

        .stApp { background: #F7F8FB; }

        /* ---- Page header ---------------------------------------------------- */
        .oc-header { margin: 0.2rem 0 1.1rem 0; }
        .oc-header .oc-title {
            font-size: 1.95rem;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: #2C3144;
            line-height: 1.15;
            margin: 0;
        }
        .oc-header .oc-subtitle {
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #8A8FA6;
            margin-top: 0.25rem;
        }
        .oc-header .oc-rule {
            height: 3px; width: 48px; border-radius: 3px;
            background: #566385; margin-top: 0.7rem;
        }

        /* ---- Cards & pills -------------------------------------------------- */
        .oc-card {
            border-radius: 14px;
            padding: 1.2rem 1.35rem;
            background: #FFFFFF;
            box-shadow: 0 6px 20px rgba(44, 49, 68, 0.05);
            border: 1px solid #E2E5EF;
            margin-bottom: 1rem;
        }
        .oc-card.dark { background: #EEF0F6; }
        .oc-card h3 {
            margin-bottom: 0.25rem; font-size: 1.05rem;
            font-weight: 600; color: #2C3144;
        }
        .oc-pill {
            display: inline-flex; align-items: center; gap: 0.4rem;
            padding: 0.2rem 0.7rem; border-radius: 999px;
            font-size: 0.75rem; font-weight: 600;
            background: #EEF0F6; color: #566385;
        }
        .oc-pill.pink    { background: #E7E4F0; color: #7D7BA4; }
        .oc-pill.warning { background: #F3ECDC; color: #7A5B2E; }
        .oc-pill.success { background: #DEEAE2; color: #2F5D4A; }

        /* ---- Buttons -------------------------------------------------------- */
        .stButton>button {
            border-radius: 10px; border: 1px solid #566385;
            padding: 0.45rem 1.2rem; font-weight: 600;
            background: #566385; color: #FFFFFF;
            box-shadow: 0 4px 12px rgba(86, 99, 133, 0.22);
            transition: all 0.18s ease;
        }
        .stButton>button:hover {
            background: #45506d; border-color: #45506d;
            transform: translateY(-1px);
            box-shadow: 0 6px 16px rgba(86, 99, 133, 0.3);
        }

        /* ---- Tabs ----------------------------------------------------------- */
        .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px; padding: 0.35rem 0.9rem;
            background: #EEF0F6; color: #6B7088; font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background: #566385 !important; color: #FFFFFF !important; font-weight: 600;
        }

        /* ---- Metrics -------------------------------------------------------- */
        [data-testid="stMetricValue"] { font-size: 1.9rem; font-weight: 700; color: #2C3144; }
        [data-testid="stMetricLabel"] { font-size: 0.78rem; color: #6B7088; font-weight: 600;
            letter-spacing: 0.02em; text-transform: uppercase; }
        [data-testid="stMetricDelta"] { font-size: 0.85rem; }

        /* ---- Sidebar -------------------------------------------------------- */
        [data-testid="stSidebar"] { background: #EEF0F6; border-right: 1px solid #E2E5EF; }
        [data-testid="stSidebar"] h1 { color: #2C3144; font-weight: 700; letter-spacing: -0.01em; }

        .stRadio > label { background: transparent !important; }
        .stRadio [role="radiogroup"] label {
            padding: 0.5rem 0.9rem; border-radius: 10px;
            background: #FFFFFF; margin-bottom: 0.3rem;
            border: 1px solid transparent; transition: all 0.18s ease;
        }
        .stRadio [role="radiogroup"] label:hover {
            background: #FFFFFF; border-color: #CFD5E6; transform: translateX(2px);
        }
        .stRadio [role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
            background-color: #566385;
        }

        /* ---- Inputs --------------------------------------------------------- */
        .stTextInput input, .stNumberInput input, .stSelectbox select {
            border-radius: 10px; border: 1px solid #D5DAE8;
            background: #FFFFFF; color: #2C3144;
        }
        .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
            border-color: #566385; box-shadow: 0 0 0 1px #566385;
        }

        .stDataFrame { border-radius: 10px; overflow: hidden; }

        .streamlit-expanderHeader {
            background: #EEF0F6; border-radius: 10px; color: #2C3144; font-weight: 600;
        }
        .streamlit-expanderHeader:hover { background: #E4E8F2; }

        /* ---- Alert boxes (cool tones) --------------------------------------- */
        .stSuccess { background: #DEEAE2; border-left: 4px solid #5B8F77; border-radius: 8px; }
        .stError   { background: #F2E2E6; border-left: 4px solid #B06A7B; border-radius: 8px; }
        .stWarning { background: #F3ECDC; border-left: 4px solid #C79A52; border-radius: 8px; }
        .stInfo    { background: #EEF0F6; border-left: 4px solid #566385; border-radius: 8px; }

        hr { border-color: rgba(86, 99, 133, 0.14); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title, subtitle=""):
    """Render a clean, left-aligned page header with a slate accent rule."""
    sub = f'<div class="oc-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="oc-header">'
        f'<div class="oc-title">{title}</div>'
        f'{sub}'
        f'<div class="oc-rule"></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_card(content, dark=False):
    """Render a styled card."""
    card_class = "oc-card dark" if dark else "oc-card"
    st.markdown(f'<div class="{card_class}">{content}</div>', unsafe_allow_html=True)


def render_pill(text, style="success"):
    """Render a styled pill badge."""
    return f'<span class="oc-pill {style}">{text}</span>'
