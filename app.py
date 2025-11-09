import streamlit as st
from auth_config import setup_authentication
from database import init_db
import os

st.set_page_config(
    page_title="Ohh Crumbs - Bakery Management",
    page_icon="🍰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Force light theme
st.markdown("""
    <style>
        [data-testid="stAppViewContainer"] {
            background-color: #FFF5F7 !important;
        }

        [data-testid="stHeader"] {
            background-color: transparent !important;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        /* Main color palette */
        :root {
            --pink-light: #FFF5F7;
            --pink-medium: #FFE5EC;
            --pink-accent: #FFB3C6;
            --gold: #D4AF37;
            --gold-light: #F4E4C1;
            --charcoal: #1a1a1a;
            --text-dark: #2D2D2D;
            --white: #FFFFFF;
        }

        /* Main content area */
        .main {
            padding: 1rem;
            background-color: var(--pink-light);
        }

        /* Text color overrides for visibility */
        .main * {
            color: #2D2D2D;
        }

        /* Login form specific */
        [data-testid="stForm"] label {
            color: #1a1a1a !important;
            font-weight: 600;
        }

        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--pink-medium) 0%, var(--white) 100%);
            border-right: 2px solid var(--gold);
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
            color: var(--charcoal);
            font-weight: 700;
        }

        /* Dashboard - Ohh Crumbs Brand Style */
        h1 {
            font-family: 'Brush Script MT', 'Lucida Handwriting', cursive !important;
            color: #C9A882 !important;
            text-align: center;
            font-size: 3rem !important;
            font-weight: normal !important;
            letter-spacing: 2px !important;
            margin: 2rem 0 !important;
            background: none !important;
            -webkit-text-fill-color: #C9A882 !important;
        }

        h2, h3 {
            font-family: 'Garamond', 'Georgia', serif !important;
            color: #C9A882 !important;
            letter-spacing: 1px !important;
        }

        label, p, span, div {
            color: #2D2D2D !important;
        }

        /* Select box */
        [data-testid="stSelectbox"] {
            background: #FFF5F5;
            border-radius: 15px;
            padding: 0.5rem;
            border: 2px solid #F5E6D3;
        }

        select {
            background-color: #FFFFFF !important;
            color: #8B7355 !important;
            border: 2px solid #F5E6D3 !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
            padding: 0.75rem !important;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
            background: linear-gradient(135deg, #FFFFFF 0%, #FFF5F5 100%) !important;
            padding: 2rem 1.5rem !important;
            border-radius: 25px !important;
            box-shadow: 0 4px 15px rgba(201, 168, 130, 0.15) !important;
            border: 3px solid #F5E6D3 !important;
            border-left: 6px solid #C9A882 !important;
            transition: transform 0.3s ease, box-shadow 0.3s ease !important;
        }

        [data-testid="stMetric"]:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 6px 20px rgba(201, 168, 130, 0.25) !important;
        }

        [data-testid="stMetric"] label {
            color: #8B7355 !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
            font-family: 'Garamond', 'Georgia', serif !important;
        }

        [data-testid="stMetricValue"] {
            color: #5D4E37 !important;
            font-weight: 700 !important;
            font-size: 2rem !important;
        }

        /* Buttons */
        button[kind="primary"], 
        button[type="submit"],
        .stButton > button,
        form button,
        .stButton button,
        button {
            background: linear-gradient(135deg, #FFB3C6 0%, #FF8FAB 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            padding: 0.75rem 1.5rem !important;
            box-shadow: 0 4px 8px rgba(255, 179, 198, 0.3) !important;
            transition: all 0.3s ease !important;
            width: 100%;
        }

        button:hover {
            background: linear-gradient(135deg, #FF8FAB 0%, #FF6B94 100%) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 12px rgba(255, 179, 198, 0.4) !important;
        }

                /* Password toggle - make it smaller and prettier */
        button[kind="icon"] {
            background: transparent !important;
            color: var(--pink-accent) !important;
            width: auto !important;
            padding: 0.3rem !important;
            min-width: 1rem !important;
            height: 1rem !important;
        }
        
        button[kind="icon"]:hover {
            background: var(--pink-light) !important;
            color: var(--gold) !important;
        }
        
        /* Make the icon itself smaller */
        button[kind="icon"] svg {
            width: 10px !important;
            height: 10px !important;
        }
        
        /* Input fields */
        input, textarea, select {
            border-radius: 8px;
            border: 2px solid var(--pink-accent) !important;
            background-color: var(--white) !important;
            color: var(--charcoal) !important;
            padding: 0.75rem !important;  /* ← This controls the size! */
        }

        input:focus, textarea:focus, select:focus {
            border-color: var(--gold) !important;
            box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.2) !important;
            background-color: var(--white) !important;
        }

        /* Expanders */
        div[data-testid="stExpander"] {
            background-color: var(--white);
            border: 2px solid var(--pink-medium);
            border-radius: 12px;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(255, 179, 198, 0.15);
        }

        div[data-testid="stExpander"]:hover {
            border-color: var(--pink-accent);
        }

        /* Alerts */
        .stAlert {
            border-radius: 10px;
            border-left: 4px solid var(--gold);
        }

        /* Tables */
        [data-testid="stDataFrame"] {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        /* Dividers */
        hr {
            border-color: var(--pink-accent);
        }

        /* Radio buttons (navigation) */
        [data-testid="stRadio"] label {
            font-weight: 500;
            padding: 0.5rem;
            border-radius: 8px;
            transition: all 0.2s ease;
        }

        [data-testid="stRadio"] label:hover {
            background-color: var(--pink-light);
        }

        /* Mobile responsive */
        @media (max-width: 768px) {
            .main {
                padding: 0.5rem;
            }
            h1 {
                font-size: 2rem !important;
            }
            h2 {
                font-size: 1.4rem !important;
            }
            h3 {
                font-size: 1.2rem !important;
            }
            [data-testid="stMetric"] {
                padding: 1rem !important;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.5rem !important;
            }
        }
    </style>
""", unsafe_allow_html=True)

init_db()

authenticator = setup_authentication()

authenticator.login(location='main')

if st.session_state.get('authentication_status') is False:
    st.error('Username/Password is incorrect')

elif st.session_state.get('authentication_status') is None:
    st.warning('Please enter your username and password')
    with st.expander("ℹ️ First time logging in?"):
        st.write("Default username: `admin`")
        st.write("The password is set via the `ADMIN_PASSWORD` environment variable.")
        st.write("Contact your administrator or check Replit Secrets (🔒) for the password.")

elif st.session_state.get('authentication_status'):
    with st.sidebar:
        st.title("🍰 Ohh Crumbs")
        st.write(f"Welcome, **{st.session_state.get('name')}**!")
        
        authenticator.logout('Logout', 'sidebar')
        
        st.divider()
        
        page = st.radio(
            "Navigation",
            [
                "📊 Dashboard",
                "🥖 Ingredients",
                "📖 Recipes",
                "📦 Suppliers",
                "💰 Profit Analysis",
                "🔔 Inventory Alerts",
                "🔗 Square Setup"
            ],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.write("### Quick Stats")
        
        from database import get_session, close_session
        from models import Ingredient, Recipe, SalesCache
        
        session = get_session()
        
        try:
            ingredient_count = session.query(Ingredient).count()
            recipe_count = session.query(Recipe).count()
            sales_count = session.query(SalesCache).count()
            
            st.metric("Ingredients", ingredient_count)
            st.metric("Recipes", recipe_count)
            st.metric("Sales Records", sales_count)
        finally:
            close_session(session)
        
        st.divider()
        
        st.caption("Ohh Crumbs Bakery Management v1.0")
    
    if page == "📊 Dashboard":
        from pages.dashboard import show_dashboard
        show_dashboard()
    
    elif page == "🥖 Ingredients":
        from pages.ingredients import show_ingredients
        show_ingredients()
    
    elif page == "📖 Recipes":
        from pages.recipes import show_recipes
        show_recipes()
    
    elif page == "📦 Suppliers":
        from pages.suppliers import show_suppliers
        show_suppliers()
    
    elif page == "💰 Profit Analysis":
        from pages.profit_analysis import show_profit_analysis
        show_profit_analysis()
    
    elif page == "🔔 Inventory Alerts":
        from pages.inventory_alerts import show_inventory_alerts
        show_inventory_alerts()
    
    elif page == "🔗 Square Setup":
        from pages.square_setup import show_square_setup
        show_square_setup()
