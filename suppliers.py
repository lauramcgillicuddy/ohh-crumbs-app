import streamlit as st
from styling import inject_custom_css, render_page_header
from database import get_session, close_session
from models import Supplier, Ingredient, SupplierOrder, SupplierOrderItem
from datetime import datetime, timedelta
import pandas as pd

def show_suppliers():
    inject_custom_css()

    render_page_header("📦 Supplier Management", "MANAGE YOUR VENDORS")

    session = get_session()

    try:
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Suppliers", "📝 Orders", "📦 Create Order", "➕ Add Supplier"])

        with tab1:
            st.subheader("Active Suppliers")

            suppliers = session.query(Supplier).order_by(Supplier.name).all()

            if suppliers:
                for supplier in suppliers:
                    with st.expander(f"**{supplier.name}** - Lead Time: {supplier.lead_time_days} days"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Contact:** {supplier.contact_name or 'N/A'}")
                            st.write(f"**Email:** {supplier.email or 'N/A'}")
                            st.write(f"**Phone:** {supplier.phone or 'N/A'}")

                        with col2:
                            st.write(f"**Address:** {supplier.address or 'N/A'}")
                            st.write(f"**Lead Time:** {supplier.lead_time_days} days")

                        if supplier.notes:
                            st.write(f"**Notes:** {supplier.notes}")

                        ingredients = session.query(Ingredient).filter(
                            Ingredient.supplier_id == supplier.id
                        ).all()

                        if ingredients:
                            st.write(f"**Supplies {len(ingredients)} ingredients:**")
                            st.write(", ".join([ing.name for ing in ingredients]))

                        orders = session.query(SupplierOrder).filter(
                            SupplierOrder.supplier_id == supplier.id
                        ).order_by(SupplierOrder.order_date.desc()).limit(5).all()

                        if orders:
                            st.write(f"**Recent Orders ({len(orders)}):**")
                            for order in orders:
                                st.write(f"- {order.order_date.strftime('%Y-%m-%d')}: £{order.total_cost:.2f} ({order.status})")

                        st.divider()

                        col_edit, col_delete = st.columns(2)

                        with col_edit:
                            if st.button(f"✏️ Edit", key=f"edit_{supplier.id}"):
                                st.session_state[f'editing_supplier_{supplier.id}'] = True
                                st.rerun()

                        with col_delete:
                            if st.button(f"🗑️ Delete", key=f"delete_{supplier.id}"):
                                try:
                                    session.query(Ingredient).filter(
                                        Ingredient.supplier_id == supplier.id
                                    ).update({'supplier_id': None})

                                    session.delete(supplier)
                                    session.commit()
                                    st.success(f"Deleted supplier: {supplier.name}")
                                    st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"Error deleting supplier: {str(e)}")

                        if st.session_state.get(f'editing_supplier_{supplier.id}'):
                            st.subheader(f"Edit {supplier.name}")

                            with st.form(f"edit_form_{supplier.id}"):
                                new_name = st.text_input("Supplier Name", value=supplier.name)
                                new_contact = st.text_input("Contact Name", value=supplier.contact_name or "")
                                new_email = st.text_input("Email", value=supplier.email or "")
                                new_phone = st.text_input("Phone", value=supplier.phone or "")
                                new_address = st.text_area("Address", value=supplier.address or "")
                                new_lead_time = st.number_input("Lead Time (days)", min_value=1, value=supplier.lead_time_days)
                                new_notes = st.text_area("Notes", value=supplier.notes or "")

                                col_save, col_cancel = st.columns(2)

                                with col_save:
                                    submitted = st.form_submit_button("💾 Save Changes")

                                with col_cancel:
                                    cancelled = st.form_submit_button("❌ Cancel")

                                if submitted:
                                    try:
                                        supplier.name = new_name
                                        supplier.contact_name = new_contact
                                        supplier.email = new_email
                                        supplier.phone = new_phone
                                        supplier.address = new_address
                                        supplier.lead_time_days = new_lead_time
                                        supplier.notes = new_notes

                                        session.commit()
                                        st.success(f"Updated supplier: {new_name}")
                                        del st.session_state[f'editing_supplier_{supplier.id}']
                                        st.rerun()
                                    except Exception as e:
                                        session.rollback()
                                        st.error(f"Error updating supplier: {str(e)}")

                                if cancelled:
                                    del st.session_state[f'editing_supplier_{supplier.id}']
                                    st.rerun()
            else:
                st.info("📭 No suppliers yet. Add your first supplier in the 'Add Supplier' tab.")

        with tab2:
            st.subheader("Order History")

            orders = session.query(SupplierOrder).order_by(
                SupplierOrder.order_date.desc()
            ).all()

            if orders:
                for order in orders:
                    supplier = session.query(Supplier).get(order.supplier_id)

                    status_emoji = {
                        'pending': '⏳',
                        'ordered': '📤',
                        'delivered': '✅',
                        'cancelled': '❌'
                    }.get(order.status, '📦')

                    with st.expander(f"{status_emoji} Order #{order.id} - {supplier.name if supplier else 'Unknown'} - £{order.total_cost:.2f}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Order Date:** {order.order_date.strftime('%Y-%m-%d %H:%M')}")
                            st.write(f"**Status:** {order.status.title()}")
                            if order.expected_delivery_date:
                                st.write(f"**Expected Delivery:** {order.expected_delivery_date.strftime('%Y-%m-%d')}")

                        with col2:
                            if order.actual_delivery_date:
                                st.write(f"**Delivered:** {order.actual_delivery_date.strftime('%Y-%m-%d')}")
                            st.write(f"**Total Cost:** £{order.total_cost:.2f}")

                        if order.notes:
                            st.write(f"**Notes:** {order.notes}")

                        if order.order_items:
                            st.write("**Items:**")
                            items_data = []
                            for item in order.order_items:
                                ingredient = session.query(Ingredient).get(item.ingredient_id)
                                if ingredient:
                                    items_data.append({
                                        'Ingredient': ingredient.name,
                                        'Quantity': f"{item.quantity} {ingredient.unit}",
                                        'Unit Cost': f"£{item.unit_cost:.2f}",
                                        'Total': f"£{item.total_cost:.2f}"
                                    })

                            if items_data:
                                df = pd.DataFrame(items_data)
                                st.dataframe(df, use_container_width=True, hide_index=True)

                        if order.status != 'delivered':
                            col_status1, col_status2 = st.columns(2)

                            with col_status1:
                                if st.button("✅ Mark Delivered", key=f"deliver_{order.id}"):
                                    order.status = 'delivered'
                                    order.actual_delivery_date = datetime.utcnow()

                                    for item in order.order_items:
                                        ingredient = session.query(Ingredient).get(item.ingredient_id)
                                        if ingredient:
                                            ingredient.current_stock += item.quantity

                                    session.commit()
                                    st.success("Order marked as delivered and stock updated!")
                                    st.rerun()

                            with col_status2:
                                if st.button("❌ Cancel Order", key=f"cancel_{order.id}"):
                                    order.status = 'cancelled'
                                    session.commit()
                                    st.success("Order cancelled")
                                    st.rerun()
            else:
                st.info("📭 No orders yet. Create a new order in the 'Create Order' tab!")

        with tab3:
            st.subheader("📦 Create New Supplier Order")
            st.info("💡 Create a purchase order for ingredients. When it arrives, mark it as delivered to automatically update inventory!")

            # Select supplier
            suppliers = session.query(Supplier).order_by(Supplier.name).all()

            if not suppliers:
                st.warning("⚠️ No suppliers available. Please add a supplier first in the 'Add Supplier' tab.")
            else:
                supplier_options = {s.name: s for s in suppliers}
                selected_supplier_name = st.selectbox(
                    "Select Supplier *",
                    options=list(supplier_options.keys()),
                    help="Choose the supplier you're ordering from"
                )

                selected_supplier = supplier_options[selected_supplier_name]

                st.write(f"**Lead Time:** {selected_supplier.lead_time_days} days")

                st.markdown("---")
                st.markdown("### 📝 Order Details")

                # Order dates
                col_date1, col_date2 = st.columns(2)

                with col_date1:
                    order_date = st.date_input(
                        "Order Date",
                        value=datetime.now().date(),
                        help="Date you're placing this order"
                    )

                with col_date2:
                    expected_delivery = order_date + timedelta(days=selected_supplier.lead_time_days)
                    expected_delivery_date = st.date_input(
                        "Expected Delivery Date",
                        value=expected_delivery,
                        help="When you expect to receive this order"
                    )

                order_notes = st.text_area(
                    "Order Notes (optional)",
                    placeholder="e.g., Spoke with John, confirmed delivery time, etc."
                )

                st.markdown("---")
                st.markdown("### 🛒 Order Items")

                # Get ingredients from this supplier (or all ingredients)
                supplier_ingredients = session.query(Ingredient).filter(
                    Ingredient.supplier_id == selected_supplier.id
                ).order_by(Ingredient.name).all()

                # If supplier has no assigned ingredients, show all ingredients
                if not supplier_ingredients:
                    st.info(f"💡 No ingredients are assigned to {selected_supplier.name} yet. Showing all ingredients.")
                    supplier_ingredients = session.query(Ingredient).order_by(Ingredient.name).all()

                if not supplier_ingredients:
                    st.warning("⚠️ No ingredients in the system. Please add ingredients first!")
                else:
                    # Initialize order items in session state
                    if 'order_items' not in st.session_state:
                        st.session_state['order_items'] = []

                    # Add item section
                    with st.expander("➕ Add Items to Order", expanded=True):
                        col_ing, col_qty, col_add = st.columns([3, 2, 1])

                        with col_ing:
                            ingredient_options = {f"{ing.name} ({ing.unit})": ing for ing in supplier_ingredients}
                            selected_ingredient_name = st.selectbox(
                                "Ingredient",
                                options=list(ingredient_options.keys()),
                                key="new_order_item_ingredient"
                            )
                            selected_ingredient = ingredient_options[selected_ingredient_name]

                        with col_qty:
                            quantity = st.number_input(
                                f"Quantity ({selected_ingredient.unit})",
                                min_value=0.1,
                                value=1.0,
                                step=0.1,
                                key="new_order_item_quantity"
                            )

                        with col_add:
                            st.write("")  # Spacing
                            st.write("")  # Spacing
                            if st.button("➕ Add Item", use_container_width=True):
                                # Check if item already in order
                                existing_item = next(
                                    (item for item in st.session_state['order_items']
                                     if item['ingredient_id'] == selected_ingredient.id),
                                    None
                                )

                                if existing_item:
                                    # Update quantity
                                    existing_item['quantity'] += quantity
                                    st.success(f"Updated quantity for {selected_ingredient.name}")
                                else:
                                    # Add new item
                                    st.session_state['order_items'].append({
                                        'ingredient_id': selected_ingredient.id,
                                        'ingredient_name': selected_ingredient.name,
                                        'unit': selected_ingredient.unit,
                                        'quantity': quantity,
                                        'unit_cost': selected_ingredient.cost_per_unit,
                                        'total_cost': quantity * selected_ingredient.cost_per_unit
                                    })
                                    st.success(f"Added {selected_ingredient.name} to order")
                                st.rerun()

                    # Display current order items
                    if st.session_state['order_items']:
                        st.markdown("### 📋 Current Order")

                        order_total = 0.0
                        items_to_remove = []

                        for idx, item in enumerate(st.session_state['order_items']):
                            col_item, col_qty, col_cost, col_remove = st.columns([3, 2, 2, 1])

                            with col_item:
                                st.write(f"**{item['ingredient_name']}**")

                            with col_qty:
                                st.write(f"{item['quantity']} {item['unit']}")

                            with col_cost:
                                st.write(f"£{item['total_cost']:.2f}")
                                order_total += item['total_cost']

                            with col_remove:
                                if st.button("🗑️", key=f"remove_item_{idx}"):
                                    items_to_remove.append(idx)

                        # Remove items marked for deletion
                        for idx in sorted(items_to_remove, reverse=True):
                            st.session_state['order_items'].pop(idx)
                            st.rerun()

                        st.markdown("---")
                        st.markdown(f"### **Total Order Value: £{order_total:.2f}**")
                        st.markdown("---")

                        # Save order buttons
                        col_save1, col_save2, col_cancel = st.columns(3)

                        with col_save1:
                            if st.button("💾 Save as Pending", type="primary", use_container_width=True):
                                try:
                                    # Create order
                                    new_order = SupplierOrder(
                                        supplier_id=selected_supplier.id,
                                        order_date=datetime.combine(order_date, datetime.min.time()),
                                        expected_delivery_date=datetime.combine(expected_delivery_date, datetime.min.time()),
                                        status='pending',
                                        total_cost=order_total,
                                        notes=order_notes if order_notes else None
                                    )
                                    session.add(new_order)
                                    session.flush()

                                    # Add order items
                                    for item in st.session_state['order_items']:
                                        order_item = SupplierOrderItem(
                                            order_id=new_order.id,
                                            ingredient_id=item['ingredient_id'],
                                            quantity=item['quantity'],
                                            unit_cost=item['unit_cost'],
                                            total_cost=item['total_cost']
                                        )
                                        session.add(order_item)

                                    session.commit()
                                    st.success(f"✅ Order #{new_order.id} saved as PENDING!")
                                    st.info("💡 Go to the 'Orders' tab to mark it as delivered when it arrives.")

                                    # Clear order items
                                    st.session_state['order_items'] = []
                                    st.rerun()

                                except Exception as e:
                                    session.rollback()
                                    st.error(f"Error saving order: {str(e)}")

                        with col_save2:
                            if st.button("📤 Save as Ordered", type="secondary", use_container_width=True):
                                try:
                                    # Create order
                                    new_order = SupplierOrder(
                                        supplier_id=selected_supplier.id,
                                        order_date=datetime.combine(order_date, datetime.min.time()),
                                        expected_delivery_date=datetime.combine(expected_delivery_date, datetime.min.time()),
                                        status='ordered',
                                        total_cost=order_total,
                                        notes=order_notes if order_notes else None
                                    )
                                    session.add(new_order)
                                    session.flush()

                                    # Add order items
                                    for item in st.session_state['order_items']:
                                        order_item = SupplierOrderItem(
                                            order_id=new_order.id,
                                            ingredient_id=item['ingredient_id'],
                                            quantity=item['quantity'],
                                            unit_cost=item['unit_cost'],
                                            total_cost=item['total_cost']
                                        )
                                        session.add(order_item)

                                    session.commit()
                                    st.success(f"✅ Order #{new_order.id} saved as ORDERED!")
                                    st.info("💡 Mark as delivered in the 'Orders' tab when it arrives to update inventory.")

                                    # Clear order items
                                    st.session_state['order_items'] = []
                                    st.rerun()

                                except Exception as e:
                                    session.rollback()
                                    st.error(f"Error saving order: {str(e)}")

                        with col_cancel:
                            if st.button("🗑️ Clear Order", use_container_width=True):
                                st.session_state['order_items'] = []
                                st.rerun()
                    else:
                        st.info("👆 Add items to your order using the form above")

        with tab4:
            st.subheader("Add New Supplier")

            with st.form("add_supplier_form"):
                name = st.text_input(
                    "Supplier Name *",
                    placeholder="e.g., Andrew Ingredients Ltd"
                )
                contact_name = st.text_input("Contact Name", placeholder="e.g., John Smith")
                email = st.text_input(
                    "Email",
                    placeholder="e.g., sales@andrewingredients.com"
                )
                phone = st.text_input(
                    "Phone",
                    placeholder="e.g., (028) 9267 2525"
                )
                address = st.text_area(
                    "Address",
                    placeholder="27 Ferguson Drive\nLisburn, BT28 2EX"
                )
                lead_time = st.number_input("Lead Time (days)", min_value=1, value=7, help="Typical delivery time in days")
                notes = st.text_area("Notes", placeholder="Any special instructions or information")

                submitted = st.form_submit_button("➕ Add Supplier", use_container_width=True)

                if submitted:
                    if not name:
                        st.error("Supplier name is required")
                    else:
                        try:
                            existing = session.query(Supplier).filter(Supplier.name == name).first()
                            if existing:
                                st.error(f"Supplier '{name}' already exists")
                            else:
                                new_supplier = Supplier(
                                    name=name,
                                    contact_name=contact_name if contact_name else None,
                                    email=email if email else None,
                                    phone=phone if phone else None,
                                    address=address if address else None,
                                    lead_time_days=lead_time,
                                    notes=notes if notes else None
                                )

                                session.add(new_supplier)
                                session.commit()

                                st.success(f"✅ Added supplier: {name}")
                                st.rerun()
                        except Exception as e:
                            session.rollback()
                            st.error(f"Error adding supplier: {str(e)}")

    finally:
        close_session(session)

if __name__ == "__main__":
    show_suppliers()
