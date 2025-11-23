"""
Equipment Maintenance Log
Track equipment maintenance, schedule next service, and monitor costs
"""

import streamlit as st
from database import get_session, close_session
from models import EquipmentLog
from styling import inject_custom_css, render_page_header
from datetime import datetime, timedelta
import pandas as pd


def show_equipment_maintenance():
    inject_custom_css()
    render_page_header("🔧 Equipment Maintenance", "KEEP YOUR BAKERY RUNNING SMOOTHLY")

    session = get_session()

    try:
        tab1, tab2, tab3 = st.tabs(["📋 Equipment List", "➕ Log Maintenance", "📊 Maintenance History"])

        with tab1:
            st.subheader("Equipment Status & Upcoming Maintenance")

            equipment_logs = session.query(EquipmentLog).order_by(EquipmentLog.next_maintenance_date).all()

            if not equipment_logs:
                st.info("No equipment logged yet. Add your first equipment maintenance record in the 'Log Maintenance' tab!")
            else:
                # Group by equipment name (get latest maintenance for each)
                equipment_dict = {}
                for log in equipment_logs:
                    if log.equipment_name not in equipment_dict:
                        equipment_dict[log.equipment_name] = log
                    else:
                        # Keep the most recent maintenance record
                        if log.maintenance_date > equipment_dict[log.equipment_name].maintenance_date:
                            equipment_dict[log.equipment_name] = log

                # Show equipment status cards
                for eq_name, latest_log in equipment_dict.items():
                    # Determine status
                    days_until_next = None
                    status_color = "🟢"
                    status_text = "Good"

                    if latest_log.next_maintenance_date:
                        days_until_next = (latest_log.next_maintenance_date - datetime.now()).days

                        if days_until_next < 0:
                            status_color = "🔴"
                            status_text = "OVERDUE"
                        elif days_until_next <= 7:
                            status_color = "🟡"
                            status_text = "Due Soon"
                        elif days_until_next <= 30:
                            status_color = "🟢"
                            status_text = "Upcoming"
                        else:
                            status_color = "🟢"
                            status_text = "Good"

                    with st.expander(f"{status_color} {eq_name} - {status_text}"):
                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.write(f"**Type:** {latest_log.equipment_type or 'Not specified'}")
                            st.write(f"**Last Maintenance:** {latest_log.maintenance_date.strftime('%Y-%m-%d')}")
                            st.write(f"**Maintenance Type:** {latest_log.maintenance_type}")

                        with col2:
                            if latest_log.next_maintenance_date:
                                st.write(f"**Next Due:** {latest_log.next_maintenance_date.strftime('%Y-%m-%d')}")
                                st.write(f"**Days Until:** {days_until_next} days")
                            else:
                                st.write("**Next Due:** Not scheduled")

                            if latest_log.cost > 0:
                                st.write(f"**Last Cost:** £{latest_log.cost:.2f}")

                        with col3:
                            if latest_log.performed_by:
                                st.write(f"**Performed By:** {latest_log.performed_by}")

                            if latest_log.notes:
                                st.write(f"**Notes:** {latest_log.notes}")

                        # Quick schedule next maintenance
                        with st.form(f"schedule_next_{latest_log.id}"):
                            st.write("**Schedule Next Maintenance:**")

                            next_date = st.date_input(
                                "Next Maintenance Date",
                                value=datetime.now() + timedelta(days=90)
                            )

                            if st.form_submit_button("📅 Update Next Maintenance Date"):
                                latest_log.next_maintenance_date = datetime.combine(next_date, datetime.min.time())
                                session.commit()
                                st.success(f"✅ Next maintenance scheduled for {next_date}")
                                st.rerun()

        with tab2:
            st.subheader("Log Equipment Maintenance")

            # Get existing equipment names for autocomplete
            existing_equipment = session.query(EquipmentLog.equipment_name).distinct().all()
            existing_names = [eq[0] for eq in existing_equipment]

            with st.form("log_maintenance_form"):
                equipment_mode = st.radio(
                    "Equipment",
                    ["Select Existing", "Add New Equipment"],
                    horizontal=True
                )

                if equipment_mode == "Select Existing" and existing_names:
                    equipment_name = st.selectbox("Select Equipment", existing_names)
                else:
                    equipment_name = st.text_input("Equipment Name *", placeholder="e.g., Main Oven, Stand Mixer")

                col1, col2 = st.columns(2)

                with col1:
                    equipment_type = st.selectbox(
                        "Equipment Type",
                        ["Oven", "Mixer", "Refrigerator", "Freezer", "Proofer", "Dough Sheeter", "Display Case", "Other"]
                    )

                with col2:
                    maintenance_type = st.selectbox(
                        "Maintenance Type",
                        ["Cleaning", "Repair", "Calibration", "Inspection", "Replacement", "Servicing"]
                    )

                col3, col4 = st.columns(2)

                with col3:
                    maintenance_date = st.date_input("Maintenance Date", value=datetime.now())

                with col4:
                    next_maintenance_date = st.date_input(
                        "Next Maintenance Due",
                        value=datetime.now() + timedelta(days=90),
                        help="When should this equipment be serviced again?"
                    )

                col5, col6 = st.columns(2)

                with col5:
                    cost = st.number_input("Cost (£)", min_value=0.0, step=0.01, value=0.0)

                with col6:
                    performed_by = st.text_input("Performed By", placeholder="e.g., John Smith, ABC Repairs")

                notes = st.text_area("Notes", placeholder="e.g., Replaced heating element, cleaned filters")

                submitted = st.form_submit_button("🔧 Log Maintenance")

                if submitted:
                    if not equipment_name:
                        st.error("Please enter an equipment name")
                    else:
                        maintenance_log = EquipmentLog(
                            equipment_name=equipment_name,
                            equipment_type=equipment_type,
                            maintenance_type=maintenance_type,
                            maintenance_date=datetime.combine(maintenance_date, datetime.min.time()),
                            next_maintenance_date=datetime.combine(next_maintenance_date, datetime.min.time()),
                            cost=cost,
                            performed_by=performed_by,
                            notes=notes
                        )

                        session.add(maintenance_log)
                        session.commit()

                        st.success(f"✅ Maintenance logged for {equipment_name}")
                        st.rerun()

        with tab3:
            st.subheader("Maintenance History")

            # Filters
            col_filter1, col_filter2 = st.columns(2)

            with col_filter1:
                filter_equipment = st.selectbox(
                    "Filter by Equipment",
                    ["All"] + [eq[0] for eq in session.query(EquipmentLog.equipment_name).distinct().all()]
                )

            with col_filter2:
                filter_days = st.selectbox("Time Period", [30, 60, 90, 180, 365], index=2)

            start_date = datetime.now() - timedelta(days=filter_days)

            query = session.query(EquipmentLog).filter(EquipmentLog.maintenance_date >= start_date)

            if filter_equipment != "All":
                query = query.filter(EquipmentLog.equipment_name == filter_equipment)

            maintenance_logs = query.order_by(EquipmentLog.maintenance_date.desc()).all()

            if not maintenance_logs:
                st.info("No maintenance records found for the selected filters.")
            else:
                # Summary metrics
                total_cost = sum(log.cost for log in maintenance_logs)
                total_events = len(maintenance_logs)

                col_metric1, col_metric2, col_metric3 = st.columns(3)

                with col_metric1:
                    st.metric("Total Maintenance Cost", f"£{total_cost:.2f}")

                with col_metric2:
                    st.metric("Maintenance Events", total_events)

                with col_metric3:
                    avg_cost = total_cost / total_events if total_events > 0 else 0
                    st.metric("Avg Cost/Event", f"£{avg_cost:.2f}")

                st.markdown("---")

                # Display logs
                for log in maintenance_logs:
                    with st.expander(f"{log.maintenance_date.strftime('%Y-%m-%d')} - {log.equipment_name} - {log.maintenance_type}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"**Equipment:** {log.equipment_name}")
                            st.write(f"**Type:** {log.equipment_type}")
                            st.write(f"**Maintenance:** {log.maintenance_type}")
                            st.write(f"**Date:** {log.maintenance_date.strftime('%Y-%m-%d')}")

                        with col2:
                            if log.cost > 0:
                                st.write(f"**Cost:** £{log.cost:.2f}")

                            if log.performed_by:
                                st.write(f"**Performed By:** {log.performed_by}")

                            if log.next_maintenance_date:
                                st.write(f"**Next Due:** {log.next_maintenance_date.strftime('%Y-%m-%d')}")

                        if log.notes:
                            st.write(f"**Notes:** {log.notes}")

                        # Delete button
                        if st.button(f"🗑️ Delete Record", key=f"delete_maintenance_{log.id}"):
                            session.delete(log)
                            session.commit()
                            st.success("Maintenance record deleted")
                            st.rerun()

    finally:
        close_session(session)
