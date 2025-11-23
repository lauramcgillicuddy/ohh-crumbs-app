import streamlit as st
from database import get_session, close_session
from models import Ingredient, Supplier, RecipeItem, SupplierOrderItem
from datetime import datetime
from styling import inject_custom_css, render_page_header
from unit_conversions import BAKING_CONVERSIONS
from allergens import ALLERGEN_CATEGORIES
from common_ingredients import get_allergen_template, suggest_allergen_template
from product_lookup import lookup_product_by_barcode, map_to_natasha_allergens
import json

def show_ingredients():
    inject_custom_css()

    render_page_header("🥖 Ingredient Management", "TRACK YOUR STOCK")
    
    session = get_session()
    
    try:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 View Ingredients", "➕ Add Ingredient", "📦 Update Stock", "📱 Barcode Scanner", "⚠️ Allergen Audit"])
        
        with tab1:
            st.subheader("Current Ingredients")
            
            ingredients = session.query(Ingredient).order_by(Ingredient.name).all()
            
            if ingredients:
                for ingredient in ingredients:
                    # Check if allergen info is missing
                    has_allergen_info = ingredient.allergens or ingredient.sub_ingredients
                    warning_icon = "" if has_allergen_info else " ⚠️"

                    with st.expander(f"{ingredient.name} ({ingredient.unit}){warning_icon}"):
                        # Show warning if allergen info is missing
                        if not has_allergen_info:
                            st.error("⚠️ **ALLERGEN DATA MISSING** - This ingredient needs allergen information for Natasha's Law compliance!")

                            # Check if there's a template suggestion
                            suggestion = suggest_allergen_template(ingredient.name)
                            if suggestion:
                                st.info(suggestion)

                        col1, col2, col3 = st.columns(3)

                        with col1:
                            st.write(f"**Cost per {ingredient.unit}:** £{ingredient.cost_per_unit:.2f}")
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

                        # Show allergen information if present
                        if ingredient.allergens or ingredient.sub_ingredients or ingredient.may_contain:
                            st.markdown("---")
                            st.markdown("**🏷️ Allergen Information:**")

                            if ingredient.allergens:
                                try:
                                    allergens = json.loads(ingredient.allergens)
                                    if allergens:
                                        st.write(f"**Contains:** {', '.join(allergens)}")
                                except:
                                    pass

                            if ingredient.sub_ingredients:
                                st.write(f"**Sub-ingredients:** {ingredient.sub_ingredients}")

                            if ingredient.may_contain:
                                try:
                                    may_contain = json.loads(ingredient.may_contain)
                                    if may_contain:
                                        st.write(f"**May contain:** {', '.join(may_contain)}")
                                except:
                                    pass

                        col_edit1, col_edit2 = st.columns([1, 1])
                        
                        with col_edit1:
                            if st.button(f"✏️ Edit", key=f"edit_{ingredient.id}"):
                                st.session_state[f'editing_{ingredient.id}'] = True
                        
                        with col_edit2:
                            if st.button(f"🗑️ Delete", key=f"delete_{ingredient.id}"):
                                try:
                                    # Rollback any pending changes first to avoid conflicts
                                    session.rollback()

                                    # Re-fetch the ingredient after rollback
                                    ingredient = session.query(Ingredient).get(ingredient.id)

                                    # Check if ingredient is used in any recipes
                                    recipe_uses = session.query(RecipeItem).filter(
                                        RecipeItem.ingredient_id == ingredient.id
                                    ).count()

                                    # Check if ingredient is in any supplier orders
                                    order_uses = session.query(SupplierOrderItem).filter(
                                        SupplierOrderItem.ingredient_id == ingredient.id
                                    ).count()

                                    if recipe_uses > 0:
                                        st.error(f"❌ Cannot delete {ingredient.name} - it's used in {recipe_uses} recipe(s). Remove it from recipes first!")
                                    elif order_uses > 0:
                                        st.error(f"❌ Cannot delete {ingredient.name} - it's in {order_uses} supplier order(s). This is historical data that should be kept.")
                                    else:
                                        session.delete(ingredient)
                                        session.commit()
                                        st.success(f"✅ Deleted {ingredient.name}")
                                        st.rerun()
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"Error deleting ingredient: {str(e)}")
                        
                        if st.session_state.get(f'editing_{ingredient.id}', False):
                            with st.form(key=f"edit_form_{ingredient.id}"):
                                st.write("**Edit Ingredient**")

                                col_cost, col_unit = st.columns(2)

                                with col_cost:
                                    new_cost = st.number_input("Cost per unit", value=float(ingredient.cost_per_unit), min_value=0.0, step=0.01)

                                with col_unit:
                                    available_units = ["kg", "g", "lb", "oz", "L", "mL", "cups", "tbsp", "tsp", "units"]
                                    current_unit_index = available_units.index(ingredient.unit) if ingredient.unit in available_units else 0
                                    new_unit = st.selectbox("Unit", available_units, index=current_unit_index)

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

                                st.markdown("---")
                                st.markdown("### 🏷️ Allergen Information")
                                st.warning("⚠️ **Complete this section for Natasha's Law compliance!**")

                                # Check if there's a suggested template
                                suggestion = suggest_allergen_template(ingredient.name)
                                if suggestion and (not ingredient.allergens and not ingredient.sub_ingredients):
                                    st.info(suggestion)

                                    # Add auto-fill button
                                    if st.button(f"✨ Auto-Fill Allergen Data for {ingredient.name}", key=f"autofill_{ingredient.id}"):
                                        auto_template = get_allergen_template(ingredient.name)
                                        if auto_template:
                                            ingredient.allergens = json.dumps(auto_template['allergens']) if auto_template['allergens'] else None
                                            ingredient.sub_ingredients = auto_template['sub_ingredients'] if auto_template['sub_ingredients'] else None
                                            if auto_template['may_contain']:
                                                ingredient.may_contain = json.dumps(auto_template['may_contain'])
                                            session.commit()
                                            st.success(f"✅ Auto-filled allergen data for {ingredient.name}!")
                                            st.rerun()

                                # Get existing allergens
                                existing_allergens = []
                                if ingredient.allergens:
                                    try:
                                        existing_allergens = json.loads(ingredient.allergens)
                                    except:
                                        pass

                                # Allergen selection
                                allergen_selections = []
                                for category, allergens_list in ALLERGEN_CATEGORIES.items():
                                    if len(allergens_list) == 1:
                                        # Simple checkbox for single-item categories
                                        default_value = allergens_list[0] in existing_allergens
                                        if st.checkbox(f"Contains {category}", value=default_value, key=f"edit_allergen_{ingredient.id}_{category}",
                                                     help=f"Check if this ingredient contains {category}"):
                                            allergen_selections.extend(allergens_list)
                                    else:
                                        # Multi-select for categories with multiple items
                                        default_selections = [a for a in allergens_list if a in existing_allergens]
                                        selected = st.multiselect(
                                            f"{category}",
                                            allergens_list,
                                            default=default_selections,
                                            key=f"edit_allergen_{ingredient.id}_{category}",
                                            help=f"Select all {category} allergens that apply"
                                        )
                                        allergen_selections.extend(selected)

                                # Sub-ingredients
                                sub_ingredients_edit = st.text_area(
                                    "Sub-Ingredients (for compound ingredients)",
                                    value=ingredient.sub_ingredients or "",
                                    placeholder="e.g., Wheat, Calcium Carbonate, Iron",
                                    key=f"edit_sub_ing_{ingredient.id}",
                                    help="⚠️ IMPORTANT: If this ingredient is made of other ingredients, list them ALL here. This appears on the label!"
                                )

                                # May contain
                                existing_may_contain = ""
                                if ingredient.may_contain:
                                    try:
                                        may_contain_list = json.loads(ingredient.may_contain)
                                        existing_may_contain = ", ".join(may_contain_list)
                                    except:
                                        existing_may_contain = ingredient.may_contain or ""

                                may_contain_input = st.text_input(
                                    "May contain (cross-contamination)",
                                    value=existing_may_contain,
                                    placeholder="e.g., nuts, sesame",
                                    key=f"edit_may_contain_{ingredient.id}",
                                    help="⚠️ IMPORTANT: List allergens that may be present due to shared equipment"
                                )

                                col_submit, col_cancel = st.columns(2)
                                
                                with col_submit:
                                    if st.form_submit_button("💾 Save"):
                                        ingredient.cost_per_unit = new_cost
                                        ingredient.unit = new_unit

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

                                        # Save allergen data
                                        allergens_json = json.dumps(allergen_selections) if allergen_selections else None
                                        may_contain_list = [m.strip() for m in may_contain_input.split(',') if m.strip()]
                                        may_contain_json = json.dumps(may_contain_list) if may_contain_list else None

                                        ingredient.allergens = allergens_json
                                        ingredient.sub_ingredients = sub_ingredients_edit if sub_ingredients_edit else None
                                        ingredient.may_contain = may_contain_json

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

            # Ingredient autocomplete search
            st.markdown("### 🔍 Copy from Existing Ingredient")
            st.info("💡 Start typing an ingredient name to auto-fill all details from an existing ingredient!")

            # Get all existing ingredients for autocomplete
            all_ingredients = session.query(Ingredient).order_by(Ingredient.name).all()
            ingredient_options = ["➕ Create New Ingredient"] + [ing.name for ing in all_ingredients]

            col_search, col_clear = st.columns([3, 1])

            with col_search:
                selected_ingredient_name = st.selectbox(
                    "Search existing ingredients or create new",
                    ingredient_options,
                    key="ingredient_autocomplete",
                    help="Type to search for existing ingredients, or select 'Create New' to start fresh"
                )

            with col_clear:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("🗑️ Clear", key="clear_ingredient_selection"):
                    st.session_state['ingredient_autocomplete'] = "➕ Create New Ingredient"
                    st.rerun()

            # Store selected ingredient data in session state
            prefill_data = None
            if selected_ingredient_name != "➕ Create New Ingredient":
                selected_ing = session.query(Ingredient).filter(Ingredient.name == selected_ingredient_name).first()
                if selected_ing:
                    st.success(f"✨ Copying details from **{selected_ing.name}**. Modify as needed and save to create a new ingredient!")
                    prefill_data = selected_ing

            st.markdown("---")

            # Barcode Scanner for Product Lookup
            st.markdown("### 📱 Scan Product Barcode (Optional)")
            st.info("💡 Scan a product barcode to auto-fill allergen information from the product packaging!")

            # Try to import scanner
            scanner_available = False
            try:
                from streamlit_qrcode_scanner import qrcode_scanner
                scanner_available = True
            except ImportError:
                pass

            scanned_product = None
            if scanner_available:
                scan_mode = st.radio("Product lookup:", ["⌨️ Manual Entry", "📷 Scan Barcode", "🔢 Type Barcode Number", "📸 Photo of Ingredients"], horizontal=True, key="product_scan_mode")

                barcode = None

                if scan_mode == "📷 Scan Barcode":
                    st.caption("📷 Point your camera at the product barcode. Allow camera access if prompted.")
                    try:
                        barcode = qrcode_scanner(key='product_barcode_scanner')
                    except Exception as e:
                        st.error(f"Scanner error: {str(e)}")
                        st.info("Try 'Type Barcode Number' option instead!")

                elif scan_mode == "🔢 Type Barcode Number":
                    st.caption("🔢 Type or paste the barcode number from the product packaging")
                    barcode_input = st.text_input("Barcode number:", placeholder="e.g., 5000169000250", key="manual_barcode_input")
                    if st.button("🔍 Look Up Product", key="lookup_barcode") and barcode_input:
                        barcode = barcode_input.strip()

                elif scan_mode == "📸 Photo of Ingredients":
                    st.caption("📸 Take or upload a photo of the ingredients list on the product packaging")
                    uploaded_file = st.file_uploader("Upload ingredient photo", type=['png', 'jpg', 'jpeg'], key="ingredient_photo")

                    if uploaded_file is not None:
                        st.image(uploaded_file, caption="Uploaded Image", width=300)

                        if st.button("🔍 Extract Ingredients from Photo", key="ocr_ingredients"):
                            with st.spinner("🤖 Analyzing photo with AI..."):
                                try:
                                    import base64
                                    import requests
                                    import os

                                    # Get API key from environment/secrets
                                    openai_key = os.getenv('OPENAI_API_KEY') or st.secrets.get("OPENAI_API_KEY")

                                    if not openai_key:
                                        st.error("⚠️ OpenAI API key not found. Please add it to your Streamlit secrets.")
                                        st.info("Add `OPENAI_API_KEY = \"sk-...\"` to your `.streamlit/secrets.toml` file")
                                    else:
                                        # Convert image to base64
                                        uploaded_file.seek(0)  # Reset file pointer
                                        image_bytes = uploaded_file.read()
                                        base64_image = base64.b64encode(image_bytes).decode('utf-8')

                                        headers = {
                                            "Content-Type": "application/json",
                                            "Authorization": f"Bearer {openai_key}"
                                        }

                                        payload = {
                                            "model": "gpt-4o-mini",
                                            "messages": [
                                                {
                                                    "role": "user",
                                                    "content": [
                                                        {
                                                            "type": "text",
                                                            "text": """Please carefully read and extract ALL text from the ingredients list in this product packaging photo.

Extract the complete ingredient list exactly as written on the package. Include:
- All ingredient names
- Any sub-ingredients in parentheses
- Percentages if shown
- Allergen warnings if present

Format: Return ONLY the ingredient text as it appears on the package, maintaining the original formatting as much as possible."""
                                                        },
                                                        {
                                                            "type": "image_url",
                                                            "image_url": {
                                                                "url": f"data:image/jpeg;base64,{base64_image}"
                                                            }
                                                        }
                                                    ]
                                                }
                                            ],
                                            "max_tokens": 1000
                                        }

                                        response = requests.post(
                                            "https://api.openai.com/v1/chat/completions",
                                            headers=headers,
                                            json=payload,
                                            timeout=30
                                        )

                                        if response.status_code == 200:
                                            extracted_text = response.json()['choices'][0]['message']['content'].strip()

                                            if extracted_text:
                                                st.success("✅ Successfully extracted ingredients using GPT-4o-mini!")

                                                # Store extracted text in session state
                                                st.session_state['ocr_ingredients_text'] = extracted_text

                                                # Display extracted text
                                                st.text_area("Extracted Ingredients:", value=extracted_text, height=200, key="ocr_display")

                                                st.info("💡 **Review the text above and use it to fill in the ingredient details below!**")
                                            else:
                                                st.warning("❌ Could not extract text from image. Try a clearer photo!")
                                        else:
                                            st.error(f"API request failed with status {response.status_code}")
                                            st.error(f"Response: {response.text}")

                                except Exception as e:
                                    st.error(f"OCR error: {str(e)}")
                                    st.info("Make sure your OpenAI API key is valid and you have credits available!")

                # Process barcode lookup
                if barcode:
                    st.info(f"Looking up barcode: {barcode}")
                    with st.spinner("Searching product database..."):
                        product_data = lookup_product_by_barcode(barcode)

                        if product_data.get('found'):
                            st.success(f"✅ Found: **{product_data['name']}** ({product_data['brand']})")

                            # Store in session state
                            st.session_state['scanned_product'] = product_data

                            if product_data.get('image_url'):
                                col_img, col_info = st.columns([1, 2])
                                with col_img:
                                    st.image(product_data['image_url'], width=150)
                                with col_info:
                                    if product_data['allergens']:
                                        st.write(f"**Allergens:** {', '.join(product_data['allergens'])}")
                                    if product_data['traces']:
                                        st.write(f"**May contain:** {', '.join(product_data['traces'])}")
                                    if product_data.get('ingredients_text'):
                                        st.write(f"**Ingredients:** {product_data['ingredients_text'][:100]}...")
                        else:
                            st.warning(f"❌ Product not found in Open Food Facts database")
                            st.info("💡 **This product isn't in the database yet.** You can:")
                            st.write("1. Fill in the allergen info manually below (use the template suggestions)")
                            st.write("2. Or add this product to Open Food Facts at: https://world.openfoodfacts.org")
                            st.write(f"   (Barcode: `{barcode}`)")
            else:
                st.caption("🔍 Barcode scanner not available. Fill in ingredient details manually below.")

            # Check if we have scanned product data or OCR text
            if 'scanned_product' in st.session_state:
                scanned_product = st.session_state['scanned_product']

                # Add clear button
                if st.button("🗑️ Clear Scanned Data & Start Fresh", key="clear_scan"):
                    del st.session_state['scanned_product']
                    if 'ocr_ingredients_text' in st.session_state:
                        del st.session_state['ocr_ingredients_text']
                    st.rerun()

            elif 'ocr_ingredients_text' in st.session_state:
                # Show clear OCR button if we have OCR text but no scanned product
                st.success(f"✅ Photo text extracted! Review below in the form.")
                if st.button("🗑️ Clear Photo Text & Start Fresh", key="clear_ocr"):
                    del st.session_state['ocr_ingredients_text']
                    st.rerun()

            st.markdown("---")

            # Conversion reference
            with st.expander("📏 Unit Conversion Reference"):
                st.markdown(BAKING_CONVERSIONS)

            with st.form("add_ingredient_form"):
                # Pre-fill from selected ingredient, scanned product, or empty
                default_name = ""
                default_unit = "kg"
                default_cost = 0.0
                default_stock = 0.0
                default_supplier = "None"
                default_lead_time = 7

                # Priority 1: Prefill from selected existing ingredient
                if prefill_data:
                    default_name = prefill_data.name
                    default_unit = prefill_data.unit if prefill_data.unit else "kg"
                    default_cost = float(prefill_data.cost_per_unit)
                    default_stock = 0.0  # Don't copy stock, start fresh
                    default_lead_time = prefill_data.supplier_lead_time_days

                    # Get supplier name
                    if prefill_data.supplier_id:
                        supplier_obj = session.query(Supplier).get(prefill_data.supplier_id)
                        if supplier_obj:
                            default_supplier = supplier_obj.name
                    elif prefill_data.supplier:
                        default_supplier = prefill_data.supplier

                # Priority 2: Prefill from scanned product (if no ingredient selected)
                elif scanned_product and scanned_product.get('found'):
                    product_name = scanned_product.get('name', '')
                    brand = scanned_product.get('brand', '')
                    default_name = f"{brand} {product_name}".strip() if brand else product_name

                name = st.text_input("Ingredient Name *", value=default_name, placeholder="e.g., All-Purpose Flour")

                col1, col2 = st.columns(2)

                with col1:
                    available_units = ["kg", "g", "lb", "oz", "L", "mL", "cups", "tbsp", "tsp", "units"]
                    default_unit_index = available_units.index(default_unit) if default_unit in available_units else 0
                    unit = st.selectbox("Unit of Measurement *", available_units, index=default_unit_index)

                with col2:
                    cost_per_unit = st.number_input("Cost per Unit *", min_value=0.0, step=0.01, value=default_cost)

                col3, col4 = st.columns(2)

                with col3:
                    initial_stock = st.number_input("Initial Stock Quantity", min_value=0.0, step=0.1, value=default_stock)

                with col4:
                    suppliers = session.query(Supplier).order_by(Supplier.name).all()
                    supplier_options = ["None"] + [s.name for s in suppliers]
                    default_supplier_index = 0
                    if default_supplier in supplier_options:
                        default_supplier_index = supplier_options.index(default_supplier)
                    selected_supplier = st.selectbox("Supplier", supplier_options, index=default_supplier_index,
                        help="Select from existing suppliers or choose 'None'")

                lead_time = st.number_input("Supplier Lead Time (days)", min_value=1, step=1, value=default_lead_time,
                    help="How many days it takes to receive an order from this supplier (only used if no supplier selected)")

                st.markdown("---")
                st.markdown("### 🏷️ Natasha's Law - Allergen Information")

                # Determine allergen source: prefilled ingredient, scanned product, or template
                allergen_source = None
                default_allergens = []
                default_traces = []
                default_ingredients_text = ""

                # Priority 1: Prefill from selected existing ingredient
                if prefill_data:
                    allergen_source = "prefill"
                    # Parse allergens from JSON
                    if prefill_data.allergens:
                        try:
                            default_allergens = json.loads(prefill_data.allergens)
                        except:
                            default_allergens = []
                    # Parse may_contain from JSON
                    if prefill_data.may_contain:
                        try:
                            default_traces = json.loads(prefill_data.may_contain)
                        except:
                            default_traces = []
                    # Get sub-ingredients
                    if prefill_data.sub_ingredients:
                        default_ingredients_text = prefill_data.sub_ingredients

                    st.success(f"💡 **From Selected Ingredient:** Allergen data copied from '{prefill_data.name}'. Review and adjust if needed!")

                # Priority 2: Use scanned product data
                elif scanned_product and scanned_product.get('found'):
                    allergen_source = "scanned"
                    raw_allergens = scanned_product.get('allergens', [])
                    default_allergens = map_to_natasha_allergens(raw_allergens)
                    raw_traces = scanned_product.get('traces', [])
                    default_traces = map_to_natasha_allergens(raw_traces)
                    default_ingredients_text = scanned_product.get('ingredients_text', '')
                    st.success(f"💡 **From Scanned Product:** Allergen data auto-filled from product packaging!")

                # Priority 3: Check template
                else:
                    template = None
                    if name:
                        template = get_allergen_template(name)
                        if template:
                            allergen_source = "template"
                            default_allergens = template['allergens']
                            if template['may_contain']:
                                default_traces = template['may_contain']
                            if template['sub_ingredients']:
                                default_ingredients_text = template['sub_ingredients']
                            st.success(f"💡 **Smart Suggestion:** Allergen data auto-filled for '{name}'. Review and adjust if needed!")

                st.info("⚠️ **IMPORTANT:** Allergen information is required for Natasha's Law compliance in Northern Ireland. Review and adjust if needed!")

                # Allergen selection (with defaults from prefill, scanned product, or template)
                allergen_selections = []
                for category, allergens in ALLERGEN_CATEGORIES.items():
                    if len(allergens) == 1:
                        # Check if this allergen is in the defaults
                        default_checked = allergens[0] in default_allergens

                        # Simple checkbox for single-item categories
                        if st.checkbox(f"Contains {category}", value=default_checked, key=f"allergen_{category}",
                                     help=f"Check if this ingredient contains {category}"):
                            allergen_selections.extend(allergens)
                    else:
                        # Get default selections
                        default_selections = [a for a in allergens if a in default_allergens]

                        # Multi-select for categories with multiple items
                        selected = st.multiselect(
                            f"{category}",
                            allergens,
                            default=default_selections,
                            key=f"allergen_{category}",
                            help=f"Select all {category} allergens that apply"
                        )
                        allergen_selections.extend(selected)

                # Sub-ingredients (for compound ingredients)
                # Check for OCR text if no other source
                if not default_ingredients_text and 'ocr_ingredients_text' in st.session_state:
                    default_ingredients_text = st.session_state['ocr_ingredients_text']
                    st.success("💡 **From Photo:** Ingredients text extracted from your uploaded photo!")

                sub_ingredients = st.text_area(
                    "Sub-Ingredients (for compound ingredients)",
                    value=default_ingredients_text,
                    placeholder="e.g., for 'Wheat Flour': Wheat, Calcium Carbonate, Iron, Niacin, Thiamin",
                    help="⚠️ IMPORTANT: If this ingredient is made of other ingredients, list them ALL here. This appears on the label!"
                )

                # May contain warnings
                default_may_contain = ", ".join(default_traces) if default_traces else ""

                may_contain = st.text_input(
                    "May contain (cross-contamination warnings)",
                    value=default_may_contain,
                    placeholder="e.g., nuts, sesame",
                    help="⚠️ IMPORTANT: List allergens that may be present due to shared equipment or manufacturing facility"
                )

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

                            # Auto-fill from template if no allergen data was entered
                            final_allergen_selections = allergen_selections
                            final_sub_ingredients = sub_ingredients
                            final_may_contain = may_contain

                            # If user didn't fill anything in, try to auto-fill from template
                            if not allergen_selections and not sub_ingredients:
                                auto_template = get_allergen_template(name)
                                if auto_template:
                                    final_allergen_selections = auto_template['allergens']
                                    final_sub_ingredients = auto_template['sub_ingredients']
                                    if auto_template['may_contain'] and not may_contain:
                                        final_may_contain = ", ".join(auto_template['may_contain'])

                            # Prepare allergen data
                            allergens_json = json.dumps(final_allergen_selections) if final_allergen_selections else None
                            may_contain_list = [m.strip() for m in final_may_contain.split(',') if m.strip()]
                            may_contain_json = json.dumps(may_contain_list) if may_contain_list else None

                            new_ingredient = Ingredient(
                                name=name,
                                unit=unit,
                                cost_per_unit=cost_per_unit,
                                current_stock=initial_stock,
                                supplier_id=supplier_id,
                                supplier=supplier_name,
                                supplier_lead_time_days=supplier_lead_time,
                                allergens=allergens_json,
                                sub_ingredients=final_sub_ingredients if final_sub_ingredients else None,
                                may_contain=may_contain_json
                            )

                            session.add(new_ingredient)
                            session.commit()

                            # Clear scanned product and OCR text from session state
                            if 'scanned_product' in st.session_state:
                                del st.session_state['scanned_product']
                            if 'ocr_ingredients_text' in st.session_state:
                                del st.session_state['ocr_ingredients_text']

                            if auto_template and (not allergen_selections and not sub_ingredients):
                                st.success(f"✅ Added '{name}' with auto-filled allergen data from template!")
                            else:
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

            st.info("💡 **How it works:** Search for an ingredient by name to quickly update inventory.")

            # Try to import the QR scanner package
            scanned_code = None
            scanner_available = False
            try:
                from streamlit_qrcode_scanner import qrcode_scanner
                scanner_available = True
            except ImportError:
                pass

            if scanner_available:
                # Show scanner option
                scan_mode = st.radio("Choose input method:", ["🔍 Search by Name", "📷 Scan QR Code"], horizontal=True)

                if scan_mode == "📷 Scan QR Code":
                    st.write("**📷 Camera Scanner:**")
                    st.caption("Allow camera access when prompted. The scanner will appear below.")
                    try:
                        scanned_code = qrcode_scanner(key='ingredient_scanner')
                    except Exception as e:
                        st.error(f"Scanner error: {str(e)}")
                        st.info("Try using the 'Search by Name' option instead!")

                    st.write("**Or enter manually:**")
                    manual_code = st.text_input("Type ingredient name", placeholder="e.g., Flour, Butter", key="manual_barcode")
                else:
                    st.write("**🔍 Search for Ingredient:**")
                    manual_code = st.text_input("Enter ingredient name or ID", placeholder="e.g., Flour, Butter, or ingredient ID", key="manual_barcode")
            else:
                # Fallback if scanner not available
                st.write("**🔍 Search for Ingredient:**")
                manual_code = st.text_input("Enter ingredient name or ID", placeholder="e.g., Flour, Butter, or ingredient ID", key="manual_barcode")

            barcode_value = scanned_code if scanned_code else manual_code

            if barcode_value:
                st.divider()
                st.write(f"**Scanned/Entered Code:** `{barcode_value}`")

                # First try to search by name
                ingredient = session.query(Ingredient).filter(Ingredient.name.ilike(f"%{barcode_value}%")).first()

                # If not found by name, try by ID (only if it's a valid small integer)
                if not ingredient:
                    try:
                        # Try to convert to integer
                        id_value = int(barcode_value)
                        # Only query by ID if it's a reasonable ingredient ID (not a product barcode)
                        if 0 < id_value < 1000000:  # Reasonable ID range
                            ingredient = session.query(Ingredient).filter(Ingredient.id == id_value).first()
                    except (ValueError, OverflowError):
                        # Not a valid integer, skip ID search
                        pass
                
                if ingredient:
                    st.success(f"✅ Found: **{ingredient.name}**")
                    
                    col_info1, col_info2 = st.columns(2)
                    
                    with col_info1:
                        st.write(f"**Current Stock:** {ingredient.current_stock:.2f} {ingredient.unit}")
                        st.write(f"**Cost per Unit:** £{ingredient.cost_per_unit:.2f}")
                    
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

        with tab5:
            st.subheader("⚠️ Allergen Information Audit")
            st.info("This audit shows which ingredients are missing allergen data required for Natasha's Law compliance.")

            ingredients = session.query(Ingredient).order_by(Ingredient.name).all()

            if not ingredients:
                st.warning("No ingredients found. Add ingredients first!")
            else:
                # Check how many can be auto-filled
                auto_fillable = []
                for ing in ingredients:
                    if not (ing.allergens or ing.sub_ingredients):
                        template = get_allergen_template(ing.name)
                        if template:
                            auto_fillable.append((ing, template))

                # Show Quick Fill button if there are auto-fillable ingredients
                if auto_fillable:
                    st.markdown("---")
                    col_btn1, col_btn2 = st.columns([1, 3])
                    with col_btn1:
                        if st.button(f"✨ Quick Fill All ({len(auto_fillable)} ingredients)", type="primary"):
                            filled_count = 0
                            for ing, template in auto_fillable:
                                ing.allergens = json.dumps(template['allergens']) if template['allergens'] else None
                                ing.sub_ingredients = template['sub_ingredients'] if template['sub_ingredients'] else None
                                if template['may_contain']:
                                    ing.may_contain = json.dumps(template['may_contain'])
                                filled_count += 1

                            session.commit()
                            st.success(f"🎉 Auto-filled allergen data for {filled_count} ingredients!")
                            st.rerun()

                    with col_btn2:
                        st.caption("Automatically fill allergen data for all ingredients with known templates (flour, butter, eggs, etc.)")

                    st.markdown("---")
                # Categorize ingredients
                complete_ingredients = []
                incomplete_ingredients = []

                for ing in ingredients:
                    has_allergen_info = ing.allergens or ing.sub_ingredients
                    if has_allergen_info:
                        complete_ingredients.append(ing)
                    else:
                        incomplete_ingredients.append(ing)

                # Show summary
                total = len(ingredients)
                complete_count = len(complete_ingredients)
                incomplete_count = len(incomplete_ingredients)
                completion_pct = (complete_count / total * 100) if total > 0 else 0

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Ingredients", total)

                with col2:
                    st.metric("✅ Complete", complete_count)

                with col3:
                    st.metric("⚠️ Missing Data", incomplete_count)

                # Progress bar
                st.progress(completion_pct / 100, text=f"Allergen Data Completion: {completion_pct:.1f}%")

                st.markdown("---")

                # Show incomplete ingredients first (priority)
                if incomplete_ingredients:
                    st.error(f"**⚠️ {incomplete_count} Ingredient(s) Need Allergen Data:**")

                    for ing in incomplete_ingredients:
                        col_name, col_action = st.columns([3, 1])

                        with col_name:
                            st.write(f"**{ing.name}** ({ing.unit})")

                            # Show suggestion if available
                            suggestion = suggest_allergen_template(ing.name)
                            if suggestion:
                                st.caption(suggestion)

                        with col_action:
                            if st.button("✏️ Edit", key=f"audit_edit_{ing.id}"):
                                # Set editing state and switch to View tab
                                st.session_state[f'editing_{ing.id}'] = True
                                st.info("👆 Switched to 'View Ingredients' tab. Look for the ingredient you selected!")
                                st.rerun()

                        st.markdown("---")
                else:
                    st.success("🎉 **Excellent!** All ingredients have allergen information!")

                # Show complete ingredients
                if complete_ingredients:
                    with st.expander(f"✅ View Complete Ingredients ({complete_count})"):
                        for ing in complete_ingredients:
                            st.write(f"✅ **{ing.name}** ({ing.unit})")

                            # Show what allergens it has
                            if ing.allergens:
                                try:
                                    allergens = json.loads(ing.allergens)
                                    if allergens:
                                        st.caption(f"Contains: {', '.join(allergens)}")
                                except:
                                    pass

    finally:
        close_session(session)
