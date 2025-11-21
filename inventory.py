import streamlit as st
from database import get_session, close_session
from models import Recipe, Ingredient, RecipeItem, DailyUsage, SalesCache
from square_api import SquareAPI
from styling import inject_custom_css, render_page_header
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import func


def process_square_orders_and_update_inventory(days_back=1):
    """
    Fetch Square orders and update ingredient inventory based on items sold.
    Returns a summary of processed orders.
    """
    session = get_session()
    try:
        square_api = SquareAPI()

        if not square_api.is_configured:
            return {
                'success': False,
                'message': 'Square API not configured',
                'orders_processed': 0,
                'ingredients_updated': []
            }

        # Get orders from Square
        orders = square_api.get_orders(days_back=days_back)

        if not orders:
            return {
                'success': True,
                'message': 'No orders found',
                'orders_processed': 0,
                'ingredients_updated': []
            }

        # Group orders by item name to get total quantities
        item_quantities = {}
        for order in orders:
            item_name = order['item_name']
            quantity = order['quantity']

            if item_name in item_quantities:
                item_quantities[item_name] += quantity
            else:
                item_quantities[item_name] = quantity

        # Process each item and deduct ingredients
        ingredients_updated = []
        orders_processed = 0

        for item_name, total_quantity in item_quantities.items():
            # Find recipe matching this item name
            recipe = session.query(Recipe).filter(
                Recipe.name.ilike(f'%{item_name}%')
            ).first()

            if recipe and recipe.recipe_items:
                orders_processed += 1

                # Deduct ingredients for each unit sold
                for recipe_item in recipe.recipe_items:
                    ingredient = recipe_item.ingredient
                    quantity_needed = recipe_item.quantity * total_quantity

                    # Update stock
                    old_stock = ingredient.current_stock
                    ingredient.current_stock = max(0, ingredient.current_stock - quantity_needed)

                    # Record daily usage
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    daily_usage = session.query(DailyUsage).filter(
                        DailyUsage.ingredient_id == ingredient.id,
                        DailyUsage.date == today
                    ).first()

                    if daily_usage:
                        daily_usage.quantity_used += quantity_needed
                    else:
                        daily_usage = DailyUsage(
                            ingredient_id=ingredient.id,
                            date=today,
                            quantity_used=quantity_needed
                        )
                        session.add(daily_usage)

                    ingredients_updated.append({
                        'name': ingredient.name,
                        'used': quantity_needed,
                        'old_stock': old_stock,
                        'new_stock': ingredient.current_stock,
                        'unit': ingredient.unit
                    })

        session.commit()

        return {
            'success': True,
            'message': f'Processed {orders_processed} unique items from {len(orders)} orders',
            'orders_processed': orders_processed,
            'ingredients_updated': ingredients_updated
        }

    except Exception as e:
        session.rollback()
        return {
            'success': False,
            'message': f'Error: {str(e)}',
            'orders_processed': 0,
            'ingredients_updated': []
        }
    finally:
        close_session(session)


