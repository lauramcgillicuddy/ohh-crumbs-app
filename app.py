import os
import streamlit as st

st.set_page_config(page_title="Ohh Crumbs", page_icon="🍰", layout="wide")

# --- Initialize database tables ---
from database import init_db
init_db()

# --- Import your pages (top-level .py files) ---
import dashboard, ingredients, inventory, inventory_alerts, profit_analysis, recipes, suppliers, square_setup, production_log
import waste_tracking, equipment_maintenance, expiry_tracking, production_planner, cash_flow

st.sidebar.title("🍰 Ohh Crumbs")
page = st.sidebar.radio(
    "Go to",
    [
        "🏠 Dashboard",
        "🥖 Ingredients",
        "📖 Recipes",
        "🍰 Production Log",
        "📅 Production Planner",
        "📊 Inventory Tracking",
        "⏰ Expiry & FIFO",
        "🔔 Inventory Alerts",
        "🗑️ Waste Tracking",
        "💰 Profit Analysis",
        "💸 Cash Flow Forecast",
        "🔧 Equipment Maintenance",
        "📦 Suppliers",
        "🔗 Square Setup"
    ],
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
elif page.startswith("🍰"): call(production_log, "show_production_log")
elif page.startswith("📅"): call(production_planner, "show_production_planner")
elif page.startswith("📊"): call(inventory, "show_inventory")
elif page.startswith("⏰"): call(expiry_tracking, "show_expiry_tracking")
elif page.startswith("🔔"): call(inventory_alerts, "show_inventory_alerts")
elif page.startswith("🗑️"): call(waste_tracking, "show_waste_tracking")
elif page.startswith("💰"): call(profit_analysis, "show_profit_analysis")
elif page.startswith("💸"): call(cash_flow, "show_cash_flow")
elif page.startswith("🔧"): call(equipment_maintenance, "show_equipment_maintenance")
elif page.startswith("📦"): call(suppliers, "show_suppliers")
elif page.startswith("🔗"): call(square_setup, "show_square_setup")

st.sidebar.markdown("---")
st.sidebar.caption("Add to Home Screen on iPhone for an app-like icon.")
