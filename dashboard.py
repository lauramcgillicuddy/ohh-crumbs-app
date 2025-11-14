import streamlit as st
from database import get_session, close_session
from utils import get_sales_summary, generate_business_recommendations, auto_sync_square_sales
from models import SalesCache, Recipe
from utils import calculate_profit_margin
from sqlalchemy import func
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
from pdf_reports import generate_sales_report
from styling import inject_custom_css, render_page_header

def show_dashboard():
    inject_custom_css()

    render_page_header("🧁 Ohh Crumbs", "CAKE AND CRUMBLE")

    # Auto-sync Square sales data (runs once per hour due to cache)
    sync_result = auto_sync_square_sales(days_back=30)
    if sync_result and sync_result.get('imported', 0) > 0:
        st.toast(f"✅ Synced {sync_result['imported']} new sales from Square", icon="🔄")

    session = get_session()

    try:
        # Time period selector
        col_space, col_select = st.columns([3, 1])
        with col_select:
            days_back = st.selectbox("Time Period", [7, 14, 30, 60, 90], index=2)

        st.markdown("<br>", unsafe_allow_html=True)

        start_date = datetime.utcnow() - timedelta(days=days_back)
        end_date = datetime.utcnow()

        summary = get_sales_summary(session, days=days_back)

        # Metrics cards
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Revenue",
                f"£{summary['total_revenue']:,.2f}"
            )

        with col2:
            st.metric(
                "Total Profit",
                f"£{summary['total_profit']:,.2f}"
            )

        with col3:
            st.metric(
                "Profit Margin",
                f"{summary['avg_profit_margin']:.1f}%"
            )

        with col4:
            st.metric(
                "Items Sold",
                f"{summary['total_items_sold']:,}"
            )

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()

        st.subheader("💡 Business Recommendations")

        recommendations = generate_business_recommendations(session)

        if recommendations:
            for rec in recommendations:
                if rec['priority'] == 'critical':
                    st.error(f"🚨 {rec['message']}")
                elif rec['priority'] == 'high':
                    st.success(f"⭐ {rec['message']}")
                elif rec['priority'] == 'medium':
                    st.info(f"💡 {rec['message']}")
                else:
                    st.info(f"✨ {rec['message']}")
        else:
            st.info("✨ No recommendations at this time. Keep adding sales data and recipes for insights!")

        st.divider()

        sales_data = session.query(SalesCache).filter(
            SalesCache.timestamp >= start_date
        ).order_by(SalesCache.timestamp).all()

        if sales_data:
            st.subheader("📈 Sales Trends")

            df = pd.DataFrame([{
                'date': sale.timestamp.date(),
                'item': sale.item_name,
                'quantity': sale.quantity,
                'amount': sale.total_amount
            } for sale in sales_data])

            daily_sales = df.groupby('date').agg({
                'amount': 'sum',
                'quantity': 'sum'
            }).reset_index()

            # Pastel pink themed chart
            fig_revenue = px.line(
                daily_sales,
                x='date',
                y='amount',
                title='Daily Revenue Trend'
            )
            fig_revenue.update_layout(
                height=400,
                plot_bgcolor='rgba(255,247,242,0.5)',
                paper_bgcolor='#FFF7F2',
                font=dict(color='#2C1735', size=12),
                title_font=dict(size=16, color='#F29BB2', family='Baloo 2'),
                xaxis=dict(
                    title='Date',
                    gridcolor='#FFE4F2',
                    showgrid=True
                ),
                yaxis=dict(
                    title='Revenue (£)',
                    gridcolor='#FFE4F2',
                    showgrid=True
                )
            )
            fig_revenue.update_traces(
                line=dict(color='#F29BB2', width=3),
                fill='tozeroy',
                fillcolor='rgba(242, 155, 178, 0.2)'
            )
            st.plotly_chart(fig_revenue, use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("🏆 Top Selling Items")

            top_items = df.groupby('item').agg({
                'quantity': 'sum',
                'amount': 'sum'
            }).reset_index().sort_values('quantity', ascending=False).head(10)

            # Pastel pink themed bar chart
            fig_items = px.bar(
                top_items,
                x='item',
                y='quantity',
                title='Top 10 Best Sellers'
            )
            fig_items.update_layout(
                height=400,
                plot_bgcolor='rgba(255,247,242,0.5)',
                paper_bgcolor='#FFF7F2',
                font=dict(color='#2C1735', size=12),
                title_font=dict(size=16, color='#F29BB2', family='Baloo 2'),
                xaxis=dict(
                    title='Item',
                    gridcolor='#FFE4F2',
                    tickangle=-45
                ),
                yaxis=dict(
                    title='Units Sold',
                    gridcolor='#FFE4F2'
                )
            )
            fig_items.update_traces(
                marker=dict(
                    color='#F29BB2',
                    line=dict(color='#FFE4F2', width=2)
                )
            )
            st.plotly_chart(fig_items, use_container_width=True)
        else:
            st.info("📭 No sales data available yet. Connect to Square API or add manual sales entries.")

        st.divider()

        st.subheader("📄 Export Reports")

        if st.button("📥 Generate PDF Sales Report", use_container_width=True):
            recipes = session.query(Recipe).all()
            sales_data_for_pdf = []

            for recipe in recipes:
                sales_count = session.query(func.sum(SalesCache.quantity)).filter(
                    SalesCache.item_name == recipe.name,
                    SalesCache.timestamp >= start_date
                ).scalar() or 0

                if sales_count > 0:
                    total_revenue = recipe.sale_price * sales_count
                    sales_data_for_pdf.append({
                        'Item': recipe.name,
                        'Units Sold': sales_count,
                        'Sale Price': recipe.sale_price,
                        'Total Revenue': total_revenue
                    })

            if sales_data_for_pdf:
                df_pdf = pd.DataFrame(sales_data_for_pdf)
                pdf_bytes = generate_sales_report(df_pdf, start_date, end_date)

                st.download_button(
                    label="💾 Download Sales Report PDF",
                    data=pdf_bytes,
                    file_name=f"sales_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("No sales data available to generate report.")

    finally:
        close_session(session)