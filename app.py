import os
import streamlit as st

st.set_page_config(page_title="Ohh Crumbs", page_icon="🍰", layout="wide")

# --- Simple optional password gate via Streamlit Secrets ---
def gate():
    want_auth = bool(st.secrets.get("ADMIN_PASSWORD", ""))
    if not want_auth or st.session_state.get("ok"):
        return True
    with st.sidebar:
        st.subheader("Login")
        pw = st.text_input("Password", type="password")
        if st.button("Enter"):
            if pw == st.secrets["ADMIN_PASSWORD"]:
                st.session_state.ok = True
                st.rerun()
            else:
                st.error("Wrong password")
    st.stop()
gate()

# --- Import your pages (top-level .py files) ---
import dashboard, ingredients, inventory_alerts, profit_analysis, recipes, suppliers, square_setup

st.sidebar.title("🍰 Ohh Crumbs")
page = st.sidebar.radio(
    "Go to",
    ["🏠 Dashboard","🥖 Ingredients","📖 Recipes","🔔 Inventory Alerts","💰 Profit Analysis","📦 Suppliers","🔗 Square Setup"],
    label_visibility="collapsed",
)

def call(mod, func):
    if hasattr(mod, func):
        getattr(mod, func)()
    else:
        st.warning(f"`{mod.__name__}.{func}()` not found.")

if page.startswith("🏠"): call(dashboard, "show_dashboard")
elif page.startswith("🥖"): call(ingredients, "show_ingredients")
elif page.startswith("📖"): call(recipes, "show_recipes")
elif page.startswith("🔔"): call(inventory_alerts, "show_inventory_alerts")
elif page.startswith("💰"): call(profit_analysis, "show_profit_analysis")
elif page.startswith("📦"): call(suppliers, "show_suppliers")
elif page.startswith("🔗"): call(square_setup, "show_square_setup")

st.sidebar.markdown("---")
st.sidebar.caption("Add to Home Screen on iPhone for an app-like icon.")
