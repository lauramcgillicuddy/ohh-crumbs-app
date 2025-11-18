import streamlit as st
from database import get_session, close_session
from models import Recipe, Ingredient, RecipeItem
from utils import calculate_recipe_cost, calculate_profit_margin
from styling import inject_custom_css, render_page_header
from recipe_ocr_parser import parse_recipe_from_image
import pandas as pd

def show_recipes():
    inject_custom_css()

    render_page_header("📖 Recipe Database", "MANAGE YOUR MENU ITEMS")
    
    session = get_session()
    
    try:
        tab1, tab2 = st.tabs(["📋 View Recipes", "➕ Add Recipe"])
        
        with tab1:
            st.subheader("Current Recipes")
            
            recipes = session.query(Recipe).order_by(Recipe.name).all()
            
            if recipes:
                for recipe in recipes:
                    cost, profit, margin = calculate_profit_margin(session, recipe.id)
                    
                    with st.expander(f"{recipe.name} - £{recipe.sale_price:.2f} | Margin: {margin:.1f}%"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Sale Price:** £{recipe.sale_price:.2f}")
                            st.write(f"**Ingredient Cost:** £{cost:.2f}")
                            st.write(f"**Profit per Item:** £{profit:.2f}")
                            st.write(f"**Profit Margin:** {margin:.1f}%")
                        
                        with col2:
                            st.write(f"**Category:** {recipe.category or 'Uncategorized'}")
                            if recipe.description:
                                st.write(f"**Description:** {recipe.description}")
                            if recipe.square_item_id:
                                st.write(f"**Square ID:** {recipe.square_item_id}")
                        
                        st.write("**Ingredients:**")
                        
                        if recipe.recipe_items:
                            for item in recipe.recipe_items:
                                ingredient = item.ingredient
                                item_cost = ingredient.cost_per_unit * item.quantity
                                st.write(f"- {item.quantity:.2f} {ingredient.unit} of {ingredient.name} (£{item_cost:.2f})")
                        else:
                            st.info("No ingredients added to this recipe yet.")
                        
                        col_edit, col_delete = st.columns(2)
                        
                        with col_edit:
                            if st.button(f"✏️ Edit Recipe", key=f"edit_recipe_{recipe.id}"):
                                st.session_state[f'editing_recipe_{recipe.id}'] = True
                        
                        with col_delete:
                            if st.button(f"🗑️ Delete Recipe", key=f"delete_recipe_{recipe.id}"):
                                session.delete(recipe)
                                session.commit()
                                st.success(f"Deleted recipe: {recipe.name}")
                                st.rerun()
                        
                        if st.session_state.get(f'editing_recipe_{recipe.id}', False):
                            st.write("---")
                            st.write("**Edit Recipe Details**")
                            
                            with st.form(key=f"edit_recipe_form_{recipe.id}"):
                                new_price = st.number_input("Sale Price", value=float(recipe.sale_price), min_value=0.0, step=0.01)
                                new_category = st.text_input("Category", value=recipe.category or "")
                                new_description = st.text_area("Description", value=recipe.description or "")
                                
                                col_save, col_cancel = st.columns(2)
                                
                                with col_save:
                                    if st.form_submit_button("💾 Save Changes"):
                                        recipe.sale_price = new_price
                                        recipe.category = new_category
                                        recipe.description = new_description
                                        session.commit()
                                        st.session_state[f'editing_recipe_{recipe.id}'] = False
                                        st.success("Recipe updated!")
                                        st.rerun()
                                
                                with col_cancel:
                                    if st.form_submit_button("❌ Cancel"):
                                        st.session_state[f'editing_recipe_{recipe.id}'] = False
                                        st.rerun()
                            
                            st.write("**Manage Ingredients**")
                            
                            ingredients = session.query(Ingredient).order_by(Ingredient.name).all()
                            
                            if ingredients:
                                with st.form(key=f"add_ingredient_to_recipe_{recipe.id}"):
                                    ingredient_id = st.selectbox(
                                        "Select Ingredient",
                                        options=[ing.id for ing in ingredients],
                                        format_func=lambda x: next(ing.name for ing in ingredients if ing.id == x)
                                    )
                                    
                                    quantity = st.number_input("Quantity", min_value=0.01, step=0.1, value=1.0)
                                    
                                    if st.form_submit_button("➕ Add to Recipe"):
                                        existing_item = session.query(RecipeItem).filter_by(
                                            recipe_id=recipe.id,
                                            ingredient_id=ingredient_id
                                        ).first()
                                        
                                        if existing_item:
                                            st.warning("This ingredient is already in the recipe. Update the quantity below.")
                                        else:
                                            new_item = RecipeItem(
                                                recipe_id=recipe.id,
                                                ingredient_id=ingredient_id,
                                                quantity=quantity
                                            )
                                            session.add(new_item)
                                            session.commit()
                                            st.success("Ingredient added to recipe!")
                                            st.rerun()
                                
                                if recipe.recipe_items:
                                    st.write("**Current Ingredients (Click to Remove)**")
                                    for item in recipe.recipe_items:
                                        col_name, col_qty, col_remove = st.columns([2, 1, 1])
                                        
                                        with col_name:
                                            st.write(f"{item.ingredient.name}")
                                        
                                        with col_qty:
                                            st.write(f"{item.quantity:.2f} {item.ingredient.unit}")
                                        
                                        with col_remove:
                                            if st.button("❌", key=f"remove_item_{item.id}"):
                                                session.delete(item)
                                                session.commit()
                                                st.rerun()
            else:
                st.info("No recipes added yet. Create your first recipe below!")
        
        with tab2:
            st.subheader("Create New Recipe")

            ingredients = session.query(Ingredient).order_by(Ingredient.name).all()

            if not ingredients:
                st.warning("⚠️ You need to add ingredients first before creating recipes!")
                st.info("Go to the 'Ingredient Management' page to add ingredients.")
            else:
                # OCR Recipe Image Upload Section
                st.markdown("### 📸 Option 1: Scan Recipe Image")
                st.info("Upload a photo of your recipe to automatically extract ingredients!")

                uploaded_file = st.file_uploader(
                    "Upload Recipe Image",
                    type=['png', 'jpg', 'jpeg', 'pdf'],
                    key="recipe_image_upload",
                    help="Take a photo of your recipe card or printed recipe"
                )

                if uploaded_file is not None:
                    # Display uploaded image
                    if uploaded_file.type.startswith('image'):
                        # Use getvalue() to get bytes regardless of file pointer position
                        st.image(uploaded_file.getvalue(), caption="Uploaded Recipe", use_container_width=True)

                    # Process with OCR
                    if st.button("🔍 Extract Ingredients from Image", type="primary"):
                        with st.spinner("Reading recipe image..."):
                            try:
                                # Use getvalue() to get full file content
                                image_bytes = uploaded_file.getvalue()

                                # Parse recipe from image
                                result = parse_recipe_from_image(image_bytes, ingredients)

                                # Store in session state
                                st.session_state['ocr_recipe_result'] = result
                                st.success(f"✅ Extracted {len(result['matched_ingredients'])} ingredients from recipe!")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error processing image: {e}")

                # Display OCR Results if available
                if 'ocr_recipe_result' in st.session_state:
                    result = st.session_state['ocr_recipe_result']

                    st.markdown("---")
                    st.markdown("### 📋 Extracted Ingredients")

                    # Show raw text in expander
                    with st.expander("📄 View Extracted Text"):
                        st.text(result['raw_text'])

                    # Show matched ingredients with selection options
                    st.write(f"**Found {len(result['matched_ingredients'])} ingredients:**")

                    # Create a form for ingredient selection
                    matched_selections = []

                    for idx, matched in enumerate(result['matched_ingredients']):
                        parsed = matched['parsed']
                        matches = matched['matches']

                        st.write(f"**{idx + 1}. {parsed['raw_line']}**")

                        col1, col2, col3 = st.columns([3, 1, 1])

                        with col1:
                            if len(matches) == 0:
                                st.warning(f"⚠️ No match found for '{parsed['ingredient_name']}' - You may need to add this ingredient first")
                                selected_ingredient = None
                            elif len(matches) == 1:
                                # Only one match - auto-select
                                ingredient_obj, score = matches[0]
                                st.success(f"✓ Matched: {ingredient_obj.name} (confidence: {score*100:.0f}%)")
                                selected_ingredient = ingredient_obj.id
                            else:
                                # Multiple matches - show dropdown
                                st.info(f"🔍 Multiple matches found - please select:")
                                match_options = [m[0].id for m in matches]
                                match_labels = {m[0].id: f"{m[0].name} ({m[1]*100:.0f}% match)" for m in matches}

                                selected_ingredient = st.selectbox(
                                    "Select ingredient",
                                    options=[None] + match_options,
                                    format_func=lambda x: "-- Skip this ingredient --" if x is None else match_labels[x],
                                    key=f"ocr_match_{idx}"
                                )

                        with col2:
                            # Quantity
                            default_qty = parsed['quantity'] if parsed['quantity'] else 1.0
                            quantity = st.number_input(
                                "Quantity",
                                min_value=0.01,
                                value=float(default_qty),
                                step=0.1,
                                key=f"ocr_qty_{idx}"
                            )

                        with col3:
                            # Unit (just for display)
                            unit_display = parsed['unit'] if parsed['unit'] else 'units'
                            st.text_input(
                                "Unit",
                                value=unit_display,
                                disabled=True,
                                key=f"ocr_unit_{idx}"
                            )

                        if selected_ingredient:
                            matched_selections.append({
                                'ingredient_id': selected_ingredient,
                                'quantity': quantity
                            })

                        st.write("---")

                    # Store selections in session state
                    st.session_state['ocr_ingredient_selections'] = matched_selections

                    if st.button("✅ Use These Ingredients", type="primary"):
                        st.success(f"Selected {len(matched_selections)} ingredients - scroll down to complete the recipe!")
                        st.info("👇 Fill in the recipe name and price below, then click 'Create Recipe'")

                    if st.button("🗑️ Clear and Start Over"):
                        del st.session_state['ocr_recipe_result']
                        if 'ocr_ingredient_selections' in st.session_state:
                            del st.session_state['ocr_ingredient_selections']
                        st.rerun()

                st.markdown("---")
                st.markdown("### ✍️ Option 2: Manual Entry")

                # Get OCR selections if available, otherwise use manual entry
                with st.form("add_recipe_form"):
                    recipe_name = st.text_input("Recipe Name *", placeholder="e.g., Chocolate Chip Cookie")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        sale_price = st.number_input("Sale Price (£) *", min_value=0.0, step=0.01, value=0.0)
                    
                    with col2:
                        category = st.text_input("Category", placeholder="e.g., Cookies")
                    
                    description = st.text_area("Description (optional)", placeholder="Any notes or special instructions")
                    square_id = st.text_input("Square Item ID (optional)", placeholder="Leave blank if not syncing with Square")
                    
                    st.write("---")
                    st.write("**Add Ingredients to Recipe**")
                    st.info("You can add more ingredients after creating the recipe by editing it.")
                    
                    num_ingredients = st.number_input("How many ingredients to add now?", min_value=0, max_value=20, value=3, step=1)
                    
                    ingredient_selections = []
                    
                    for i in range(int(num_ingredients)):
                        st.write(f"**Ingredient #{i+1}**")
                        col_ing, col_qty = st.columns(2)
                        
                        with col_ing:
                            ingredient_id = st.selectbox(
                                f"Ingredient",
                                options=[ing.id for ing in ingredients],
                                format_func=lambda x: next(ing.name for ing in ingredients if ing.id == x),
                                key=f"new_recipe_ing_{i}"
                            )
                        
                        with col_qty:
                            quantity = st.number_input(
                                f"Quantity",
                                min_value=0.01,
                                step=0.1,
                                value=1.0,
                                key=f"new_recipe_qty_{i}"
                            )
                        
                        ingredient_selections.append({'id': ingredient_id, 'quantity': quantity})
                    
                    submitted = st.form_submit_button("➕ Create Recipe")

                    if submitted:
                        if not recipe_name or sale_price <= 0:
                            st.error("Please provide a recipe name and sale price!")
                        else:
                            existing = session.query(Recipe).filter_by(name=recipe_name).first()

                            if existing:
                                st.error(f"Recipe '{recipe_name}' already exists!")
                            else:
                                new_recipe = Recipe(
                                    name=recipe_name,
                                    sale_price=sale_price,
                                    category=category,
                                    description=description,
                                    square_item_id=square_id if square_id else None
                                )

                                session.add(new_recipe)
                                session.commit()

                                # Use OCR selections if available, otherwise manual selections
                                final_selections = ingredient_selections
                                if 'ocr_ingredient_selections' in st.session_state and st.session_state['ocr_ingredient_selections']:
                                    # Convert OCR selections to match format
                                    final_selections = [
                                        {'id': s['ingredient_id'], 'quantity': s['quantity']}
                                        for s in st.session_state['ocr_ingredient_selections']
                                    ]

                                for selection in final_selections:
                                    recipe_item = RecipeItem(
                                        recipe_id=new_recipe.id,
                                        ingredient_id=selection['id'],
                                        quantity=selection['quantity']
                                    )
                                    session.add(recipe_item)

                                session.commit()

                                # Clear OCR session state
                                if 'ocr_recipe_result' in st.session_state:
                                    del st.session_state['ocr_recipe_result']
                                if 'ocr_ingredient_selections' in st.session_state:
                                    del st.session_state['ocr_ingredient_selections']

                                st.success(f"✅ Created recipe: {recipe_name} with {len(final_selections)} ingredients!")
                                st.rerun()
    
    finally:
        close_session(session)
