"""
Production Planner with AI Forecasting
Smart recommendations on what to bake based on sales trends, stock levels, and expiry dates
"""

import streamlit as st
from database import get_session, close_session
from models import ProductionPlan, Recipe, SalesCache, Ingredient, RecipeItem
from styling import inject_custom_css, render_page_header
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
from sqlalchemy import func


def forecast_demand(session, recipe_id, days_back=30):
    """
    Simple demand forecasting based on historical sales
    Returns: (average_daily_demand, confidence_score, trend)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    recipe = session.query(Recipe).get(recipe_id)

    if not recipe:
        return 0.0, 0, "unknown"

    # Get sales history
    sales_data = session.query(
        func.date(SalesCache.timestamp).label('sale_date'),
        func.sum(SalesCache.quantity).label('quantity')
    ).filter(
        SalesCache.item_name == recipe.name,
        SalesCache.timestamp >= start_date
    ).group_by(
        func.date(SalesCache.timestamp)
    ).all()

    if not sales_data:
        return 0.0, 0, "no_data"

    # Calculate average daily demand
    total_sold = sum(day[1] for day in sales_data)
    days_with_sales = len(sales_data)
    avg_daily = total_sold / days_back  # Use total days, not just days with sales

    # Calculate confidence based on consistency
    if days_with_sales < 3:
        confidence = 20
    elif days_with_sales < 7:
        confidence = 40
    elif days_with_sales < 14:
        confidence = 60
    else:
        confidence = 80

    # Detect trend (simple: compare first half vs second half)
    mid_date = start_date + timedelta(days=days_back // 2)

    first_half = sum(day[1] for day in sales_data if day[0] < mid_date.date())
    second_half = sum(day[1] for day in sales_data if day[0] >= mid_date.date())

    if second_half > first_half * 1.2:
        trend = "increasing"
        confidence += 10  # More confident if trending up
    elif second_half < first_half * 0.8:
        trend = "decreasing"
    else:
        trend = "stable"

    # Day of week analysis (boost confidence if we have weekly pattern)
    if len(sales_data) >= 14:
        weekday_sales = {}
        for day_date, quantity in sales_data:
            weekday = day_date.weekday()
            if weekday not in weekday_sales:
                weekday_sales[weekday] = []
            weekday_sales[weekday].append(quantity)

        # Check if there's a clear weekly pattern
        if len(weekday_sales) >= 5:
            confidence += 10

    confidence = min(100, confidence)  # Cap at 100%

    return avg_daily, confidence, trend


def show_production_planner():
    inject_custom_css()
    render_page_header("📅 Production Planner", "SMART BAKING RECOMMENDATIONS")

    session = get_session()

    try:
        tab1, tab2, tab3 = st.tabs(["🤖 AI Recommendations", "📅 Production Schedule", "📊 Forecast Analysis"])

        with tab1:
            st.subheader("What Should I Bake Today?")

            # Planning date selector
            col_date, col_refresh = st.columns([3, 1])

            with col_date:
                plan_date = st.date_input("Planning For Date", value=datetime.now())

            with col_refresh:
                st.write("")
                st.write("")
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()

            st.markdown("---")

            recipes = session.query(Recipe).all()

            if not recipes:
                st.warning("⚠️ No recipes found. Add recipes first!")
            else:
                recommendations = []

                for recipe in recipes:
                    # Get forecast
                    avg_demand, confidence, trend = forecast_demand(session, recipe.id, days_back=30)

                    # Check ingredient availability
                    can_make = True
                    max_possible = float('inf')

                    for recipe_item in recipe.recipe_items:
                        ingredient = recipe_item.ingredient
                        needed_per_unit = recipe_item.quantity

                        if needed_per_unit > 0:
                            possible_units = ingredient.current_stock / needed_per_unit
                            max_possible = min(max_possible, possible_units)

                            if ingredient.current_stock < avg_demand * needed_per_unit:
                                can_make = False

                    if max_possible == float('inf'):
                        max_possible = 0

                    # Calculate priority score
                    priority = avg_demand * confidence / 100

                    # Boost priority for trending items
                    if trend == "increasing":
                        priority *= 1.3
                    elif trend == "decreasing":
                        priority *= 0.7

                    recommendations.append({
                        'recipe': recipe,
                        'avg_demand': avg_demand,
                        'confidence': confidence,
                        'trend': trend,
                        'can_make': can_make,
                        'max_possible': int(max_possible),
                        'priority': priority
                    })

                # Sort by priority
                recommendations.sort(key=lambda x: x['priority'], reverse=True)

                # Show top recommendations
                st.write("**🎯 Top Recommendations:**")

                for idx, rec in enumerate(recommendations[:10], 1):
                    recipe = rec['recipe']
                    avg_demand = rec['avg_demand']
                    confidence = rec['confidence']
                    trend = rec['trend']
                    max_possible = rec['max_possible']

                    # Color code by priority
                    if rec['priority'] > 5:
                        priority_color = "🔥"
                        priority_text = "HIGH"
                    elif rec['priority'] > 2:
                        priority_color = "⭐"
                        priority_text = "MEDIUM"
                    else:
                        priority_color = "💡"
                        priority_text = "LOW"

                    trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "➡️", "no_data": "❓"}

                    with st.expander(f"{idx}. {priority_color} {recipe.name} - {priority_text} Priority"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.metric("Avg Daily Demand", f"{avg_demand:.1f} units")
                            st.write(f"**Suggested Production:** {int(avg_demand * 1.2)} units")
                            st.caption("(20% buffer for safety)")

                        with col2:
                            st.metric("Forecast Confidence", f"{confidence}%")
                            st.write(f"**Trend:** {trend_emoji.get(trend, '❓')} {trend.title()}")

                        with col3:
                            st.metric("Max Possible", f"{max_possible} units")
                            if rec['can_make']:
                                st.success("✅ Ingredients available")
                            else:
                                st.error("❌ Low stock")

                        # Ingredient requirements
                        st.write("**Ingredients Needed (for suggested production):**")
                        suggested_qty = int(avg_demand * 1.2)

                        for item in recipe.recipe_items:
                            needed = item.quantity * suggested_qty
                            available = item.ingredient.current_stock

                            if available >= needed:
                                st.write(f"✅ {item.ingredient.name}: {needed:.2f} {item.ingredient.unit} (have {available:.2f})")
                            else:
                                shortage = needed - available
                                st.write(f"❌ {item.ingredient.name}: {needed:.2f} {item.ingredient.unit} needed, only {available:.2f} available")
                                st.write(f"   ⚠️ Short by {shortage:.2f} {item.ingredient.unit}")

                        # Quick add to schedule button
                        if st.button(f"📅 Add to Production Schedule", key=f"quick_add_{recipe.id}"):
                            planned_date = datetime.combine(plan_date, datetime.min.time())

                            # Check if already planned
                            existing = session.query(ProductionPlan).filter(
                                ProductionPlan.recipe_id == recipe.id,
                                ProductionPlan.planned_date == planned_date,
                                ProductionPlan.status == 'planned'
                            ).first()

                            if existing:
                                st.warning("Already in production schedule for this date!")
                            else:
                                plan = ProductionPlan(
                                    recipe_id=recipe.id,
                                    planned_date=planned_date,
                                    planned_quantity=suggested_qty,
                                    forecasted_demand=avg_demand,
                                    confidence_score=confidence,
                                    status='planned'
                                )
                                session.add(plan)
                                session.commit()
                                st.success(f"✅ Added {suggested_qty} units of {recipe.name} to production schedule!")
                                st.rerun()

        with tab2:
            st.subheader("Production Schedule")

            # Date range selector
            col_start, col_end = st.columns(2)

            with col_start:
                start_date = st.date_input("From Date", value=datetime.now())

            with col_end:
                end_date = st.date_input("To Date", value=datetime.now() + timedelta(days=7))

            # Get scheduled production
            plans = session.query(ProductionPlan).filter(
                ProductionPlan.planned_date >= datetime.combine(start_date, datetime.min.time()),
                ProductionPlan.planned_date <= datetime.combine(end_date, datetime.min.time())
            ).order_by(ProductionPlan.planned_date).all()

            if not plans:
                st.info("No production scheduled for this date range. Use AI Recommendations to create a schedule!")
            else:
                # Group by date
                plans_by_date = {}
                for plan in plans:
                    date_str = plan.planned_date.strftime('%Y-%m-%d')
                    if date_str not in plans_by_date:
                        plans_by_date[date_str] = []
                    plans_by_date[date_str].append(plan)

                # Display schedule
                for date_str, date_plans in plans_by_date.items():
                    st.write(f"### 📅 {date_str}")

                    for plan in date_plans:
                        recipe = session.query(Recipe).get(plan.recipe_id)

                        if recipe:
                            status_emoji = {
                                'planned': '📝',
                                'in_progress': '⏳',
                                'completed': '✅',
                                'cancelled': '❌'
                            }

                            with st.expander(f"{status_emoji.get(plan.status, '❓')} {recipe.name} - {plan.planned_quantity:.0f} units"):
                                col1, col2 = st.columns(2)

                                with col1:
                                    st.write(f"**Planned Quantity:** {plan.planned_quantity:.0f} units")
                                    if plan.forecasted_demand:
                                        st.write(f"**Forecasted Demand:** {plan.forecasted_demand:.1f} units/day")
                                    if plan.confidence_score:
                                        st.write(f"**Confidence:** {plan.confidence_score:.0f}%")

                                with col2:
                                    st.write(f"**Status:** {plan.status.title()}")
                                    if plan.actual_quantity:
                                        st.write(f"**Actually Produced:** {plan.actual_quantity:.0f} units")

                                if plan.notes:
                                    st.write(f"**Notes:** {plan.notes}")

                                # Action buttons
                                col_btn1, col_btn2, col_btn3 = st.columns(3)

                                with col_btn1:
                                    if plan.status == 'planned' and st.button("▶️ Start", key=f"start_{plan.id}"):
                                        plan.status = 'in_progress'
                                        session.commit()
                                        st.rerun()

                                with col_btn2:
                                    if plan.status in ['planned', 'in_progress'] and st.button("✅ Complete", key=f"complete_{plan.id}"):
                                        plan.status = 'completed'
                                        plan.actual_quantity = plan.planned_quantity
                                        session.commit()
                                        st.success("Marked as completed!")
                                        st.rerun()

                                with col_btn3:
                                    if st.button("🗑️ Delete", key=f"delete_plan_{plan.id}"):
                                        session.delete(plan)
                                        session.commit()
                                        st.rerun()

                    st.markdown("---")

        with tab3:
            st.subheader("Forecast Analysis")

            recipes = session.query(Recipe).all()

            if not recipes:
                st.warning("No recipes to analyze")
            else:
                # Select recipe to analyze
                recipe_names = [r.name for r in recipes]
                selected_recipe_name = st.selectbox("Select Recipe to Analyze", recipe_names)

                selected_recipe = next(r for r in recipes if r.name == selected_recipe_name)

                # Get forecast
                avg_demand, confidence, trend = forecast_demand(session, selected_recipe.id, days_back=60)

                # Display metrics
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Avg Daily Demand", f"{avg_demand:.1f} units")

                with col2:
                    st.metric("Confidence Score", f"{confidence}%")

                with col3:
                    trend_emoji = {"increasing": "📈", "decreasing": "📉", "stable": "➡️", "no_data": "❓"}
                    st.metric("Trend", f"{trend_emoji.get(trend, '❓')} {trend.title()}")

                st.markdown("---")

                # Sales history chart
                st.write("**📊 Sales History (Last 60 Days)**")

                end_date = datetime.now()
                start_date = end_date - timedelta(days=60)

                sales_data = session.query(
                    func.date(SalesCache.timestamp).label('sale_date'),
                    func.sum(SalesCache.quantity).label('quantity')
                ).filter(
                    SalesCache.item_name == selected_recipe.name,
                    SalesCache.timestamp >= start_date
                ).group_by(
                    func.date(SalesCache.timestamp)
                ).all()

                if sales_data:
                    df_sales = pd.DataFrame(sales_data, columns=['date', 'quantity'])

                    fig = px.bar(
                        df_sales,
                        x='date',
                        y='quantity',
                        title=f'Daily Sales: {selected_recipe.name}'
                    )
                    fig.update_layout(
                        paper_bgcolor='#FFF7F2',
                        plot_bgcolor='rgba(255,247,242,0.5)',
                        font=dict(color='#2C1735')
                    )
                    fig.update_traces(marker_color='#F29BB2')

                    # Add trend line
                    fig.add_scatter(
                        x=df_sales['date'],
                        y=[avg_demand] * len(df_sales),
                        mode='lines',
                        name='Average',
                        line=dict(color='#FF6B9D', dash='dash')
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    # Day of week analysis
                    st.write("**📅 Sales by Day of Week:**")

                    df_sales['weekday'] = pd.to_datetime(df_sales['date']).dt.day_name()

                    weekday_avg = df_sales.groupby('weekday')['quantity'].mean().reset_index()

                    # Order by day of week
                    weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    weekday_avg['weekday'] = pd.Categorical(weekday_avg['weekday'], categories=weekday_order, ordered=True)
                    weekday_avg = weekday_avg.sort_values('weekday')

                    fig_weekday = px.bar(
                        weekday_avg,
                        x='weekday',
                        y='quantity',
                        title='Average Sales by Day of Week'
                    )
                    fig_weekday.update_layout(
                        paper_bgcolor='#FFF7F2',
                        font=dict(color='#2C1735')
                    )
                    fig_weekday.update_traces(marker_color='#FFD4E5')

                    st.plotly_chart(fig_weekday, use_container_width=True)

                else:
                    st.info("No sales history available for this recipe yet.")

    finally:
        close_session(session)
