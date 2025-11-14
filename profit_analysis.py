import streamlit as st
from styling import inject_custom_css, render_page_header
from database import get_session, close_session
from models import Recipe, SalesCache, ProfitHistory
from utils import calculate_profit_margin
from sqlalchemy import func
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pdf_reports import generate_profit_report

def show_profit_analysis():
    inject_custom_css()

    render_page_header("💰 Profit Analysis", "TRACK YOUR MARGINS")
    
    session = get_session()
    
    try:
        recipes = session.query(Recipe).all()
        
        if not recipes:
            st.warning("⚠️ No recipes found. Add recipes first to see profit analysis!")
            return
        
        st.subheader("Item Profitability Overview")
        
        profit_data = []
        
        for recipe in recipes:
            cost, profit, margin = calculate_profit_margin(session, recipe.id)
            
            sales_count = session.query(func.sum(SalesCache.quantity)).filter(
                SalesCache.item_name == recipe.name
            ).scalar() or 0
            
            total_revenue = recipe.sale_price * sales_count
            total_profit = profit * sales_count
            
            profit_data.append({
                'Item': recipe.name,
                'Sale Price': recipe.sale_price,
                'Cost': cost,
                'Profit per Item': profit,
                'Margin %': margin,
                'Units Sold': sales_count,
                'Total Revenue': total_revenue,
                'Total Profit': total_profit
            })
        
        df = pd.DataFrame(profit_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Highest Margin Item",
                df.loc[df['Margin %'].idxmax(), 'Item'] if not df.empty else "N/A",
                f"{df['Margin %'].max():.1f}%" if not df.empty else "0%"
            )
        
        with col2:
            st.metric(
                "Most Profitable Item",
                df.loc[df['Total Profit'].idxmax(), 'Item'] if not df.empty and df['Total Profit'].max() > 0 else "N/A",
                f"£{df['Total Profit'].max():,.2f}" if not df.empty else "£0"
            )
        
        st.divider()
        
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Profitability vs Sales", "📈 Historical Trends", "📋 Detailed Table", "🎯 Insights"])
        
        with tab1:
            st.subheader("Profitability vs. Sales Volume")
            
            if not df.empty and df['Units Sold'].sum() > 0:
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df['Units Sold'],
                    y=df['Margin %'],
                    mode='markers+text',
                    marker=dict(
                        size=df['Total Profit'].apply(lambda x: max(10, min(50, x / 2))),
                        color=df['Margin %'],
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="Margin %")
                    ),
                    text=df['Item'],
                    textposition="top center",
                    hovertemplate='<b>%{text}</b><br>' +
                                  'Units Sold: %{x}<br>' +
                                  'Margin: %{y:.1f}%<br>' +
                                  '<extra></extra>'
                ))
                
                fig.update_layout(
                    title="Item Performance: Sales Volume vs Profit Margin",
                    xaxis_title="Units Sold",
                    yaxis_title="Profit Margin (%)",
                    height=500,
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                st.info("💡 **How to read this chart:** Items in the top-right are ideal (high sales + high margin). Items in the bottom-right sell well but have low margins. Items in the top-left have great margins but don't sell much.")
            else:
                st.info("📭 No sales data available yet. Connect to Square or add manual sales to see the analysis.")
            
            st.subheader("Profit Margin Comparison")
            
            fig_margin = px.bar(
                df.sort_values('Margin %', ascending=True),
                y='Item',
                x='Margin %',
                orientation='h',
                title='Profit Margin by Item',
                color='Margin %',
                color_continuous_scale='RdYlGn',
                labels={'Margin %': 'Profit Margin (%)'}
            )
            fig_margin.update_layout(height=max(400, len(df) * 30))
            st.plotly_chart(fig_margin, use_container_width=True)
        
        with tab2:
            st.subheader("📈 Profit Margin Trends Over Time")
            
            col_filter1, col_filter2 = st.columns(2)
            
            with col_filter1:
                days_range = st.selectbox("Time Range", [7, 14, 30, 60, 90, 180], index=3, key="trend_days")
            
            with col_filter2:
                recipe_names = ["All Items"] + [r.name for r in recipes]
                selected_recipe = st.selectbox("Filter by Item", recipe_names, key="trend_recipe")
            
            start_date = datetime.utcnow() - timedelta(days=days_range)
            
            query = session.query(ProfitHistory).filter(ProfitHistory.date >= start_date)
            
            if selected_recipe != "All Items":
                selected_recipe_obj = session.query(Recipe).filter(Recipe.name == selected_recipe).first()
                if selected_recipe_obj:
                    query = query.filter(ProfitHistory.recipe_id == selected_recipe_obj.id)
            
            history_data = query.order_by(ProfitHistory.date).all()
            
            if history_data:
                history_df = pd.DataFrame([{
                    'date': h.date,
                    'recipe_id': h.recipe_id,
                    'profit_margin': h.profit_margin,
                    'profit': h.profit,
                    'quantity': h.quantity_sold,
                    'sale_price': h.sale_price,
                    'cost': h.ingredient_cost
                } for h in history_data])
                
                recipe_lookup = {r.id: r.name for r in recipes}
                history_df['item_name'] = history_df['recipe_id'].map(recipe_lookup)
                
                daily_avg = history_df.groupby(history_df['date'].dt.date).agg({
                    'profit_margin': 'mean',
                    'profit': 'sum',
                    'quantity': 'sum'
                }).reset_index()
                
                fig_trend = go.Figure()
                
                fig_trend.add_trace(go.Scatter(
                    x=daily_avg['date'],
                    y=daily_avg['profit_margin'],
                    mode='lines+markers',
                    name='Avg Profit Margin',
                    line=dict(color='#2E86AB', width=3),
                    marker=dict(size=8)
                ))
                
                avg_margin = daily_avg['profit_margin'].mean()
                fig_trend.add_hline(
                    y=avg_margin,
                    line_dash="dash",
                    line_color="gray",
                    annotation_text=f"Avg: {avg_margin:.1f}%",
                    annotation_position="right"
                )
                
                fig_trend.update_layout(
                    title="Daily Average Profit Margin Trend",
                    xaxis_title="Date",
                    yaxis_title="Profit Margin (%)",
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
                
                if selected_recipe == "All Items":
                    st.subheader("Item-by-Item Trends")
                    
                    item_trends = history_df.groupby(['item_name', history_df['date'].dt.date]).agg({
                        'profit_margin': 'mean'
                    }).reset_index()
                    
                    fig_items = px.line(
                        item_trends,
                        x='date',
                        y='profit_margin',
                        color='item_name',
                        title='Profit Margin by Item Over Time',
                        labels={'profit_margin': 'Profit Margin (%)', 'date': 'Date', 'item_name': 'Item'}
                    )
                    fig_items.update_layout(height=400)
                    st.plotly_chart(fig_items, use_container_width=True)
                
                st.subheader("📊 Trend Statistics")
                
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                
                with col_stat1:
                    current_margin = daily_avg.iloc[-1]['profit_margin'] if len(daily_avg) > 0 else 0
                    previous_margin = daily_avg.iloc[0]['profit_margin'] if len(daily_avg) > 0 else 0
                    margin_change = current_margin - previous_margin
                    
                    st.metric(
                        "Margin Change",
                        f"{current_margin:.1f}%",
                        f"{margin_change:+.1f}%"
                    )
                
                with col_stat2:
                    total_profit = daily_avg['profit'].sum()
                    st.metric("Total Profit (Period)", f"£{total_profit:.2f}")
                
                with col_stat3:
                    total_quantity = daily_avg['quantity'].sum()
                    st.metric("Items Sold (Period)", f"{int(total_quantity)}")
                
                if len(daily_avg) >= 7:
                    recent_trend = daily_avg.tail(7)['profit_margin'].mean()
                    overall_avg = daily_avg['profit_margin'].mean()
                    
                    if recent_trend > overall_avg * 1.05:
                        st.success("📈 **Positive Trend:** Your profit margins are improving in recent days!")
                    elif recent_trend < overall_avg * 0.95:
                        st.warning("📉 **Declining Trend:** Your profit margins have decreased recently. Review ingredient costs and pricing.")
                    else:
                        st.info("➡️ **Stable Trend:** Your profit margins are relatively stable.")
            else:
                st.info("📭 No historical profit data available yet. Profit history is recorded automatically when sales are synced from Square.")
                
                st.write("**To populate historical data:**")
                st.write("1. Ensure you have recipes with ingredient costs set up")
                st.write("2. Sync sales data from Square in the Square Setup page")
                st.write("3. Historical profit data will be calculated and displayed here")
                
                if st.button("🔄 Calculate History from Existing Sales"):
                    sales = session.query(SalesCache).order_by(SalesCache.timestamp).all()
                    
                    if sales:
                        records_added = 0
                        
                        for sale in sales:
                            recipe = session.query(Recipe).filter(Recipe.name == sale.item_name).first()
                            
                            if recipe:
                                cost, profit, margin = calculate_profit_margin(session, recipe.id)
                                
                                existing = session.query(ProfitHistory).filter(
                                    ProfitHistory.recipe_id == recipe.id,
                                    ProfitHistory.date == sale.timestamp
                                ).first()
                                
                                if not existing:
                                    history_entry = ProfitHistory(
                                        recipe_id=recipe.id,
                                        date=sale.timestamp,
                                        sale_price=recipe.sale_price,
                                        ingredient_cost=cost,
                                        profit=profit,
                                        profit_margin=margin,
                                        quantity_sold=sale.quantity
                                    )
                                    session.add(history_entry)
                                    records_added += 1
                        
                        session.commit()
                        st.success(f"✅ Added {records_added} historical profit records!")
                        st.rerun()
                    else:
                        st.warning("No sales data found to calculate history from.")
        
        with tab3:
            st.subheader("Detailed Profit Analysis")
            
            display_df = df.copy()
            display_df['Sale Price'] = display_df['Sale Price'].apply(lambda x: f"£{x:.2f}")
            display_df['Cost'] = display_df['Cost'].apply(lambda x: f"£{x:.2f}")
            display_df['Profit per Item'] = display_df['Profit per Item'].apply(lambda x: f"£{x:.2f}")
            display_df['Margin %'] = display_df['Margin %'].apply(lambda x: f"{x:.1f}%")
            display_df['Total Revenue'] = display_df['Total Revenue'].apply(lambda x: f"£{x:.2f}")
            display_df['Total Profit'] = display_df['Total Profit'].apply(lambda x: f"£{x:.2f}")
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False)
            
            col_csv, col_pdf = st.columns(2)
            
            with col_csv:
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="profit_analysis.csv",
                    mime="text/csv"
                )
            
            with col_pdf:
                if st.button("📄 Generate PDF Report"):
                    pdf_bytes = generate_profit_report(df)
                    st.download_button(
                        label="💾 Download Profit Report PDF",
                        data=pdf_bytes,
                        file_name=f"profit_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        key="download_profit_pdf"
                    )
        
        with tab4:
            st.subheader("Business Insights")
            
            if not df.empty:
                avg_margin = df['Margin %'].mean()
                
                st.metric("Average Profit Margin", f"{avg_margin:.1f}%")
                
                st.write("---")
                
                high_margin = df[df['Margin %'] > 60]
                if not high_margin.empty:
                    st.success("🌟 **High Margin Items** (>60%)")
                    for _, row in high_margin.iterrows():
                        st.write(f"- **{row['Item']}**: {row['Margin %']:.1f}% margin, {int(row['Units Sold'])} sold")
                
                low_margin = df[df['Margin %'] < 30]
                if not low_margin.empty:
                    st.warning("⚠️ **Low Margin Items** (<30%)")
                    for _, row in low_margin.iterrows():
                        st.write(f"- **{row['Item']}**: {row['Margin %']:.1f}% margin, {int(row['Units Sold'])} sold")
                    st.write("\n**Recommendations:** Consider raising prices, reducing ingredient costs, or discontinuing these items.")
                
                if df['Units Sold'].sum() > 0:
                    best_seller = df.loc[df['Units Sold'].idxmax()]
                    most_profitable = df.loc[df['Total Profit'].idxmax()]
                    
                    if best_seller['Item'] != most_profitable['Item']:
                        st.info(f"💡 **Interesting Finding:** Your best-selling item is '{best_seller['Item']}' ({int(best_seller['Units Sold'])} sold), but '{most_profitable['Item']}' generates more total profit (£{most_profitable['Total Profit']:.2f} vs £{best_seller['Total Profit']:.2f}).")
                
                expensive_items = df[df['Cost'] > df['Cost'].median()]
                if not expensive_items.empty:
                    st.write("---")
                    st.write("**💸 High-Cost Items** (above median ingredient cost)")
                    for _, row in expensive_items.iterrows():
                        st.write(f"- **{row['Item']}**: £{row['Cost']:.2f} cost per item")
            else:
                st.info("Add recipes and sales data to see insights!")
    
    finally:
        close_session(session)
