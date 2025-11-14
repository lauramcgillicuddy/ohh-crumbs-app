import streamlit as st
from styling import inject_custom_css, render_page_header
from database import get_session, close_session
from models import Ingredient, Supplier, SupplierOrder, SupplierOrderItem
from utils import get_low_stock_ingredients, calculate_reorder_threshold
import plotly.express as px
import pandas as pd
from pdf_reports import generate_inventory_report
from datetime import datetime, timedelta

def show_inventory_alerts():
    inject_custom_css()

    render_page_header("🔔 Inventory Alerts", "STAY STOCKED UP")
    
    session = get_session()
    
    try:
        st.subheader("Smart Reorder Alerts")
        
        st.info("📊 Reorder thresholds are automatically calculated based on your daily usage rate and supplier lead time, plus a 3-day safety buffer.")
        
        low_stock = get_low_stock_ingredients(session)
        
        if low_stock:
            critical = [item for item in low_stock if item['urgency'] == 'critical']
            warning = [item for item in low_stock if item['urgency'] == 'warning']
            notice = [item for item in low_stock if item['urgency'] == 'notice']
            
            if critical:
                st.error(f"🚨 **CRITICAL:** {len(critical)} ingredient(s) need immediate ordering!")
                
                for item in critical:
                    ing = item['ingredient']
                    with st.expander(f"❗ {ing.name} - {item['days_remaining']:.1f} days remaining", expanded=True):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Current Stock", f"{item['current_stock']:.2f} {ing.unit}")
                        
                        with col2:
                            st.metric("Daily Usage", f"{item['daily_usage']:.2f} {ing.unit}")
                        
                        with col3:
                            st.metric("Reorder Point", f"{item['reorder_point']:.2f} {ing.unit}")
                        
                        days_remaining = item['days_remaining']
                        
                        if days_remaining < 1:
                            st.error(f"⚠️ **URGENT:** Less than 1 day of stock remaining!")
                        else:
                            st.warning(f"⏰ Estimated {days_remaining:.1f} days until stockout")
                        
                        suggested_order = item['daily_usage'] * (ing.supplier_lead_time_days + 7)
                        st.write(f"**Suggested order quantity:** {suggested_order:.2f} {ing.unit}")
                        st.write(f"**Supplier:** {ing.supplier or 'Not specified'}")
                        st.write(f"**Lead time:** {ing.supplier_lead_time_days} days")
            
            if warning:
                st.warning(f"⚠️ **WARNING:** {len(warning)} ingredient(s) running low")
                
                for item in warning:
                    ing = item['ingredient']
                    with st.expander(f"⚠️ {ing.name} - {item['days_remaining']:.1f} days remaining"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Current Stock", f"{item['current_stock']:.2f} {ing.unit}")
                        
                        with col2:
                            st.metric("Daily Usage", f"{item['daily_usage']:.2f} {ing.unit}")
                        
                        with col3:
                            st.metric("Reorder Point", f"{item['reorder_point']:.2f} {ing.unit}")
                        
                        suggested_order = item['daily_usage'] * (ing.supplier_lead_time_days + 7)
                        st.write(f"**Suggested order:** {suggested_order:.2f} {ing.unit}")
                        st.write(f"**Supplier:** {ing.supplier or 'Not specified'}")
            
            if notice:
                with st.expander(f"ℹ️ {len(notice)} ingredient(s) approaching reorder point"):
                    for item in notice:
                        ing = item['ingredient']
                        st.write(f"**{ing.name}**: {item['current_stock']:.2f} {ing.unit} remaining ({item['days_remaining']:.1f} days)")
            
            st.divider()
            
            st.subheader("📦 Automated Ordering")
            
            st.write("Create supplier orders automatically based on low stock levels.")
            
            items_to_order = critical + warning
            
            if items_to_order:
                suppliers_dict = {}
                for item in items_to_order:
                    ing = item['ingredient']
                    if ing.supplier_id:
                        supplier = session.query(Supplier).get(ing.supplier_id)
                        if supplier:
                            if supplier.id not in suppliers_dict:
                                suppliers_dict[supplier.id] = {
                                    'supplier': supplier,
                                    'items': []
                                }
                            suggested_qty = item['daily_usage'] * (ing.supplier_lead_time_days + 7)
                            suppliers_dict[supplier.id]['items'].append({
                                'ingredient': ing,
                                'quantity': suggested_qty,
                                'daily_usage': item['daily_usage']
                            })
                
                if suppliers_dict:
                    st.write(f"**{len(suppliers_dict)} supplier(s) have items to order:**")
                    
                    for supplier_id, data in suppliers_dict.items():
                        supplier = data['supplier']
                        items = data['items']
                        
                        with st.expander(f"📦 {supplier.name} - {len(items)} items"):
                            total_order_cost = 0
                            
                            for item_data in items:
                                ing = item_data['ingredient']
                                qty = item_data['quantity']
                                cost = qty * ing.cost_per_unit
                                total_order_cost += cost
                                
                                st.write(f"- **{ing.name}**: {qty:.2f} {ing.unit} @ £{ing.cost_per_unit:.2f} = £{cost:.2f}")
                            
                            st.write(f"**Total Order Cost:** £{total_order_cost:.2f}")
                            st.write(f"**Delivery Time:** {supplier.lead_time_days} days")
                            
                            if st.button(f"✅ Create Order for {supplier.name}", key=f"order_{supplier_id}"):
                                expected_delivery = datetime.utcnow() + timedelta(days=supplier.lead_time_days)
                                
                                new_order = SupplierOrder(
                                    supplier_id=supplier.id,
                                    order_date=datetime.utcnow(),
                                    expected_delivery_date=expected_delivery,
                                    status='pending',
                                    total_cost=total_order_cost,
                                    notes=f"Auto-generated order for {len(items)} low-stock items"
                                )
                                session.add(new_order)
                                session.flush()
                                
                                for item_data in items:
                                    ing = item_data['ingredient']
                                    qty = item_data['quantity']
                                    
                                    order_item = SupplierOrderItem(
                                        order_id=new_order.id,
                                        ingredient_id=ing.id,
                                        quantity=qty,
                                        unit_cost=ing.cost_per_unit,
                                        total_cost=qty * ing.cost_per_unit
                                    )
                                    session.add(order_item)
                                
                                session.commit()
                                
                                st.success(f"✅ Order #{new_order.id} created for {supplier.name}!")
                                st.info(f"📧 **Note:** In production, an email/SMS notification would be sent to {supplier.email or supplier.phone or 'the supplier'}.")
                                st.rerun()
                else:
                    st.info("💡 Assign suppliers to ingredients to enable automated ordering.")
            else:
                st.info("No critical or warning-level items to order at this time.")
        else:
            st.success("✅ All ingredients are well-stocked!")
        
        st.divider()
        
        st.subheader("📊 Inventory Status Overview")
        
        all_ingredients = session.query(Ingredient).all()
        
        if all_ingredients:
            inventory_data = []
            
            for ing in all_ingredients:
                reorder_point, daily_usage = calculate_reorder_threshold(session, ing)
                days_remaining = ing.current_stock / daily_usage if daily_usage > 0 else 999
                
                stock_status = 'Critical' if days_remaining < 2 else 'Low' if days_remaining < 5 else 'Warning' if days_remaining < 10 else 'Good'
                
                inventory_data.append({
                    'Ingredient': ing.name,
                    'Current Stock': ing.current_stock,
                    'Unit': ing.unit,
                    'Daily Usage': daily_usage,
                    'Days Remaining': min(days_remaining, 30),
                    'Reorder Point': reorder_point,
                    'Status': stock_status
                })
            
            df = pd.DataFrame(inventory_data)
            
            if not df.empty:
                status_colors = {
                    'Critical': '#d62728',
                    'Low': '#ff7f0e',
                    'Warning': '#ffdd57',
                    'Good': '#2ca02c'
                }
                
                df['Color'] = df['Status'].map(status_colors)
                
                fig = px.bar(
                    df.sort_values('Days Remaining'),
                    x='Days Remaining',
                    y='Ingredient',
                    orientation='h',
                    title='Days of Stock Remaining',
                    color='Status',
                    color_discrete_map=status_colors,
                    labels={'Days Remaining': 'Days of Stock Remaining'}
                )
                
                fig.add_vline(x=5, line_dash="dash", line_color="orange", 
                            annotation_text="5-day warning threshold")
                fig.add_vline(x=2, line_dash="dash", line_color="red",
                            annotation_text="2-day critical threshold")
                
                fig.update_layout(height=max(400, len(df) * 30))
                st.plotly_chart(fig, use_container_width=True)
                
                st.write("---")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Inventory Status Summary**")
                    status_counts = df['Status'].value_counts()
                    for status, count in status_counts.items():
                        st.write(f"- {status}: {count} items")
                
                with col2:
                    st.write("**Top 5 Fastest Moving Items**")
                    top_movers = df.nsmallest(5, 'Days Remaining')[['Ingredient', 'Days Remaining']]
                    for _, row in top_movers.iterrows():
                        st.write(f"- {row['Ingredient']}: {row['Days Remaining']:.1f} days")
                
                st.divider()
                
                st.subheader("📄 Export Inventory Report")
                
                if st.button("📥 Generate PDF Inventory Report"):
                    ingredients = session.query(Ingredient).all()
                    ingredients_df = pd.DataFrame([{
                        'name': ing.name,
                        'unit': ing.unit,
                        'current_stock': ing.current_stock,
                        'cost_per_unit': ing.cost_per_unit,
                        'supplier': ing.supplier
                    } for ing in ingredients])
                    
                    pdf_bytes = generate_inventory_report(ingredients_df, low_stock)
                    
                    st.download_button(
                        label="💾 Download Inventory Report PDF",
                        data=pdf_bytes,
                        file_name=f"inventory_report_{pd.Timestamp.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
        else:
            st.info("No ingredients in inventory yet. Add ingredients to start tracking!")
    
    finally:
        close_session(session)