def show_inventory():
    inject_custom_css()
    render_page_header("📦 Inventory Management", "TRACK YOUR INGREDIENT STOCK")

    session = get_session()

    try:
        st.markdown("---")

        # Sync with Square section
        st.subheader("🔄 Sync with Square")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📥 Sync Last 24 Hours", type="primary"):
                with st.spinner("Syncing with Square..."):
                    result = process_square_orders_and_update_inventory(days_back=1)

                    if result['success']:
                        st.success(result['message'])

                        if result['ingredients_updated']:
                            st.write("**Ingredients Updated:**")
                            for ing in result['ingredients_updated']:
                                st.write(f"- {ing['name']}: {ing['old_stock']:.2f} → {ing['new_stock']:.2f} {ing['unit']} (used: {ing['used']:.2f})")
                    else:
                        st.error(result['message'])

        with col2:
            if st.button("📥 Sync Last 7 Days"):
                with st.spinner("Syncing with Square..."):
                    result = process_square_orders_and_update_inventory(days_back=7)

                    if result['success']:
                        st.success(result['message'])
                    else:
                        st.error(result['message'])

        with col3:
            if st.button("📥 Sync Last 30 Days"):
                with st.spinner("Syncing with Square..."):
                    result = process_square_orders_and_update_inventory(days_back=30)

                    if result['success']:
                        st.success(result['message'])
                    else:
                        st.error(result['message'])

        st.markdown("---")

        # Current Stock Levels
        st.subheader("📊 Current Stock Levels")

        ingredients = session.query(Ingredient).order_by(Ingredient.name).all()

        if not ingredients:
            st.info("No ingredients in database. Add ingredients first!")
        else:
            # Create stock level dataframe
            stock_data = []
            for ing in ingredients:
                # Calculate usage in last 7 days
                week_ago = datetime.now() - timedelta(days=7)
                weekly_usage = session.query(DailyUsage).filter(
                    DailyUsage.ingredient_id == ing.id,
                    DailyUsage.date >= week_ago
                ).all()

                total_weekly_usage = sum([usage.quantity_used for usage in weekly_usage])
                avg_daily_usage = total_weekly_usage / 7 if total_weekly_usage > 0 else 0
                days_remaining = ing.current_stock / avg_daily_usage if avg_daily_usage > 0 else 999

                # Determine stock status
                if ing.current_stock <= 0:
                    status = "🔴 Out of Stock"
                elif days_remaining < 3:
                    status = "🟠 Low Stock"
                elif days_remaining < 7:
                    status = "🟡 Moderate"
                else:
                    status = "🟢 Good"

                stock_data.append({
                    'Ingredient': ing.name,
                    'Current Stock': f"{ing.current_stock:.2f} {ing.unit}",
                    'Weekly Usage': f"{total_weekly_usage:.2f} {ing.unit}",
                    'Avg Daily': f"{avg_daily_usage:.2f} {ing.unit}",
                    'Days Left': f"{days_remaining:.1f}" if days_remaining < 999 else "N/A",
                    'Status': status,
                    'Cost/Unit': f"£{ing.cost_per_unit:.2f}"
                })

            df = pd.DataFrame(stock_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Stock alerts
            low_stock = [item for item in stock_data if '🔴' in item['Status'] or '🟠' in item['Status']]

            if low_stock:
                st.warning(f"⚠️ {len(low_stock)} item(s) need attention!")

                with st.expander("View Low Stock Items"):
                    for item in low_stock:
                        st.write(f"**{item['Ingredient']}**: {item['Current Stock']} - {item['Status']}")

        st.markdown("---")

        # Link Square Sales Items to Recipes
        st.subheader("🔗 Link Square Sales Items to Recipes")

        st.info("Match your Square sales items to recipes so ingredient usage can be tracked automatically")

        # Get items from sales history
        sales_items_query = session.query(
            SalesCache.item_name,
            func.sum(SalesCache.quantity).label('total_sold')
        ).group_by(SalesCache.item_name).all()

        sales_items = []
        for item_name, total_sold in sales_items_query:
            if item_name and item_name.strip():
                sales_items.append({
                    'name': item_name,
                    'total_sold': int(total_sold) if total_sold else 0
                })

        recipes = session.query(Recipe).order_by(Recipe.name).all()

        if sales_items and recipes:
            st.write(f"**Found {len(sales_items)} items in sales history**")

            # Show current linkages (by matching names)
            linked_items = []
            for recipe in recipes:
                # Find sales item with matching name
                matching_item = next((item for item in sales_items if item['name'].lower() == recipe.name.lower()), None)
                if matching_item:
                    linked_items.append({
                        'recipe': recipe.name,
                        'sales_item': matching_item['name'],
                        'total_sold': matching_item['total_sold']
                    })

            if linked_items:
                with st.expander(f"✅ Currently Linked ({len(linked_items)})", expanded=False):
                    for link in linked_items:
                        st.write(f"- **{link['recipe']}** → {link['sales_item']} ({link['total_sold']} sold)")

            # Show unlinked items
            linked_names = {link['recipe'].lower() for link in linked_items}
            unlinked_sales = [item for item in sales_items if item['name'].lower() not in linked_names]

            if unlinked_sales:
                st.write("---")
                st.write(f"**⚠️ {len(unlinked_sales)} Sales Items Not Linked to Recipes:**")
                st.info("These items are selling but don't have recipes in your system. Create recipes for them to track ingredient usage!")

                # Sort by total sold
                sorted_unlinked = sorted(unlinked_sales, key=lambda x: x['total_sold'], reverse=True)

                with st.expander("📋 View Unlinked Sales Items", expanded=True):
                    for item in sorted_unlinked[:15]:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{item['name']}**")
                        with col2:
                            st.write(f"{item['total_sold']} sold")

                    if len(sorted_unlinked) > 15:
                        st.caption(f"Showing top 15 of {len(sorted_unlinked)} items")

                st.write("💡 **Tip:** Go to the Recipes page → Add Recipe tab to create recipes for these items!")
        else:
            if not sales_items:
                st.warning("No sales data found. Sales history will appear here once you have Square transactions.")
            if not recipes:
                st.warning("No recipes in database. Create recipes first!")

        st.markdown("---")

        # Manual Stock Adjustment
        st.subheader("✏️ Manual Stock Adjustment")

        if ingredients:
            with st.form("adjust_stock"):
                selected_ingredient_id = st.selectbox(
                    "Select Ingredient",
                    options=[ing.id for ing in ingredients],
                    format_func=lambda x: next(f"{ing.name} (Current: {ing.current_stock:.2f} {ing.unit})" for ing in ingredients if ing.id == x)
                )

                col1, col2 = st.columns(2)

                with col1:
                    adjustment_type = st.radio("Adjustment Type", ["Add Stock", "Remove Stock", "Set Stock"])

                with col2:
                    adjustment_amount = st.number_input("Amount", min_value=0.0, step=0.1, value=0.0)

                adjustment_note = st.text_input("Note (optional)", placeholder="e.g., Delivery received, Wastage, etc.")

                if st.form_submit_button("Update Stock"):
                    ingredient = session.query(Ingredient).get(selected_ingredient_id)
                    old_stock = ingredient.current_stock

                    if adjustment_type == "Add Stock":
                        ingredient.current_stock += adjustment_amount
                    elif adjustment_type == "Remove Stock":
                        ingredient.current_stock = max(0, ingredient.current_stock - adjustment_amount)
                    else:  # Set Stock
                        ingredient.current_stock = adjustment_amount

                    session.commit()

                    st.success(f"✅ Updated {ingredient.name}: {old_stock:.2f} → {ingredient.current_stock:.2f} {ingredient.unit}")
                    st.rerun()

    finally:
        close_session(session)
