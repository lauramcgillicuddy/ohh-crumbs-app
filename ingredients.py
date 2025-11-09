import streamlit as st
from database import get_session, close_session
from models import Ingredient, Supplier
from datetime import datetime

def show_ingredients():
    st.title("🥖 Ingredient Management")
    
    session = get_session()
    
    try:
        tab1, tab2, tab3, tab4 = st.tabs(["📋 View Ingredients", "➕ Add Ingredient", "📦 Update Stock", "📱 Barcode Scanner"])
        
        with tab1:
            st.subheader("Current Ingredients")
            
            ingredients = session.query(Ingredient).order_by(Ingredient.name).all()
            
            if ingredients:
                for ingredient in ingredients:
                    with st.expander(f"{ingredient.name} ({ingredient.unit})"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**Cost per {ingredient.unit}:** ${ingredient.cost_per_unit:.2f}")
                            st.write(f"**Current Stock:** {ingredient.current_stock:.2f} {ingredient.unit}")
                        
                        with col2:
                            supplier_name = ingredient.supplier
                            if ingredient.supplier_id:
                                supplier_obj = session.query(Supplier).get(ingredient.supplier_id)
                                if supplier_obj:
                                    supplier_name = supplier_obj.name
                            st.write(f"**Supplier:** {supplier_name or 'Not set'}")
                            st.write(f"**Lead Time:** {ingredient.supplier_lead_time_days} days")
                        
                        with col3:
                            st.write(f"**Last Updated:** {ingredient.last_updated.strftime('%Y-%m-%d')}")
                        
                        col_edit1, col_edit2 = st.columns([1, 1])
                        
                        with col_edit1:
                            if st.button(f"✏️ Edit", key=f"edit_{ingredient.id}"):
                                st.session_state[f'editing_{ingredient.id}'] = True
                        
                        with col_edit2:
                            if st.button(f"🗑️ Delete", key=f"delete_{ingredient.id}"):
                                session.delete(ingredient)
                                session.commit()
                                st.success(f"Deleted {ingredient.name}")
                                st.rerun()
                        
                        if st.session_state.get(f'editing_{ingredient.id}', False):
                            with st.form(key=f"edit_form_{ingredient.id}"):
                                st.write("**Edit Ingredient**")
                                
                                new_cost = st.number_input("Cost per unit", value=float(ingredient.cost_per_unit), min_value=0.0, step=0.01)
                                
                                suppliers = session.query(Supplier).order_by(Supplier.name).all()
                                supplier_options = ["None"] + [s.name for s in suppliers]
                                
                                current_supplier_name = "None"
                                if ingredient.supplier_id:
                                    supplier_obj = session.query(Supplier).get(ingredient.supplier_id)
                                    if supplier_obj:
                                        current_supplier_name = supplier_obj.name
                                elif ingredient.supplier:
                                    current_supplier_name = "None"
                                
                                current_index = 0
                                if current_supplier_name in supplier_options:
                                    current_index = supplier_options.index(current_supplier_name)
                                
                                selected_supplier = st.selectbox("Supplier", supplier_options, index=current_index)
                                new_lead_time = st.number_input("Lead time (days)", value=ingredient.supplier_lead_time_days, min_value=1, step=1)
                                
                                col_submit, col_cancel = st.columns(2)
                                
                                with col_submit:
                                    if st.form_submit_button("💾 Save"):
                                        ingredient.cost_per_unit = new_cost
                                        
                                        if selected_supplier == "None":
                                            ingredient.supplier_id = None
                                            ingredient.supplier = None
                                        else:
                                            supplier_obj = session.query(Supplier).filter(Supplier.name == selected_supplier).first()
                                            if supplier_obj:
                                                ingredient.supplier_id = supplier_obj.id
                                                ingredient.supplier = supplier_obj.name
                                                ingredient.supplier_lead_time_days = supplier_obj.lead_time_days
                                        
                                        if not ingredient.supplier_id:
                                            ingredient.supplier_lead_time_days = new_lead_time
                                        
                                        ingredient.last_updated = datetime.utcnow()
                                        session.commit()
                                        st.session_state[f'editing_{ingredient.id}'] = False
                                        st.success("Updated!")
                                        st.rerun()
                                
                                with col_cancel:
                                    if st.form_submit_button("❌ Cancel"):
                                        st.session_state[f'editing_{ingredient.id}'] = False
                                        st.rerun()
            else:
                st.info("No ingredients added yet. Add your first ingredient in the 'Add Ingredient' tab!")
        
        with tab2:
            st.subheader("Add New Ingredient")
            
            with st.form("add_ingredient_form"):
                name = st.text_input("Ingredient Name *", placeholder="e.g., All-Purpose Flour")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    unit = st.selectbox("Unit of Measurement *", 
                        ["kg", "g", "lb", "oz", "L", "mL", "cups", "tbsp", "tsp", "units"])
                
                with col2:
                    cost_per_unit = st.number_input("Cost per Unit *", min_value=0.0, step=0.01, value=0.0)
                
                col3, col4 = st.columns(2)
                
                with col3:
                    initial_stock = st.number_input("Initial Stock Quantity", min_value=0.0, step=0.1, value=0.0)
                
                with col4:
                    suppliers = session.query(Supplier).order_by(Supplier.name).all()
                    supplier_options = ["None"] + [s.name for s in suppliers]
                    selected_supplier = st.selectbox("Supplier", supplier_options, 
                        help="Select from existing suppliers or choose 'None'")
                
                lead_time = st.number_input("Supplier Lead Time (days)", min_value=1, step=1, value=7,
                    help="How many days it takes to receive an order from this supplier (only used if no supplier selected)")
                
                submitted = st.form_submit_button("➕ Add Ingredient")
                
                if submitted:
                    if not name or not unit:
                        st.error("Please fill in all required fields (marked with *)")
                    else:
                        existing = session.query(Ingredient).filter_by(name=name).first()
                        
                        if existing:
                            st.error(f"Ingredient '{name}' already exists!")
                        else:
                            supplier_id = None
                            supplier_name = None
                            supplier_lead_time = lead_time
                            
                            if selected_supplier != "None":
                                supplier_obj = session.query(Supplier).filter(Supplier.name == selected_supplier).first()
                                if supplier_obj:
                                    supplier_id = supplier_obj.id
                                    supplier_name = supplier_obj.name
                                    supplier_lead_time = supplier_obj.lead_time_days
                            
                            new_ingredient = Ingredient(
                                name=name,
                                unit=unit,
                                cost_per_unit=cost_per_unit,
                                current_stock=initial_stock,
                                supplier_id=supplier_id,
                                supplier=supplier_name,
                                supplier_lead_time_days=supplier_lead_time
                            )
                            
                            session.add(new_ingredient)
                            session.commit()
                            st.success(f"✅ Added '{name}' to ingredients!")
                            st.rerun()
        
        with tab3:
            st.subheader("Update Stock Levels")
            
            ingredients = session.query(Ingredient).order_by(Ingredient.name).all()
            
            if ingredients:
                with st.form("update_stock_form"):
                    st.write("Adjust stock quantities (e.g., after receiving a delivery or taking inventory)")
                    
                    updates = {}
                    
                    for ingredient in ingredients:
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**{ingredient.name}**")
                        
                        with col2:
                            st.write(f"Current: {ingredient.current_stock:.2f} {ingredient.unit}")
                        
                        with col3:
                            new_stock = st.number_input(
                                f"New quantity",
                                min_value=0.0,
                                step=0.1,
                                value=float(ingredient.current_stock),
                                key=f"stock_{ingredient.id}",
                                label_visibility="collapsed"
                            )
                            updates[ingredient.id] = new_stock
                    
                    if st.form_submit_button("💾 Update All Stock Levels"):
                        for ingredient_id, new_stock in updates.items():
                            ingredient = session.query(Ingredient).filter_by(id=ingredient_id).first()
                            if ingredient:
                                ingredient.current_stock = new_stock
                                ingredient.last_updated = datetime.utcnow()
                        
                        session.commit()
                        st.success("✅ Stock levels updated!")
                        st.rerun()
            else:
                st.info("No ingredients available. Add ingredients first!")
        
        with tab4:
            st.subheader("📱 Barcode/QR Scanner for Inventory")
            
            st.info("💡 **How it works:** Scan a barcode or QR code to quickly look up and update ingredient inventory. Each ingredient can have a unique code.")
            
            from streamlit_qrcode_scanner import qrcode_scanner
            
            col_scan1, col_scan2 = st.columns([1, 1])
            
            with col_scan1:
                st.write("**Scan a Code:**")
                scanned_code = qrcode_scanner(key='ingredient_scanner')
            
            with col_scan2:
                st.write("**Manual Entry:**")
                manual_code = st.text_input("Or enter code manually", placeholder="e.g., FLOUR001", key="manual_barcode")
            
            barcode_value = scanned_code if scanned_code else manual_code
            
            if barcode_value:
                st.divider()
                st.write(f"**Scanned/Entered Code:** `{barcode_value}`")
                
                ingredient = session.query(Ingredient).filter(Ingredient.name.ilike(f"%{barcode_value}%")).first()
                
                if not ingredient:
                    ingredient = session.query(Ingredient).filter(Ingredient.id == barcode_value).first()
                
                if ingredient:
                    st.success(f"✅ Found: **{ingredient.name}**")
                    
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.write(f"**Current Stock:** {ingredient.current_stock:.2f} {ingredient.unit}")
                        st.write(f"**Cost per Unit:** ${ingredient.cost_per_unit:.2f}")
                    
                    with col_info2:
                        if ingredient.supplier_id:
                            supplier_obj = session.query(Supplier).get(ingredient.supplier_id)
                            if supplier_obj:
                                st.write(f"**Supplier:** {supplier_obj.name}")
                        else:
                            st.write(f"**Supplier:** {ingredient.supplier or 'Not set'}")
                        st.write(f"**Lead Time:** {ingredient.supplier_lead_time_days} days")
                    
                    st.divider()
                    
                    st.write("**Quick Update:**")
                    
                    update_type = st.radio(
                        "Action",
                        ["Add to Stock", "Remove from Stock", "Set New Stock Level"],
                        horizontal=True,
                        key="update_type"
                    )
                    
                    if update_type == "Add to Stock":
                        quantity_change = st.number_input(
                            f"Quantity to add ({ingredient.unit})",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key="add_qty"
                        )
                        
                        if st.button("➕ Add to Stock"):
                            ingredient.current_stock += quantity_change
                            ingredient.last_updated = datetime.utcnow()
                            session.commit()
                            st.success(f"✅ Added {quantity_change:.2f} {ingredient.unit}. New stock: {ingredient.current_stock:.2f} {ingredient.unit}")
                            st.rerun()
                    
                    elif update_type == "Remove from Stock":
                        quantity_change = st.number_input(
                            f"Quantity to remove ({ingredient.unit})",
                            min_value=0.0,
                            step=0.1,
                            value=0.0,
                            key="remove_qty"
                        )
                        
                        if st.button("➖ Remove from Stock"):
                            new_stock = max(0, ingredient.current_stock - quantity_change)
                            ingredient.current_stock = new_stock
                            ingredient.last_updated = datetime.utcnow()
                            session.commit()
                            st.success(f"✅ Removed {quantity_change:.2f} {ingredient.unit}. New stock: {ingredient.current_stock:.2f} {ingredient.unit}")
                            st.rerun()
                    
                    else:
                        new_stock_level = st.number_input(
                            f"New stock level ({ingredient.unit})",
                            min_value=0.0,
                            step=0.1,
                            value=float(ingredient.current_stock),
                            key="set_stock"
                        )
                        
                        if st.button("💾 Set Stock Level"):
                            ingredient.current_stock = new_stock_level
                            ingredient.last_updated = datetime.utcnow()
                            session.commit()
                            st.success(f"✅ Stock set to {new_stock_level:.2f} {ingredient.unit}")
                            st.rerun()
                
                else:
                    st.warning(f"❌ No ingredient found matching code: `{barcode_value}`")
                    st.write("**Tips:**")
                    st.write("- Make sure the barcode/QR code contains the ingredient name or ID")
                    st.write("- You can create custom QR codes for your ingredients using free online tools")
                    st.write("- Try searching by ingredient name instead")
            else:
                st.write("---")
                st.write("**📝 Quick Reference:**")
                st.write("You can assign barcodes/QR codes to your ingredients for faster scanning:")
                
                ingredients = session.query(Ingredient).order_by(Ingredient.name).all()
                if ingredients:
                    st.write("**Current Ingredients:**")
                    for ing in ingredients[:10]:
                        st.write(f"- {ing.name} (ID: {ing.id})")
                    
                    if len(ingredients) > 10:
                        st.write(f"...and {len(ingredients) - 10} more")
    
    finally:
        close_session(session)
