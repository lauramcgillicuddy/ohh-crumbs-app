"""
Waste & Loss Tracking Page
Track wasted ingredients, finished products, and analyze waste patterns
"""

import streamlit as st
from database import get_session, close_session
from models import WastageLog, Ingredient, Recipe
from styling import inject_custom_css, render_page_header
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import func


def show_waste_tracking():
    inject_custom_css()
    render_page_header("🗑️ Waste & Loss Tracking", "REDUCE COSTS BY TRACKING WASTE")

    session = get_session()

    try:
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Log Waste", "📊 Waste Analytics", "📋 Waste History", "💡 Insights"])

        with tab1:
            st.subheader("Log Waste Event")

            waste_type = st.radio(
                "What was wasted?",
                ["🥖 Ingredient", "🍰 Finished Product"],
                horizontal=True
            )

            with st.form("log_waste_form"):
                if waste_type == "🥖 Ingredient":
                    ingredients = session.query(Ingredient).order_by(Ingredient.name).all()

                    if not ingredients:
                        st.warning("⚠️ No ingredients found. Add ingredients first!")
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
                            wastage_date = st.date_input("Waste Date", value=datetime.now())

                        reason = st.selectbox(
                            "Reason for Waste",
                            ["Expired", "Spoiled", "Dropped/Spilled", "Contaminated", "Quality Issue", "Over-ordered", "Other"]
                        )

                        notes = st.text_area("Notes (optional)", placeholder="e.g., Flour bag torn during delivery")

                        if st.form_submit_button("🗑️ Log Ingredient Waste"):
                            cost = quantity * selected_ingredient.cost_per_unit

                            waste_log = WastageLog(
                                ingredient_id=selected_ingredient.id,
                                recipe_id=None,
                                quantity=quantity,
                                unit=selected_ingredient.unit,
                                reason=reason,
                                cost=cost,
                                wastage_date=datetime.combine(wastage_date, datetime.min.time()),
                                notes=notes
                            )

                            session.add(waste_log)
                            session.commit()

                            st.success(f"✅ Logged waste: {quantity:.2f} {selected_ingredient.unit} of {selected_ingredient.name} (£{cost:.2f})")
                            st.rerun()

                else:  # Finished Product
                    recipes = session.query(Recipe).order_by(Recipe.name).all()

                    if not recipes:
                        st.warning("⚠️ No recipes found. Add recipes first!")
                        st.form_submit_button("Submit", disabled=True)
                    else:
                        recipe_options = [r.name for r in recipes]
                        selected_recipe_name = st.selectbox("Product", recipe_options)

                        selected_recipe = next(r for r in recipes if r.name == selected_recipe_name)

                        col1, col2 = st.columns(2)

                        with col1:
                            quantity = st.number_input(
                                "Quantity (units)",
                                min_value=1,
                                step=1,
                                value=1
                            )

                        with col2:
                            wastage_date = st.date_input("Waste Date", value=datetime.now())

                        reason = st.selectbox(
                            "Reason for Waste",
                            ["Burnt", "Under-cooked", "Over-cooked", "Dropped", "Customer Complaint", "Expired", "Quality Issue", "Other"]
                        )

                        notes = st.text_area("Notes (optional)", placeholder="e.g., Oven temperature was too high")

                        # Calculate cost based on recipe ingredients
                        from utils import calculate_profit_margin
                        ingredient_cost, _, _ = calculate_profit_margin(session, selected_recipe.id)
                        total_cost = ingredient_cost * quantity

                        if st.form_submit_button("🗑️ Log Product Waste"):
                            waste_log = WastageLog(
                                ingredient_id=None,
                                recipe_id=selected_recipe.id,
                                quantity=quantity,
                                unit="units",
                                reason=reason,
                                cost=total_cost,
                                wastage_date=datetime.combine(wastage_date, datetime.min.time()),
                                notes=notes
                            )

                            session.add(waste_log)
                            session.commit()

                            st.success(f"✅ Logged waste: {quantity} unit(s) of {selected_recipe.name} (£{total_cost:.2f})")
                            st.rerun()

        with tab2:
            st.subheader("Waste Analytics")

            # Time period selector
            col_space, col_period = st.columns([3, 1])
            with col_period:
                days_back = st.selectbox("Period", [7, 14, 30, 60, 90], index=2, key="analytics_period")

            start_date = datetime.now() - timedelta(days=days_back)

            waste_data = session.query(WastageLog).filter(
                WastageLog.wastage_date >= start_date
            ).all()

            if not waste_data:
                st.info("📭 No waste recorded in this period. Great job!")
            else:
                # Summary metrics
                total_waste_cost = sum(w.cost for w in waste_data)
                total_waste_events = len(waste_data)
                avg_waste_per_event = total_waste_cost / total_waste_events if total_waste_events > 0 else 0

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Waste Cost", f"£{total_waste_cost:.2f}")

                with col2:
                    st.metric("Waste Events", total_waste_events)

                with col3:
                    st.metric("Avg Cost/Event", f"£{avg_waste_per_event:.2f}")

                st.markdown("<br>", unsafe_allow_html=True)

                # Waste by reason
                df_waste = pd.DataFrame([{
                    'date': w.wastage_date,
                    'reason': w.reason,
                    'cost': w.cost,
                    'type': 'Ingredient' if w.ingredient_id else 'Product'
                } for w in waste_data])

                col_chart1, col_chart2 = st.columns(2)

                with col_chart1:
                    # Pie chart by reason
                    waste_by_reason = df_waste.groupby('reason')['cost'].sum().reset_index()
                    fig_pie = px.pie(
                        waste_by_reason,
                        values='cost',
                        names='reason',
                        title='Waste Cost by Reason'
                    )
                    fig_pie.update_layout(
                        paper_bgcolor='#FFF7F2',
                        font=dict(color='#2C1735')
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

                with col_chart2:
                    # Bar chart by type
                    waste_by_type = df_waste.groupby('type')['cost'].sum().reset_index()
                    fig_bar = px.bar(
                        waste_by_type,
                        x='type',
                        y='cost',
                        title='Waste Cost by Type',
                        color='type',
                        color_discrete_map={'Ingredient': '#F29BB2', 'Product': '#FFD4E5'}
                    )
                    fig_bar.update_layout(
                        paper_bgcolor='#FFF7F2',
                        font=dict(color='#2C1735'),
                        showlegend=False
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                # Daily trend
                daily_waste = df_waste.groupby(df_waste['date'].dt.date)['cost'].sum().reset_index()
                daily_waste.columns = ['date', 'cost']

                fig_trend = px.line(
                    daily_waste,
                    x='date',
                    y='cost',
                    title='Daily Waste Cost Trend'
                )
                fig_trend.update_layout(
                    paper_bgcolor='#FFF7F2',
                    plot_bgcolor='rgba(255,247,242,0.5)',
                    font=dict(color='#2C1735')
                )
                fig_trend.update_traces(line=dict(color='#F29BB2', width=3))
                st.plotly_chart(fig_trend, use_container_width=True)

        with tab3:
            st.subheader("Waste History")

            # Filters
            col_filter1, col_filter2 = st.columns(2)

            with col_filter1:
                filter_type = st.selectbox("Filter by Type", ["All", "Ingredients", "Products"])

            with col_filter2:
                filter_days = st.selectbox("Time Period", [7, 14, 30, 60, 90, 180], index=2, key="history_period")

            start_date = datetime.now() - timedelta(days=filter_days)

            query = session.query(WastageLog).filter(WastageLog.wastage_date >= start_date)

            if filter_type == "Ingredients":
                query = query.filter(WastageLog.ingredient_id.isnot(None))
            elif filter_type == "Products":
                query = query.filter(WastageLog.recipe_id.isnot(None))

            waste_logs = query.order_by(WastageLog.wastage_date.desc()).all()

            if not waste_logs:
                st.info("No waste records found for the selected filters.")
            else:
                for log in waste_logs:
                    with st.expander(f"{log.wastage_date.strftime('%Y-%m-%d')} - {log.reason} - £{log.cost:.2f}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            if log.ingredient_id:
                                ingredient = session.query(Ingredient).get(log.ingredient_id)
                                st.write(f"**Type:** Ingredient")
                                st.write(f"**Item:** {ingredient.name if ingredient else 'Unknown'}")
                                st.write(f"**Quantity:** {log.quantity:.2f} {log.unit}")
                            else:
                                recipe = session.query(Recipe).get(log.recipe_id)
                                st.write(f"**Type:** Finished Product")
                                st.write(f"**Item:** {recipe.name if recipe else 'Unknown'}")
                                st.write(f"**Quantity:** {log.quantity:.0f} units")

                        with col2:
                            st.write(f"**Reason:** {log.reason}")
                            st.write(f"**Cost:** £{log.cost:.2f}")
                            st.write(f"**Date:** {log.wastage_date.strftime('%Y-%m-%d')}")

                        if log.notes:
                            st.write(f"**Notes:** {log.notes}")

                        # Delete button
                        if st.button(f"🗑️ Delete", key=f"delete_waste_{log.id}"):
                            session.delete(log)
                            session.commit()
                            st.success("Waste log deleted")
                            st.rerun()

        with tab4:
            st.subheader("💡 Waste Reduction Insights")

            # Analyze waste patterns
            days_back = 30
            start_date = datetime.now() - timedelta(days=days_back)

            waste_data = session.query(WastageLog).filter(
                WastageLog.wastage_date >= start_date
            ).all()

            if not waste_data:
                st.info("Not enough data to generate insights yet. Keep logging waste!")
            else:
                total_waste_cost = sum(w.cost for w in waste_data)

                # Top waste reasons
                waste_by_reason = {}
                for w in waste_data:
                    if w.reason not in waste_by_reason:
                        waste_by_reason[w.reason] = 0
                    waste_by_reason[w.reason] += w.cost

                top_reason = max(waste_by_reason.items(), key=lambda x: x[1])

                st.error(f"🚨 **Top Waste Reason:** {top_reason[0]} (£{top_reason[1]:.2f})")

                # Recommendations based on top reason
                recommendations = {
                    "Expired": "💡 Consider: Enable expiry date tracking, reduce order quantities, or implement FIFO system",
                    "Spoiled": "💡 Consider: Check storage temperatures, review shelf life estimates, improve packaging",
                    "Burnt": "💡 Consider: Review oven settings, set timers, provide training on temperature control",
                    "Dropped/Spilled": "💡 Consider: Improve workplace organization, review handling procedures, use better containers",
                    "Customer Complaint": "💡 Consider: Review quality control procedures, gather customer feedback, improve recipes",
                    "Over-cooked": "💡 Consider: Use timers, review cooking times in recipes, provide training",
                    "Under-cooked": "💡 Consider: Check oven temperature, increase cooking times, improve quality checks"
                }

                if top_reason[0] in recommendations:
                    st.info(recommendations[top_reason[0]])

                # Most wasted items
                ingredient_waste = session.query(
                    Ingredient.name,
                    func.sum(WastageLog.cost).label('total_cost')
                ).join(
                    WastageLog, Ingredient.id == WastageLog.ingredient_id
                ).filter(
                    WastageLog.wastage_date >= start_date
                ).group_by(
                    Ingredient.name
                ).order_by(
                    func.sum(WastageLog.cost).desc()
                ).limit(5).all()

                if ingredient_waste:
                    st.warning("**Most Wasted Ingredients:**")
                    for idx, (name, cost) in enumerate(ingredient_waste, 1):
                        st.write(f"{idx}. {name} - £{cost:.2f}")

                # Waste trend
                if len(waste_data) >= 7:
                    recent_week = [w for w in waste_data if w.wastage_date >= datetime.now() - timedelta(days=7)]
                    previous_week = [w for w in waste_data if datetime.now() - timedelta(days=14) <= w.wastage_date < datetime.now() - timedelta(days=7)]

                    recent_cost = sum(w.cost for w in recent_week)
                    previous_cost = sum(w.cost for w in previous_week)

                    if previous_cost > 0:
                        change_pct = ((recent_cost - previous_cost) / previous_cost) * 100

                        if change_pct > 0:
                            st.error(f"⚠️ Waste increased by {change_pct:.1f}% compared to last week")
                        else:
                            st.success(f"✅ Waste decreased by {abs(change_pct):.1f}% compared to last week!")

    finally:
        close_session(session)
