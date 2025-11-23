"""
Cash Flow Forecast
Predict future cash flow based on sales trends, upcoming orders, and expenses
"""

import streamlit as st
from database import get_session, close_session
from models import SalesCache, SupplierOrder, ProductionBatch, WastageLog, EquipmentLog
from styling import inject_custom_css, render_page_header
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from sqlalchemy import func


def show_cash_flow():
    inject_custom_css()
    render_page_header("💰 Cash Flow Forecast", "PREDICT YOUR FINANCIAL FUTURE")

    session = get_session()

    try:
        st.subheader("Financial Overview")

        # Time range selector
        col_past, col_future = st.columns(2)

        with col_past:
            days_history = st.selectbox("Historical Data", [30, 60, 90], index=1)

        with col_future:
            days_forecast = st.selectbox("Forecast Ahead", [7, 14, 30, 60, 90], index=2)

        st.markdown("---")

        # Historical analysis
        start_date = datetime.now() - timedelta(days=days_history)
        end_date = datetime.now()

        # INCOME: Sales revenue
        sales_data = session.query(SalesCache).filter(
            SalesCache.timestamp >= start_date
        ).all()

        daily_revenue = {}
        for sale in sales_data:
            date_key = sale.timestamp.date()
            if date_key not in daily_revenue:
                daily_revenue[date_key] = 0
            daily_revenue[date_key] += sale.total_amount

        # EXPENSES: Calculate various costs
        # 1. Supplier orders
        supplier_orders = session.query(SupplierOrder).filter(
            SupplierOrder.order_date >= start_date
        ).all()

        daily_supplier_costs = {}
        for order in supplier_orders:
            date_key = order.order_date.date()
            if date_key not in daily_supplier_costs:
                daily_supplier_costs[date_key] = 0
            daily_supplier_costs[date_key] += order.total_cost

        # 2. Waste costs
        waste_logs = session.query(WastageLog).filter(
            WastageLog.wastage_date >= start_date
        ).all()

        daily_waste_costs = {}
        for waste in waste_logs:
            date_key = waste.wastage_date.date()
            if date_key not in daily_waste_costs:
                daily_waste_costs[date_key] = 0
            daily_waste_costs[date_key] += waste.cost

        # 3. Equipment maintenance
        equipment_logs = session.query(EquipmentLog).filter(
            EquipmentLog.maintenance_date >= start_date
        ).all()

        daily_equipment_costs = {}
        for log in equipment_logs:
            date_key = log.maintenance_date.date()
            if date_key not in daily_equipment_costs:
                daily_equipment_costs[date_key] = 0
            daily_equipment_costs[date_key] += log.cost

        # Calculate daily cash flow
        all_dates = set(list(daily_revenue.keys()) +
                       list(daily_supplier_costs.keys()) +
                       list(daily_waste_costs.keys()) +
                       list(daily_equipment_costs.keys()))

        daily_cash_flow = []
        for date in sorted(all_dates):
            revenue = daily_revenue.get(date, 0)
            supplier_cost = daily_supplier_costs.get(date, 0)
            waste_cost = daily_waste_costs.get(date, 0)
            equipment_cost = daily_equipment_costs.get(date, 0)

            net_flow = revenue - (supplier_cost + waste_cost + equipment_cost)

            daily_cash_flow.append({
                'date': date,
                'revenue': revenue,
                'expenses': supplier_cost + waste_cost + equipment_cost,
                'supplier_costs': supplier_cost,
                'waste_costs': waste_cost,
                'equipment_costs': equipment_cost,
                'net_flow': net_flow
            })

        if not daily_cash_flow:
            st.warning("Not enough data to generate cash flow forecast. Start logging sales, orders, and expenses!")
            return

        df_cash = pd.DataFrame(daily_cash_flow)

        # Calculate cumulative cash (assuming starting balance)
        starting_balance = st.number_input(
            "Current Cash Balance (£)",
            min_value=0.0,
            value=1000.0,
            step=100.0,
            help="How much money do you have in the bank right now?"
        )

        cumulative_balance = starting_balance
        df_cash['balance'] = 0.0

        for idx, row in df_cash.iterrows():
            cumulative_balance += row['net_flow']
            df_cash.at[idx, 'balance'] = cumulative_balance

        # Summary metrics
        total_revenue = df_cash['revenue'].sum()
        total_expenses = df_cash['expenses'].sum()
        net_profit = total_revenue - total_expenses

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Revenue", f"£{total_revenue:,.2f}")

        with col2:
            st.metric("Total Expenses", f"£{total_expenses:,.2f}")

        with col3:
            st.metric("Net Profit", f"£{net_profit:,.2f}", delta=f"{(net_profit/total_revenue*100):.1f}%" if total_revenue > 0 else "0%")

        with col4:
            current_balance = df_cash.iloc[-1]['balance']
            st.metric("Projected Balance", f"£{current_balance:,.2f}")

        st.markdown("---")

        # Historical cash flow chart
        st.subheader("📊 Historical Cash Flow")

        fig_historical = go.Figure()

        # Revenue
        fig_historical.add_trace(go.Bar(
            x=df_cash['date'],
            y=df_cash['revenue'],
            name='Revenue',
            marker_color='#2ca02c',
            hovertemplate='%{x}<br>Revenue: £%{y:,.2f}<extra></extra>'
        ))

        # Expenses
        fig_historical.add_trace(go.Bar(
            x=df_cash['date'],
            y=-df_cash['expenses'],
            name='Expenses',
            marker_color='#d62728',
            hovertemplate='%{x}<br>Expenses: £%{y:,.2f}<extra></extra>'
        ))

        # Net flow line
        fig_historical.add_trace(go.Scatter(
            x=df_cash['date'],
            y=df_cash['net_flow'],
            name='Net Cash Flow',
            line=dict(color='#1f77b4', width=3),
            hovertemplate='%{x}<br>Net Flow: £%{y:,.2f}<extra></extra>'
        ))

        fig_historical.update_layout(
            title='Daily Cash Flow',
            xaxis_title='Date',
            yaxis_title='Amount (£)',
            paper_bgcolor='#FFF7F2',
            plot_bgcolor='rgba(255,247,242,0.5)',
            font=dict(color='#2C1735'),
            hovermode='x unified',
            barmode='relative'
        )

        st.plotly_chart(fig_historical, use_container_width=True)

        # Balance projection chart
        st.subheader("💸 Cash Balance Projection")

        # Calculate forecast
        avg_daily_revenue = df_cash['revenue'].mean()
        avg_daily_expenses = df_cash['expenses'].mean()
        avg_net_flow = avg_daily_revenue - avg_daily_expenses

        # Generate forecast dates
        last_date = df_cash.iloc[-1]['date']
        forecast_dates = [last_date + timedelta(days=i) for i in range(1, days_forecast + 1)]

        # Project future balance
        forecast_balance = []
        current_bal = df_cash.iloc[-1]['balance']

        for date in forecast_dates:
            current_bal += avg_net_flow
            forecast_balance.append({
                'date': date,
                'balance': current_bal,
                'type': 'Forecast'
            })

        # Combine historical and forecast
        df_balance_historical = df_cash[['date', 'balance']].copy()
        df_balance_historical['type'] = 'Actual'

        df_balance_forecast = pd.DataFrame(forecast_balance)

        df_balance_combined = pd.concat([df_balance_historical, df_balance_forecast], ignore_index=True)

        fig_balance = go.Figure()

        # Historical balance
        df_hist = df_balance_combined[df_balance_combined['type'] == 'Actual']
        fig_balance.add_trace(go.Scatter(
            x=df_hist['date'],
            y=df_hist['balance'],
            name='Actual Balance',
            line=dict(color='#2ca02c', width=3),
            fill='tozeroy',
            fillcolor='rgba(44, 160, 44, 0.2)',
            hovertemplate='%{x}<br>Balance: £%{y:,.2f}<extra></extra>'
        ))

        # Forecast balance
        df_fore = df_balance_combined[df_balance_combined['type'] == 'Forecast']
        fig_balance.add_trace(go.Scatter(
            x=df_fore['date'],
            y=df_fore['balance'],
            name='Forecasted Balance',
            line=dict(color='#ff7f0e', width=3, dash='dash'),
            fill='tozeroy',
            fillcolor='rgba(255, 127, 14, 0.1)',
            hovertemplate='%{x}<br>Forecast: £%{y:,.2f}<extra></extra>'
        ))

        # Add zero line
        fig_balance.add_hline(y=0, line_dash="dot", line_color="red",
                            annotation_text="Break-even")

        fig_balance.update_layout(
            title='Cash Balance Over Time',
            xaxis_title='Date',
            yaxis_title='Cash Balance (£)',
            paper_bgcolor='#FFF7F2',
            plot_bgcolor='rgba(255,247,242,0.5)',
            font=dict(color='#2C1735'),
            hovermode='x unified'
        )

        st.plotly_chart(fig_balance, use_container_width=True)

        # Forecast analysis
        st.markdown("---")
        st.subheader("🔮 Forecast Analysis")

        final_forecast_balance = forecast_balance[-1]['balance']

        col_fore1, col_fore2 = st.columns(2)

        with col_fore1:
            st.write(f"**Projected balance in {days_forecast} days:** £{final_forecast_balance:,.2f}")

            if final_forecast_balance < 0:
                days_until_broke = 0
                test_bal = current_balance

                for i in range(1, days_forecast + 1):
                    test_bal += avg_net_flow
                    if test_bal < 0:
                        days_until_broke = i
                        break

                if days_until_broke > 0:
                    st.error(f"⚠️ **WARNING:** You may run out of cash in approximately {days_until_broke} days!")
                    st.write("**Recommendations:**")
                    st.write("• Reduce expenses immediately")
                    st.write("• Increase sales prices or volume")
                    st.write("• Delay non-essential orders")
                    st.write("• Consider getting a short-term loan")
            elif final_forecast_balance < starting_balance * 0.5:
                st.warning(f"⚠️ Your cash balance is projected to decline by {((starting_balance - final_forecast_balance) / starting_balance * 100):.0f}%")
                st.write("**Recommendations:**")
                st.write("• Monitor expenses closely")
                st.write("• Look for ways to boost sales")
                st.write("• Review and reduce waste")
            else:
                st.success(f"✅ Your cash flow is healthy! Balance growing by £{(final_forecast_balance - starting_balance):.2f}")

        with col_fore2:
            st.write("**Key Assumptions:**")
            st.write(f"• Avg daily revenue: £{avg_daily_revenue:.2f}")
            st.write(f"• Avg daily expenses: £{avg_daily_expenses:.2f}")
            st.write(f"• Avg net cash flow: £{avg_net_flow:.2f}/day")

            if avg_net_flow < 0:
                st.error("⚠️ You're spending more than you earn on average!")
            else:
                st.success("✅ Positive average cash flow")

        # Expense breakdown
        st.markdown("---")
        st.subheader("💸 Expense Breakdown")

        total_supplier = df_cash['supplier_costs'].sum()
        total_waste = df_cash['waste_costs'].sum()
        total_equipment = df_cash['equipment_costs'].sum()

        expense_data = pd.DataFrame({
            'Category': ['Suppliers', 'Waste', 'Equipment'],
            'Amount': [total_supplier, total_waste, total_equipment]
        })

        expense_data = expense_data[expense_data['Amount'] > 0]  # Only show non-zero

        if len(expense_data) > 0:
            col_exp1, col_exp2 = st.columns([1, 1])

            with col_exp1:
                for _, row in expense_data.iterrows():
                    pct = (row['Amount'] / total_expenses * 100) if total_expenses > 0 else 0
                    st.write(f"**{row['Category']}:** £{row['Amount']:.2f} ({pct:.1f}%)")

            with col_exp2:
                # Pie chart
                import plotly.express as px
                fig_pie = px.pie(
                    expense_data,
                    values='Amount',
                    names='Category',
                    title='Expense Distribution'
                )
                fig_pie.update_layout(
                    paper_bgcolor='#FFF7F2',
                    font=dict(color='#2C1735')
                )
                st.plotly_chart(fig_pie, use_container_width=True)

    finally:
        close_session(session)
