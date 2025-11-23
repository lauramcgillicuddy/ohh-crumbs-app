import streamlit as st
from database import get_session, close_session
from models import Recipe, Ingredient, RecipeItem, DailyUsage, ProductionBatch
from datetime import datetime, timedelta
from sqlalchemy import func
import pandas as pd
from styling import inject_custom_css, render_page_header

def deduct_ingredients_for_production(session, recipe, quantity_produced):
    """
    Deduct ingredients from inventory when a batch is produced
    Returns list of ingredients updated
    """
    ingredients_updated = []

    for recipe_item in recipe.recipe_items:
        ingredient = recipe_item.ingredient
        quantity_needed = recipe_item.quantity * quantity_produced

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

    return ingredients_updated

def show_production_log():
    inject_custom_css()

    render_page_header("🍰 Production Log", "TRACK WHAT YOU MAKE")

    session = get_session()

    try:
        tab1, tab2 = st.tabs(["📝 Log Production", "📊 Production History"])

        with tab1:
            st.subheader("Record Today's Production")
            st.info("💡 **Important:** Log what you MAKE here, not what you SELL. This deducts ingredients from inventory when you produce batches!")

            # Get all recipes
            recipes = session.query(Recipe).order_by(Recipe.name).all()

            if not recipes:
                st.warning("No recipes available. Please add recipes first in the Recipes page!")
                return

            st.markdown("---")

            # Production date selector
            production_date = st.date_input(
                "Production Date",
                value=datetime.now().date(),
                help="When did you make this batch?"
            )

            st.markdown("### 🎂 What Did You Make Today?")

            # Initialize production log in session state
            if 'production_log' not in st.session_state:
                st.session_state['production_log'] = []

            # Add batch section
            with st.expander("➕ Add Batch", expanded=True):
                col_recipe, col_qty, col_add = st.columns([3, 2, 1])

                with col_recipe:
                    recipe_options = {r.name: r for r in recipes}
                    selected_recipe_name = st.selectbox(
                        "Recipe",
                        options=list(recipe_options.keys()),
                        key="production_recipe"
                    )
                    selected_recipe = recipe_options[selected_recipe_name]

                with col_qty:
                    quantity = st.number_input(
                        "Quantity Made",
                        min_value=0.1,
                        value=1.0,
                        step=0.5,
                        help="How many servings/items did you make?",
                        key="production_quantity"
                    )

                with col_add:
                    st.write("")  # Spacing
                    st.write("")  # Spacing
                    if st.button("➕ Add Batch", use_container_width=True):
                        # Check if this recipe is already in today's log
                        existing_batch = next(
                            (item for item in st.session_state['production_log']
                             if item['recipe_id'] == selected_recipe.id),
                            None
                        )

                        if existing_batch:
                            # Update quantity
                            existing_batch['quantity'] += quantity
                            st.success(f"Updated quantity for {selected_recipe.name}")
                        else:
                            # Add new batch
                            st.session_state['production_log'].append({
                                'recipe_id': selected_recipe.id,
                                'recipe_name': selected_recipe.name,
                                'quantity': quantity
                            })
                            st.success(f"Added {selected_recipe.name} to production log")
                        st.rerun()

            # Display current production log
            if st.session_state['production_log']:
                st.markdown("### 📋 Today's Production")

                total_batches = 0
                items_to_remove = []

                for idx, batch in enumerate(st.session_state['production_log']):
                    col_recipe, col_qty, col_remove = st.columns([3, 2, 1])

                    with col_recipe:
                        st.write(f"**{batch['recipe_name']}**")

                    with col_qty:
                        st.write(f"{batch['quantity']} servings/items")
                        total_batches += batch['quantity']

                    with col_remove:
                        if st.button("🗑️", key=f"remove_batch_{idx}"):
                            items_to_remove.append(idx)

                # Remove items marked for deletion
                for idx in sorted(items_to_remove, reverse=True):
                    st.session_state['production_log'].pop(idx)
                    st.rerun()

                st.markdown("---")
                st.markdown(f"### **Total: {total_batches:.1f} items to be logged**")
                st.markdown("---")

                # Notes field
                production_notes = st.text_area(
                    "Production Notes (optional)",
                    placeholder="e.g., Made extra brownies for weekend rush, used up last of the chocolate chips",
                    key="production_notes"
                )

                # Save production buttons
                col_save, col_cancel = st.columns([1, 1])

                with col_save:
                    if st.button("✅ Log Production & Deduct Ingredients", type="primary", use_container_width=True):
                        try:
                            total_ingredients_updated = []
                            batches_saved = 0

                            for batch in st.session_state['production_log']:
                                recipe = session.query(Recipe).get(batch['recipe_id'])

                                if recipe:
                                    # Calculate expected cost based on recipe
                                    from utils import calculate_profit_margin
                                    expected_cost_per_unit, _, _ = calculate_profit_margin(session, recipe.id)
                                    expected_total_cost = expected_cost_per_unit * batch['quantity']

                                    # Calculate actual cost (sum of current ingredient costs)
                                    actual_total_cost = 0.0
                                    for recipe_item in recipe.recipe_items:
                                        ingredient = recipe_item.ingredient
                                        quantity_needed = recipe_item.quantity * batch['quantity']
                                        actual_total_cost += quantity_needed * ingredient.cost_per_unit

                                    # Create production batch record
                                    new_batch = ProductionBatch(
                                        recipe_id=recipe.id,
                                        quantity_produced=batch['quantity'],
                                        production_date=datetime.combine(production_date, datetime.min.time()),
                                        notes=production_notes if production_notes else None,
                                        expected_cost=expected_total_cost,
                                        actual_cost=actual_total_cost
                                    )
                                    session.add(new_batch)

                                    # Deduct ingredients
                                    ingredients_updated = deduct_ingredients_for_production(
                                        session, recipe, batch['quantity']
                                    )
                                    total_ingredients_updated.extend(ingredients_updated)
                                    batches_saved += 1

                            session.commit()

                            # Show success message with details
                            st.success(f"✅ Logged {batches_saved} batch(es) and updated {len(total_ingredients_updated)} ingredient(s)!")

                            # Show ingredient deductions
                            with st.expander("📦 Ingredients Deducted"):
                                for ing in total_ingredients_updated:
                                    st.write(f"**{ing['name']}**: Used {ing['used']:.2f} {ing['unit']} " +
                                           f"(Stock: {ing['old_stock']:.2f} → {ing['new_stock']:.2f} {ing['unit']})")

                            # Clear production log
                            st.session_state['production_log'] = []
                            st.rerun()

                        except Exception as e:
                            session.rollback()
                            st.error(f"Error logging production: {str(e)}")

                with col_cancel:
                    if st.button("🗑️ Clear Log", use_container_width=True):
                        st.session_state['production_log'] = []
                        st.rerun()
            else:
                st.info("👆 Add batches using the form above to start logging production")

        with tab2:
            st.subheader("Production History")

            # Date range selector
            col_days = st.columns([3, 1])[1]
            with col_days:
                days_back = st.selectbox("Time Period", [7, 14, 30, 60, 90], index=0, key="history_days")

            start_date = datetime.utcnow() - timedelta(days=days_back)

            # Get production batches
            production_batches = session.query(ProductionBatch).filter(
                ProductionBatch.production_date >= start_date
            ).order_by(ProductionBatch.production_date.desc()).all()

            if production_batches:
                # Summary metrics
                total_batches = len(production_batches)
                total_items = sum(batch.quantity_produced for batch in production_batches)

                # Count unique recipes
                unique_recipes = len(set(batch.recipe_id for batch in production_batches))

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Batches", total_batches)

                with col2:
                    st.metric("Items Produced", f"{total_items:.0f}")

                with col3:
                    st.metric("Recipes Made", unique_recipes)

                # Batch Costing Comparison (if we have cost data)
                batches_with_costs = [b for b in production_batches if b.expected_cost and b.actual_cost]

                if batches_with_costs:
                    st.markdown("---")
                    st.subheader("💰 Batch Costing Analysis")

                    total_expected = sum(b.expected_cost for b in batches_with_costs)
                    total_actual = sum(b.actual_cost for b in batches_with_costs)
                    variance = total_actual - total_expected
                    variance_pct = (variance / total_expected * 100) if total_expected > 0 else 0

                    col_exp, col_act, col_var = st.columns(3)

                    with col_exp:
                        st.metric("Expected Cost", f"£{total_expected:.2f}")

                    with col_act:
                        st.metric("Actual Cost", f"£{total_actual:.2f}")

                    with col_var:
                        variance_label = "Over Budget" if variance > 0 else "Under Budget"
                        st.metric(variance_label, f"£{abs(variance):.2f}", delta=f"{variance_pct:+.1f}%")

                    # Explanation
                    if abs(variance_pct) > 10:
                        st.warning(f"⚠️ Cost variance of {variance_pct:.1f}% - ingredient prices may have changed!")
                    elif abs(variance_pct) > 5:
                        st.info(f"💡 Small cost variance of {variance_pct:.1f}% - monitor ingredient prices")
                    else:
                        st.success(f"✅ Cost variance under 5% - on track!")

                st.markdown("---")

                # Group by date
                batches_by_date = {}
                for batch in production_batches:
                    date_key = batch.production_date.date()
                    if date_key not in batches_by_date:
                        batches_by_date[date_key] = []
                    batches_by_date[date_key].append(batch)

                # Display production history
                for date_key in sorted(batches_by_date.keys(), reverse=True):
                    date_batches = batches_by_date[date_key]
                    total_for_day = sum(b.quantity_produced for b in date_batches)

                    with st.expander(f"📅 {date_key.strftime('%A, %B %d, %Y')} - {total_for_day:.0f} items"):
                        for batch in date_batches:
                            recipe = session.query(Recipe).get(batch.recipe_id)

                            if recipe:
                                col_recipe, col_qty, col_delete = st.columns([3, 1, 1])

                                with col_recipe:
                                    st.write(f"**{recipe.name}**")
                                    if batch.notes:
                                        st.caption(f"📝 {batch.notes}")

                                with col_qty:
                                    st.write(f"{batch.quantity_produced:.1f} items")

                                with col_delete:
                                    if st.button("🗑️", key=f"delete_batch_{batch.id}", help="Delete this batch"):
                                        try:
                                            # Rollback any pending changes first
                                            session.rollback()

                                            # Re-fetch the batch after rollback
                                            batch = session.query(ProductionBatch).get(batch.id)

                                            # Warn about stock already being deducted
                                            st.warning("⚠️ Stock was already deducted when this batch was created. Deleting will NOT restore ingredient stock!")

                                            # Add confirmation
                                            if st.button("⚠️ Yes, Delete", key=f"confirm_delete_batch_{batch.id}", type="primary"):
                                                session.delete(batch)
                                                session.commit()
                                                st.success("✅ Batch deleted")
                                                st.rerun()

                                        except Exception as e:
                                            session.rollback()
                                            st.error(f"Error deleting batch: {str(e)}")

                                st.markdown("---")

                st.markdown("---")

                # Production summary chart
                st.subheader("📊 Production by Recipe")

                # Aggregate by recipe
                recipe_totals = {}
                for batch in production_batches:
                    recipe = session.query(Recipe).get(batch.recipe_id)
                    if recipe:
                        if recipe.name not in recipe_totals:
                            recipe_totals[recipe.name] = 0
                        recipe_totals[recipe.name] += batch.quantity_produced

                if recipe_totals:
                    df = pd.DataFrame({
                        'Recipe': list(recipe_totals.keys()),
                        'Quantity Produced': list(recipe_totals.values())
                    }).sort_values('Quantity Produced', ascending=True)

                    st.bar_chart(df.set_index('Recipe'))

                    st.markdown("---")
                    st.subheader("📋 Top Recipes")
                    top_recipes = sorted(recipe_totals.items(), key=lambda x: x[1], reverse=True)[:5]

                    for idx, (recipe_name, quantity) in enumerate(top_recipes, 1):
                        st.write(f"{idx}. **{recipe_name}**: {quantity:.1f} items")
            else:
                st.info("No production logged yet. Start logging what you make in the 'Log Production' tab!")

    finally:
        close_session(session)

if __name__ == "__main__":
    show_production_log()
