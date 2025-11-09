import streamlit as st
from square_api import SquareAPI
from database import get_session, close_session
from models import SalesCache, Recipe
from datetime import datetime
import os

def show_square_setup():
    st.title("🔗 Square API Integration")
    
    st.write("""
    Connect your Square account to automatically import sales data, menu items, and pricing information.
    """)
    
    square_api = SquareAPI()
    
    tab1, tab2, tab3 = st.tabs(["⚙️ Setup", "📥 Import Data", "ℹ️ Help"])
    
    with tab1:
        st.subheader("API Configuration")
        
        if square_api.is_configured:
            st.success("✅ Square API credentials are configured!")
            
            is_connected, message = square_api.test_connection()
            
            if is_connected:
                st.success(f"✅ {message}")
            else:
                st.error(f"❌ Connection test failed: {message}")
            
            if st.button("🔄 Test Connection Again"):
                st.rerun()
        else:
            st.warning("⚠️ Square API credentials not configured")
            
            st.write("""
            To connect to Square, you need to set the following environment variables:
            
            1. **SQUARE_ACCESS_TOKEN**: Your Square API access token
            2. **SQUARE_LOCATION_ID**: Your Square location ID
            
            You can add these in the Replit Secrets panel (🔒 icon in the left sidebar).
            """)
            
            with st.expander("📖 How to get Square API credentials"):
                st.write("""
                **Step 1: Get Access Token**
                1. Go to https://developer.squareup.com/
                2. Sign in with your Square account
                3. Create a new application or select an existing one
                4. Go to "Credentials" tab
                5. Copy your **Production Access Token** (or Sandbox for testing)
                
                **Step 2: Get Location ID**
                1. In the Square Developer Dashboard
                2. Go to "Locations" section
                3. Copy your **Location ID**
                
                **Step 3: Add to Replit**
                1. Click the 🔒 Secrets icon in Replit's left sidebar
                2. Add a new secret: `SQUARE_ACCESS_TOKEN` with your access token
                3. Add another secret: `SQUARE_LOCATION_ID` with your location ID
                4. Refresh this page
                """)
            
            if st.button("✅ I've Added the Credentials - Check Again"):
                st.rerun()
    
    with tab2:
        st.subheader("Import Square Data")
        
        if not square_api.is_configured:
            st.warning("⚠️ Configure Square API credentials first in the Setup tab!")
        else:
            session = get_session()
            
            try:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**📦 Import Catalog Items**")
                    st.write("Import your menu items and pricing from Square to create recipes.")
                    
                    if st.button("📥 Import Catalog Items"):
                        with st.spinner("Fetching catalog from Square..."):
                            items = square_api.get_catalog_items()
                            
                            if items:
                                imported = 0
                                updated = 0
                                
                                for item in items:
                                    existing = session.query(Recipe).filter_by(square_item_id=item['id']).first()
                                    
                                    if existing:
                                        existing.sale_price = item['price']
                                        updated += 1
                                    else:
                                        new_recipe = Recipe(
                                            name=item['name'],
                                            square_item_id=item['id'],
                                            sale_price=item['price'],
                                            category='Imported from Square'
                                        )
                                        session.add(new_recipe)
                                        imported += 1
                                
                                session.commit()
                                
                                st.success(f"✅ Imported {imported} new items, updated {updated} existing items!")
                                
                                if imported > 0:
                                    st.info("💡 Don't forget to add ingredients to these recipes in the Recipe Database!")
                            else:
                                st.warning("No catalog items found or error occurred.")
                
                with col2:
                    st.write("**💳 Import Sales Data**")
                    st.write("Import recent sales transactions to track revenue and usage.")
                    
                    days_back = st.selectbox("Import sales from past:", [7, 14, 30, 60, 90], index=2)
                    
                    if st.button("📥 Import Sales"):
                        with st.spinner(f"Fetching sales from past {days_back} days..."):
                            orders = square_api.get_orders(days_back=days_back)
                            
                            if orders:
                                imported = 0
                                skipped = 0
                                errors = 0
                                
                                for order in orders:
                                    try:
                                        unique_id = f"{order['order_id']}_{order['item_name']}"
                                        
                                        existing = session.query(SalesCache).filter(
                                            SalesCache.square_payment_id == unique_id
                                        ).first()
                                        
                                        if not existing:
                                            new_sale = SalesCache(
                                                square_payment_id=unique_id,
                                                item_name=order['item_name'],
                                                quantity=order['quantity'],
                                                total_amount=order['total_amount'],
                                                timestamp=datetime.fromisoformat(order['created_at'].replace('Z', '+00:00'))
                                            )
                                            session.add(new_sale)
                                            imported += 1
                                        else:
                                            skipped += 1
                                    except Exception as e:
                                        errors += 1
                                        st.warning(f"Error importing order {order.get('order_id', 'unknown')}: {str(e)}")
                                
                                session.commit()
                                
                                st.success(f"✅ Imported {imported} new sales transactions!")
                                
                                if skipped > 0:
                                    st.info(f"ℹ️ Skipped {skipped} duplicate transactions")
                                
                                if errors > 0:
                                    st.warning(f"⚠️ {errors} transactions had errors and were not imported")
                            else:
                                st.warning("No sales data found or error occurred.")
                
                st.divider()
                
                st.write("**🔄 Auto-Sync Settings (Coming Soon)**")
                st.info("Automatic daily synchronization with Square will be available in a future update.")
            
            finally:
                close_session(session)
    
    with tab3:
        st.subheader("Square Integration Help")
        
        st.write("""
        ### What data gets imported?
        
        **Catalog Items:**
        - Menu item names
        - Prices
        - Item IDs (for linking)
        
        **Sales Data:**
        - Transaction details
        - Items sold and quantities
        - Sale amounts
        - Timestamps
        
        ### How does it work?
        
        1. **One-time Setup**: Add your Square API credentials to Replit Secrets
        2. **Import Catalog**: Creates recipe templates with pricing from your Square menu
        3. **Add Ingredients**: Manually add ingredient costs and recipes (Square doesn't track this)
        4. **Import Sales**: Pulls transaction history to calculate profits and track inventory usage
        5. **Analyze**: View profit margins, inventory alerts, and business recommendations
        
        ### Privacy & Security
        
        - Your API credentials are stored securely in Replit's encrypted secrets
        - Data is stored in your private database
        - No data is shared with third parties
        
        ### Troubleshooting
        
        **Connection Failed:**
        - Verify your Access Token is correct
        - Check that you're using Production credentials (not Sandbox) for live data
        - Ensure your Square account has the necessary permissions
        
        **No Data Found:**
        - Make sure you have items in your Square catalog
        - Verify you have sales in the selected time period
        - Check that the Location ID matches your active location
        """)
