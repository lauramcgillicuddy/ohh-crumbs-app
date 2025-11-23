import streamlit as st
from database import get_session, close_session
from models import Recipe, Ingredient, RecipeItem, SalesCache, ProductionBatch
from utils import calculate_recipe_cost, calculate_profit_margin
from styling import inject_custom_css, render_page_header
from unit_conversions import BAKING_CONVERSIONS
from square_api import SquareAPI
import pandas as pd
from sqlalchemy import func
from label_generator import generate_natasha_label, format_label_for_display, generate_printable_label_html
from allergens import get_all_allergens_from_ingredients, get_may_contain_warnings
import json

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

                            # Show allergen information
                            st.markdown("---")
                            st.markdown("**🏷️ Allergen Information:**")

                            allergens = get_all_allergens_from_ingredients(recipe.recipe_items)
                            may_contain = get_may_contain_warnings(recipe.recipe_items)

                            if allergens:
                                st.warning(f"**Contains:** {', '.join(sorted(allergens))}")
                            else:
                                st.success("No allergens detected")

                            if may_contain:
                                st.info(f"**May contain:** {', '.join(sorted(may_contain))}")

                            col_label, col_scale = st.columns(2)

                            with col_label:
                                # Generate Label button
                                if st.button(f"📄 Generate Natasha's Law Label", key=f"generate_label_{recipe.id}"):
                                    st.session_state[f'show_label_{recipe.id}'] = True

                            with col_scale:
                                # Recipe Scaling Calculator
                                if st.button(f"⚖️ Scale Recipe", key=f"scale_recipe_{recipe.id}"):
                                    st.session_state[f'show_scale_{recipe.id}'] = True

                            # Show scaling calculator if requested
                            if st.session_state.get(f'show_scale_{recipe.id}', False):
                                st.markdown("---")
                                st.markdown("### ⚖️ Recipe Scaling Calculator")

                                scale_factor = st.number_input(
                                    "Scale Factor (e.g., 2 = double, 0.5 = half)",
                                    min_value=0.1,
                                    max_value=100.0,
                                    value=1.0,
                                    step=0.1,
                                    key=f"scale_factor_{recipe.id}",
                                    help="Enter multiplier: 2 = double batch, 3 = triple batch, 0.5 = half batch"
                                )

                                # Quick scale buttons
                                st.write("**Quick Scale:**")
                                col_half, col_double, col_triple = st.columns(3)

                                with col_half:
                                    if st.button("× 0.5 (Half)", key=f"scale_half_{recipe.id}"):
                                        st.session_state[f'scale_factor_{recipe.id}'] = 0.5
                                        st.rerun()

                                with col_double:
                                    if st.button("× 2 (Double)", key=f"scale_double_{recipe.id}"):
                                        st.session_state[f'scale_factor_{recipe.id}'] = 2.0
                                        st.rerun()

                                with col_triple:
                                    if st.button("× 3 (Triple)", key=f"scale_triple_{recipe.id}"):
                                        st.session_state[f'scale_factor_{recipe.id}'] = 3.0
                                        st.rerun()

                                st.markdown("---")

                                # Scaled recipe
                                st.write(f"**Scaled Recipe for {recipe.name} (× {scale_factor})**")
                                st.write("")

                                scaled_cost = 0.0
                                for item in recipe.recipe_items:
                                    scaled_qty = item.quantity * scale_factor
                                    item_cost = item.ingredient.cost_per_unit * scaled_qty
                                    scaled_cost += item_cost
                                    st.write(f"• {scaled_qty:.2f} {item.ingredient.unit} of {item.ingredient.name} (£{item_cost:.2f})")

                                st.markdown("---")

                                col_metrics1, col_metrics2, col_metrics3 = st.columns(3)

                                with col_metrics1:
                                    st.metric("Total Cost", f"£{scaled_cost:.2f}")

                                with col_metrics2:
                                    scaled_revenue = recipe.sale_price * scale_factor
                                    st.metric("Revenue", f"£{scaled_revenue:.2f}")

                                with col_metrics3:
                                    scaled_profit = scaled_revenue - scaled_cost
                                    st.metric("Profit", f"£{scaled_profit:.2f}")

                                # Check ingredient availability
                                st.markdown("---")
                                st.write("**📦 Ingredient Availability Check:**")

                                can_make = True
                                for item in recipe.recipe_items:
                                    scaled_qty = item.quantity * scale_factor
                                    ingredient = item.ingredient

                                    if ingredient.current_stock >= scaled_qty:
                                        st.success(f"✅ {ingredient.name}: {ingredient.current_stock:.2f} {ingredient.unit} available (need {scaled_qty:.2f})")
                                    else:
                                        st.error(f"❌ {ingredient.name}: Only {ingredient.current_stock:.2f} {ingredient.unit} available (need {scaled_qty:.2f})")
                                        shortage = scaled_qty - ingredient.current_stock
                                        st.write(f"    Short by: {shortage:.2f} {ingredient.unit}")
                                        can_make = False

                                if can_make:
                                    st.success(f"🎉 You have enough ingredients to make {scale_factor}× {recipe.name}!")
                                else:
                                    st.warning("⚠️ Not enough ingredients in stock. Order more or reduce scale factor.")

                                if st.button("❌ Close Calculator", key=f"close_scale_{recipe.id}"):
                                    st.session_state[f'show_scale_{recipe.id}'] = False
                                    st.rerun()

                            # Show label if requested
                            if st.session_state.get(f'show_label_{recipe.id}', False):
                                st.markdown("---")
                                st.markdown("### 📋 Natasha's Law Label")

                                label = generate_natasha_label(recipe)

                                # Show warnings if allergen info is incomplete
                                if not label['is_complete']:
                                    st.error(f"⚠️ **INCOMPLETE ALLERGEN DATA** - The following ingredients are missing allergen information:")
                                    for ing_name in label['missing_allergen_info']:
                                        st.write(f"  • {ing_name}")
                                    st.warning("🔧 Go to the **Ingredients** page to add allergen information for these ingredients before using this label!")
                                    st.markdown("---")

                                label_text = format_label_for_display(label)
                                st.markdown(label_text)

                                # Printable HTML version - use a checkbox instead of expander
                                show_html = st.checkbox("🖨️ Show Printable HTML Version", key=f"show_html_{recipe.id}")
                                if show_html:
                                    html_label = generate_printable_label_html(label)
                                    st.components.v1.html(html_label, height=600, scrolling=True)

                                if st.button("❌ Close Label", key=f"close_label_{recipe.id}"):
                                    st.session_state[f'show_label_{recipe.id}'] = False
                                    st.rerun()

                        else:
                            st.info("No ingredients added to this recipe yet.")

                        col_edit, col_delete = st.columns(2)
                        
                        with col_edit:
                            if st.button(f"✏️ Edit Recipe", key=f"edit_recipe_{recipe.id}"):
                                st.session_state[f'editing_recipe_{recipe.id}'] = True
                        
                        with col_delete:
                            if st.button(f"🗑️ Delete Recipe", key=f"delete_recipe_{recipe.id}"):
                                # Check if recipe is used in any production batches
                                production_uses = session.query(ProductionBatch).filter(
                                    ProductionBatch.recipe_id == recipe.id
                                ).count()

                                if production_uses > 0:
                                    st.error(f"❌ Cannot delete {recipe.name} - it's been used in {production_uses} production batch(es). This is historical data that should be kept!")
                                else:
                                    try:
                                        # Delete recipe items first (they're part of the recipe)
                                        session.query(RecipeItem).filter(
                                            RecipeItem.recipe_id == recipe.id
                                        ).delete()

                                        # Then delete the recipe
                                        session.delete(recipe)
                                        session.commit()
                                        st.success(f"✅ Deleted recipe: {recipe.name}")
                                        st.rerun()
                                    except Exception as e:
                                        session.rollback()
                                        st.error(f"Error deleting recipe: {str(e)}")
                        
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
                                    col_ing, col_qty, col_unit = st.columns([2, 1, 1])

                                    with col_ing:
                                        ingredient_id = st.selectbox(
                                            "Select Ingredient",
                                            options=[ing.id for ing in ingredients],
                                            format_func=lambda x: next(ing.name for ing in ingredients if ing.id == x)
                                        )

                                    # Get selected ingredient to show unit
                                    selected_ingredient = next(ing for ing in ingredients if ing.id == ingredient_id)

                                    with col_qty:
                                        quantity = st.number_input("Quantity", min_value=0.01, step=0.1, value=1.0)

                                    with col_unit:
                                        st.text_input(
                                            "Unit",
                                            value=selected_ingredient.unit,
                                            disabled=True,
                                            key=f"edit_recipe_unit_{recipe.id}",
                                            help=f"Measured in {selected_ingredient.unit}"
                                        )

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
                # Sales History Import Section
                st.markdown("### 📊 Import from Square Sales History")
                st.info("Create recipes from your existing Square sales data with ingredients from your saved list!")

                if st.button("📈 Load Items from Sales History", type="primary"):
                    with st.spinner("Loading items from sales history..."):
                        # Get unique items from sales cache with average prices
                        sales_items_query = session.query(
                            SalesCache.item_name,
                            func.avg(SalesCache.total_amount / SalesCache.quantity).label('avg_price'),
                            func.sum(SalesCache.quantity).label('total_sold')
                        ).group_by(SalesCache.item_name).all()

                        sales_items = []
                        for item_name, avg_price, total_sold in sales_items_query:
                            # Skip items with no name
                            if item_name and item_name.strip():
                                sales_items.append({
                                    'name': item_name,
                                    'price': float(avg_price) if avg_price else 0.0,
                                    'total_sold': int(total_sold) if total_sold else 0,
                                    'source': 'sales_history'
                                })

                        st.session_state['sales_history_items'] = sales_items
                        st.success(f"✅ Found {len(sales_items)} items from your sales history!")

                # Display sales history items if loaded
                if 'sales_history_items' in st.session_state and st.session_state['sales_history_items']:
                    sales_items = st.session_state['sales_history_items']

                    # Get existing recipe names
                    existing_recipe_names = {r.name.lower() for r in session.query(Recipe).all() if r.name}

                    # Separate into items with/without recipes
                    items_without_recipes_sales = [item for item in sales_items if item['name'].lower() not in existing_recipe_names]
                    items_with_recipes_sales = [item for item in sales_items if item['name'].lower() in existing_recipe_names]

                    st.write(f"**Sales Items:** {len(sales_items)} total | {len(items_with_recipes_sales)} with recipes | {len(items_without_recipes_sales)} need recipes")

                    # Check if we're currently creating a recipe from a sales item
                    if 'creating_sales_recipe' in st.session_state:
                        # Show ingredient selection form for the selected sales item
                        selected_item = st.session_state['creating_sales_recipe']

                        if selected_item:

                            st.markdown(f"### 🎂 Creating Recipe: {selected_item['name']}")
                            st.write(f"**Average Sale Price:** £{selected_item['price']:.2f}")
                            st.write(f"**Total Units Sold:** {selected_item['total_sold']}")
                            st.markdown("---")

                            with st.form(key="create_sales_recipe_with_ingredients"):
                                st.write("**Add Ingredients to This Recipe**")
                                st.info("Select the ingredients and quantities for this recipe. You can always add more later!")

                                # Optional category and description
                                category = st.text_input("Category (optional)", value="From Sales History", placeholder="e.g., Cakes, Cookies, Drinks")
                                description = st.text_area("Description (optional)", placeholder="Any notes or special instructions")

                                # Editable sale price (pre-filled with average)
                                sale_price = st.number_input("Sale Price (£)", value=float(selected_item['price']), min_value=0.01, step=0.01)

                                num_ingredients = st.number_input("How many ingredients to add now?", min_value=0, max_value=20, value=3, step=1)

                                ingredient_selections = []

                                for i in range(int(num_ingredients)):
                                    st.write(f"**Ingredient #{i+1}**")
                                    col_ing, col_qty, col_unit = st.columns([2, 1, 1])

                                    with col_ing:
                                        ingredient_id = st.selectbox(
                                            "Ingredient",
                                            options=[ing.id for ing in ingredients],
                                            format_func=lambda x: next(ing.name for ing in ingredients if ing.id == x),
                                            key=f"sales_recipe_ing_{i}"
                                        )

                                    selected_ing = next(ing for ing in ingredients if ing.id == ingredient_id)

                                    with col_qty:
                                        quantity = st.number_input(
                                            "Quantity",
                                            min_value=0.01,
                                            step=0.1,
                                            value=1.0,
                                            key=f"sales_recipe_qty_{i}"
                                        )

                                    with col_unit:
                                        st.text_input(
                                            "Unit",
                                            value=selected_ing.unit,
                                            disabled=True,
                                            key=f"sales_recipe_unit_{i}",
                                            help=f"This ingredient is measured in {selected_ing.unit}"
                                        )

                                    ingredient_selections.append({'id': ingredient_id, 'quantity': quantity})

                                col_create, col_cancel = st.columns(2)

                                with col_create:
                                    create_submitted = st.form_submit_button("✅ Create Recipe with Ingredients", type="primary")

                                with col_cancel:
                                    cancel_submitted = st.form_submit_button("❌ Cancel")

                                if create_submitted:
                                    # Check if recipe already exists
                                    existing_recipe = session.query(Recipe).filter(
                                        func.lower(Recipe.name) == selected_item['name'].lower()
                                    ).first()

                                    if existing_recipe:
                                        st.error(f"❌ Recipe '{selected_item['name']}' already exists! Please check the 'View Recipes' tab.")
                                    else:
                                        # Create the recipe
                                        new_recipe = Recipe(
                                            name=selected_item['name'],
                                            square_item_id=None,  # No Square ID for sales history items
                                            sale_price=sale_price,
                                            category=category,
                                            description=description
                                        )
                                        session.add(new_recipe)
                                        session.commit()

                                        # Add ingredients
                                        for selection in ingredient_selections:
                                            recipe_item = RecipeItem(
                                                recipe_id=new_recipe.id,
                                                ingredient_id=selection['id'],
                                                quantity=selection['quantity']
                                            )
                                            session.add(recipe_item)

                                        session.commit()

                                        # Clear the session state
                                        del st.session_state['creating_sales_recipe']

                                        st.success(f"✅ Created recipe for '{selected_item['name']}' with {len(ingredient_selections)} ingredients!")
                                        st.rerun()

                                if cancel_submitted:
                                    del st.session_state['creating_sales_recipe']
                                    st.rerun()

                    else:
                        # Show ALL sales items in a scrollable container
                        st.markdown("### 📋 All Sales Items")
                        st.info("Scroll through all your sales items. Items already in the database are marked with ✅")

                        # Sort all items by total sold descending
                        sorted_all_items = sorted(sales_items, key=lambda x: x['total_sold'], reverse=True)

                        # Create scrollable container with max height
                        with st.container():
                            # Add custom CSS for scrollable area
                            st.markdown("""
                                <style>
                                .scrollable-items {
                                    max-height: 600px;
                                    overflow-y: auto;
                                    padding: 10px;
                                }
                                </style>
                            """, unsafe_allow_html=True)

                            for item in sorted_all_items:
                                # Check if recipe exists
                                has_recipe = item['name'].lower() in existing_recipe_names

                                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                                with col1:
                                    if has_recipe:
                                        st.write(f"✅ **{item['name']}** *(Already in database)*")
                                    else:
                                        st.write(f"**{item['name']}**")

                                with col2:
                                    st.write(f"£{item['price']:.2f}")

                                with col3:
                                    st.write(f"{item['total_sold']} sold")

                                with col4:
                                    if has_recipe:
                                        st.write("✅ Done")
                                    else:
                                        if st.button("➕ Create", key=f"create_from_sales_{item['name'].replace(' ', '_').replace('/', '_')}"):
                                            # Store the selected item in session state
                                            st.session_state['creating_sales_recipe'] = item
                                            st.rerun()

                                st.markdown("---")

                st.markdown("---")
                st.markdown("### ✍️ Manual Recipe Entry")
                st.info("Create a recipe from scratch if it's not in your sales history")

                # Conversion reference
                with st.expander("📏 Unit Conversion Reference"):
                    st.markdown(BAKING_CONVERSIONS)
                    st.info("💡 **Tip:** Enter quantities in the same unit as the ingredient (shown in the 'Unit' column)")

                with st.form("add_recipe_form"):
                    recipe_name = st.text_input("Recipe Name *", placeholder="e.g., Chocolate Chip Cookie")

                    col1, col2 = st.columns(2)

                    with col1:
                        sale_price = st.number_input("Sale Price (£) *", min_value=0.0, step=0.01, value=0.0)

                    with col2:
                        category = st.text_input("Category", placeholder="e.g., Cookies")

                    description = st.text_area("Description (optional)", placeholder="Any notes or special instructions")

                    st.write("---")
                    st.write("**Add Ingredients to Recipe**")
                    st.info("You can add more ingredients after creating the recipe by editing it.")

                    num_ingredients = st.number_input("How many ingredients to add now?", min_value=0, max_value=20, value=3, step=1)

                    ingredient_selections = []

                    for i in range(int(num_ingredients)):
                        st.write(f"**Ingredient #{i+1}**")
                        col_ing, col_qty, col_unit = st.columns([2, 1, 1])

                        with col_ing:
                            ingredient_id = st.selectbox(
                                "Ingredient",
                                options=[ing.id for ing in ingredients],
                                format_func=lambda x: next(ing.name for ing in ingredients if ing.id == x),
                                key=f"new_recipe_ing_{i}"
                            )

                        # Get the selected ingredient to show its unit
                        selected_ing = next(ing for ing in ingredients if ing.id == ingredient_id)

                        with col_qty:
                            quantity = st.number_input(
                                "Quantity",
                                min_value=0.01,
                                step=0.1,
                                value=1.0,
                                key=f"new_recipe_qty_{i}"
                            )

                        with col_unit:
                            st.text_input(
                                "Unit",
                                value=selected_ing.unit,
                                disabled=True,
                                key=f"new_recipe_unit_{i}",
                                help=f"This ingredient is measured in {selected_ing.unit}"
                            )

                        ingredient_selections.append({'id': ingredient_id, 'quantity': quantity})

                    submitted = st.form_submit_button("➕ Create Recipe")

                    if submitted:
                        if not recipe_name or sale_price <= 0:
                            st.error("Please provide a recipe name and sale price!")
                        else:
                            # Check if recipe already exists
                            existing = session.query(Recipe).filter(
                                func.lower(Recipe.name) == recipe_name.lower()
                            ).first()

                            if existing:
                                st.error(f"Recipe '{recipe_name}' already exists!")
                            else:
                                new_recipe = Recipe(
                                    name=recipe_name,
                                    sale_price=sale_price,
                                    category=category,
                                    description=description,
                                    square_item_id=None
                                )

                                session.add(new_recipe)
                                session.commit()

                                for selection in ingredient_selections:
                                    recipe_item = RecipeItem(
                                        recipe_id=new_recipe.id,
                                        ingredient_id=selection['id'],
                                        quantity=selection['quantity']
                                    )
                                    session.add(recipe_item)

                                session.commit()

                                st.success(f"✅ Created recipe: {recipe_name} with {len(ingredient_selections)} ingredients!")
                                st.rerun()

    finally:
        close_session(session)
