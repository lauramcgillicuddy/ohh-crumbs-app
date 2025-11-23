"""
Expiry Date Tracking & FIFO Management
Track ingredient batches with expiry dates and get alerts for items expiring soon
"""

import streamlit as st
from database import get_session, close_session
from models import IngredientBatch, Ingredient, SupplierOrder
from styling import inject_custom_css, render_page_header
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px


def show_expiry_tracking():
    inject_custom_css()
    render_page_header("⏰ Expiry & FIFO Tracking", "PREVENT WASTE, USE OLDEST FIRST")

    session = get_session()

    try:
        tab1, tab2, tab3, tab4 = st.tabs(["⚠️ Expiry Alerts", "➕ Log Batch", "📦 Batch Inventory", "📊 Analytics"])

        with tab1:
            st.subheader("Expiring Soon")

            # Alert thresholds
            col_days1, col_days2 = st.columns(2)

            with col_days1:
                critical_days = st.slider("Critical (days)", 1, 7, 3)

            with col_days2:
                warning_days = st.slider("Warning (days)", 3, 14, 7)

            st.markdown("---")

            today = datetime.now()
            critical_date = today + timedelta(days=critical_days)
            warning_date = today + timedelta(days=warning_days)

            # Get expiring batches
            critical_batches = session.query(IngredientBatch).filter(
                IngredientBatch.is_active == True,
                IngredientBatch.expiry_date.isnot(None),
                IngredientBatch.expiry_date <= critical_date,
                IngredientBatch.quantity_remaining > 0
            ).order_by(IngredientBatch.expiry_date).all()

            warning_batches = session.query(IngredientBatch).filter(
                IngredientBatch.is_active == True,
                IngredientBatch.expiry_date.isnot(None),
                IngredientBatch.expiry_date > critical_date,
                IngredientBatch.expiry_date <= warning_date,
                IngredientBatch.quantity_remaining > 0
            ).order_by(IngredientBatch.expiry_date).all()

            # Critical alerts
            if critical_batches:
                st.error(f"🚨 **CRITICAL:** {len(critical_batches)} batch(es) expiring within {critical_days} days!")

                for batch in critical_batches:
                    ingredient = session.query(Ingredient).get(batch.ingredient_id)
                    days_left = (batch.expiry_date - today).days

                    with st.expander(f"🚨 {ingredient.name} - EXPIRES IN {days_left} DAYS"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Ingredient:** {ingredient.name}")
                            st.write(f"**Remaining:** {batch.quantity_remaining:.2f} {batch.unit}")
                            st.write(f"**Expiry Date:** {batch.expiry_date.strftime('%Y-%m-%d')}")
                            st.write(f"**Days Left:** {days_left}")

                        with col2:
                            if batch.batch_number:
                                st.write(f"**Batch #:** {batch.batch_number}")
                            st.write(f"**Received:** {batch.received_date.strftime('%Y-%m-%d')}")
                            cost_remaining = batch.quantity_remaining * batch.cost_per_unit
                            st.write(f"**Value:** £{cost_remaining:.2f}")

                        # Action buttons
                        col_use, col_waste = st.columns(2)

                        with col_use:
                            if st.button("✅ Mark as Used", key=f"use_critical_{batch.id}"):
                                batch.quantity_remaining = 0
                                batch.is_active = False
                                session.commit()
                                st.success("Marked as fully used!")
                                st.rerun()

                        with col_waste:
                            if st.button("🗑️ Mark as Wasted", key=f"waste_critical_{batch.id}"):
                                # Create wastage log
                                from models import WastageLog
                                waste = WastageLog(
                                    ingredient_id=ingredient.id,
                                    quantity=batch.quantity_remaining,
                                    unit=batch.unit,
                                    reason="Expired",
                                    cost=batch.quantity_remaining * batch.cost_per_unit,
                                    wastage_date=datetime.now(),
                                    notes=f"Batch {batch.batch_number} expired on {batch.expiry_date.strftime('%Y-%m-%d')}"
                                )
                                session.add(waste)

                                batch.quantity_remaining = 0
                                batch.is_active = False
                                session.commit()
                                st.warning("Logged as waste!")
                                st.rerun()

            else:
                st.success(f"✅ No critical expiring items in next {critical_days} days!")

            st.markdown("---")

            # Warning alerts
            if warning_batches:
                st.warning(f"⚠️ **WARNING:** {len(warning_batches)} batch(es) expiring within {warning_days} days")

                for batch in warning_batches:
                    ingredient = session.query(Ingredient).get(batch.ingredient_id)
                    days_left = (batch.expiry_date - today).days

                    with st.expander(f"⚠️ {ingredient.name} - {days_left} days left"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Ingredient:** {ingredient.name}")
                            st.write(f"**Remaining:** {batch.quantity_remaining:.2f} {batch.unit}")
                            st.write(f"**Expiry Date:** {batch.expiry_date.strftime('%Y-%m-%d')}")

                        with col2:
                            if batch.batch_number:
                                st.write(f"**Batch #:** {batch.batch_number}")
                            cost_remaining = batch.quantity_remaining * batch.cost_per_unit
                            st.write(f"**Value:** £{cost_remaining:.2f}")

            else:
                st.info(f"ℹ️ No items expiring in {critical_days}-{warning_days} days")

        with tab2:
            st.subheader("Log New Batch")

            with st.form("log_batch_form"):
                # Select ingredient
                ingredients = session.query(Ingredient).order_by(Ingredient.name).all()

                if not ingredients:
                    st.warning("No ingredients found. Add ingredients first!")
                    st.form_submit_button("Submit", disabled=True)
                else:
                    ingredient_options = [f"{ing.name} ({ing.unit})" for ing in ingredients]
                    selected_ingredient_str = st.selectbox("Ingredient", ingredient_options)
                    selected_ingredient = ingredients[ingredient_options.index(selected_ingredient_str)]

                    col1, col2 = st.columns(2)

                    with col1:
                        quantity = st.number_input(
                            f"Quantity ({selected_ingredient.unit})",
                            min_value=0.01,
                            step=0.1,
                            value=1.0
                        )

                    with col2:
                        cost_per_unit = st.number_input(
                            f"Cost per {selected_ingredient.unit}",
                            min_value=0.0,
                            step=0.01,
                            value=float(selected_ingredient.cost_per_unit)
                        )

                    col3, col4 = st.columns(2)

                    with col3:
                        received_date = st.date_input("Received Date", value=datetime.now())

                    with col4:
                        expiry_date = st.date_input(
                            "Expiry Date",
                            value=datetime.now() + timedelta(days=30),
                            help="When does this batch expire?"
                        )

                    batch_number = st.text_input("Batch Number (optional)", placeholder="e.g., LOT12345")

                    if st.form_submit_button("📦 Log Batch"):
                        batch = IngredientBatch(
                            ingredient_id=selected_ingredient.id,
                            quantity=quantity,
                            unit=selected_ingredient.unit,
                            cost_per_unit=cost_per_unit,
                            received_date=datetime.combine(received_date, datetime.min.time()),
                            expiry_date=datetime.combine(expiry_date, datetime.min.time()),
                            batch_number=batch_number if batch_number else None,
                            quantity_remaining=quantity,
                            is_active=True
                        )

                        session.add(batch)

                        # Also update main ingredient stock
                        selected_ingredient.current_stock += quantity

                        session.commit()

                        st.success(f"✅ Logged batch: {quantity:.2f} {selected_ingredient.unit} of {selected_ingredient.name}")
                        st.info(f"Expires on {expiry_date.strftime('%Y-%m-%d')}")
                        st.rerun()

        with tab3:
            st.subheader("All Batches (FIFO Order)")

            # Filter
            filter_status = st.radio("Show", ["Active Only", "All Batches"], horizontal=True)

            if filter_status == "Active Only":
                batches = session.query(IngredientBatch).filter(
                    IngredientBatch.is_active == True,
                    IngredientBatch.quantity_remaining > 0
                ).order_by(IngredientBatch.expiry_date).all()
            else:
                batches = session.query(IngredientBatch).order_by(
                    IngredientBatch.expiry_date.desc()
                ).all()

            if not batches:
                st.info("No batches logged yet!")
            else:
                # Group by ingredient
                batches_by_ingredient = {}
                for batch in batches:
                    ing_id = batch.ingredient_id
                    if ing_id not in batches_by_ingredient:
                        batches_by_ingredient[ing_id] = []
                    batches_by_ingredient[ing_id].append(batch)

                for ing_id, ing_batches in batches_by_ingredient.items():
                    ingredient = session.query(Ingredient).get(ing_id)

                    st.write(f"### {ingredient.name}")

                    # Show FIFO order
                    for idx, batch in enumerate(sorted(ing_batches, key=lambda x: x.expiry_date if x.expiry_date else datetime.max), 1):
                        status_icon = "🟢" if batch.is_active and batch.quantity_remaining > 0 else "⚪"
                        fifo_order = f"#{idx}" if batch.is_active else ""

                        expiry_str = batch.expiry_date.strftime('%Y-%m-%d') if batch.expiry_date else "No expiry"

                        with st.expander(f"{status_icon} {fifo_order} Batch - {expiry_str} - {batch.quantity_remaining:.2f} {batch.unit} left"):
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.write(f"**Original Qty:** {batch.quantity:.2f} {batch.unit}")
                                st.write(f"**Remaining:** {batch.quantity_remaining:.2f} {batch.unit}")
                                if batch.quantity_remaining > 0:
                                    pct_used = ((batch.quantity - batch.quantity_remaining) / batch.quantity) * 100
                                    st.write(f"**Used:** {pct_used:.0f}%")

                            with col2:
                                st.write(f"**Received:** {batch.received_date.strftime('%Y-%m-%d')}")
                                if batch.expiry_date:
                                    st.write(f"**Expires:** {batch.expiry_date.strftime('%Y-%m-%d')}")
                                    days_left = (batch.expiry_date - datetime.now()).days
                                    if days_left < 0:
                                        st.error(f"EXPIRED {abs(days_left)} days ago!")
                                    else:
                                        st.write(f"**Days left:** {days_left}")

                            with col3:
                                st.write(f"**Cost/Unit:** £{batch.cost_per_unit:.2f}")
                                total_value = batch.quantity_remaining * batch.cost_per_unit
                                st.write(f"**Value:** £{total_value:.2f}")
                                if batch.batch_number:
                                    st.write(f"**Batch #:** {batch.batch_number}")

                            # Delete button
                            if st.button("🗑️ Delete Batch", key=f"delete_batch_{batch.id}"):
                                session.delete(batch)
                                session.commit()
                                st.success("Batch deleted")
                                st.rerun()

                    st.markdown("---")

        with tab4:
            st.subheader("Expiry Analytics")

            # Total value of expiring inventory
            warning_days_analytics = 30

            expiring_batches = session.query(IngredientBatch).filter(
                IngredientBatch.is_active == True,
                IngredientBatch.expiry_date.isnot(None),
                IngredientBatch.expiry_date <= datetime.now() + timedelta(days=warning_days_analytics),
                IngredientBatch.quantity_remaining > 0
            ).all()

            if expiring_batches:
                total_value = sum(b.quantity_remaining * b.cost_per_unit for b in expiring_batches)

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(f"Batches Expiring in {warning_days_analytics} Days", len(expiring_batches))

                with col2:
                    st.metric("Total Value at Risk", f"£{total_value:.2f}")

                with col3:
                    total_qty = sum(b.quantity_remaining for b in expiring_batches)
                    st.metric("Total Quantity", f"{total_qty:.2f}")

                # Chart: Expiry timeline
                df_expiry = pd.DataFrame([{
                    'ingredient': session.query(Ingredient).get(b.ingredient_id).name,
                    'expiry_date': b.expiry_date,
                    'quantity': b.quantity_remaining,
                    'value': b.quantity_remaining * b.cost_per_unit
                } for b in expiring_batches])

                fig = px.bar(
                    df_expiry.sort_values('expiry_date'),
                    x='expiry_date',
                    y='value',
                    color='ingredient',
                    title=f'Value of Expiring Inventory ({warning_days_analytics} Days)'
                )
                fig.update_layout(
                    paper_bgcolor='#FFF7F2',
                    font=dict(color='#2C1735')
                )
                st.plotly_chart(fig, use_container_width=True)

            else:
                st.success(f"✅ No batches expiring in next {warning_days_analytics} days!")

    finally:
        close_session(session)
