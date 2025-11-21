import streamlit as st
from database import get_session, close_session
from models import Recipe, Ingredient, RecipeItem, SalesCache
from utils import calculate_recipe_cost, calculate_profit_margin
from styling import inject_custom_css, render_page_header
from unit_conversions import BAKING_CONVERSIONS
from square_api import SquareAPI
import pandas as pd
from sqlalchemy import func

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
                # Square Items Import Section
                st.markdown("### 📲 Option 1: Import from Square")
                st.info("Import items from your Square catalog to create recipes automatically")

                square_api = SquareAPI()

                if square_api.is_configured:
                    if st.button("🔄 Fetch Square Items", type="primary"):
                        with st.spinner("Fetching items from Square..."):
                            st.session_state['square_items'] = square_api.get_catalog_items()
                            st.success(f"✅ Fetched {len(st.session_state.get('square_items', []))} items from Square!")

                    # Display Square items if fetched
                    if 'square_items' in st.session_state and st.session_state['square_items']:
                        square_items = st.session_state['square_items']

                        # Get existing recipes with Square IDs
                        existing_square_ids = {r.square_item_id for r in session.query(Recipe).all() if r.square_item_id}

                        # Separate into items with/without recipes
                        items_without_recipes = [item for item in square_items if item['id'] not in existing_square_ids]
                        items_with_recipes = [item for item in square_items if item['id'] in existing_square_ids]

                        st.write(f"**Square Items:** {len(square_items)} total | {len(items_with_recipes)} with recipes | {len(items_without_recipes)} need recipes")

                        # Show items that need recipes
                        if items_without_recipes:
                            # Check if we're currently creating a recipe from a Square item
                            if 'creating_square_recipe' in st.session_state:
                                # Show ingredient selection form for the selected Square item
                                selected_item = st.session_state['creating_square_recipe']

                                st.markdown(f"### 🎂 Creating Recipe: {selected_item['name']}")
                                st.write(f"**Sale Price:** £{selected_item['price']:.2f}")
                                st.write(f"**Square ID:** {selected_item['id']}")
                                st.markdown("---")

                                with st.form(key="create_square_recipe_with_ingredients"):
                                    st.write("**Add Ingredients to This Recipe**")
                                    st.info("Select the ingredients and quantities for this recipe. You can always add more later!")

                                    # Optional category and description
                                    category = st.text_input("Category (optional)", value="Imported from Square", placeholder="e.g., Cakes, Cookies, Drinks")
                                    description = st.text_area("Description (optional)", placeholder="Any notes or special instructions")

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
                                                key=f"square_recipe_ing_{i}"
                                            )

                                        selected_ing = next(ing for ing in ingredients if ing.id == ingredient_id)

                                        with col_qty:
                                            quantity = st.number_input(
                                                "Quantity",
                                                min_value=0.01,
                                                step=0.1,
                                                value=1.0,
                                                key=f"square_recipe_qty_{i}"
                                            )

                                        with col_unit:
                                            st.text_input(
                                                "Unit",
                                                value=selected_ing.unit,
                                                disabled=True,
                                                key=f"square_recipe_unit_{i}",
                                                help=f"This ingredient is measured in {selected_ing.unit}"
                                            )

                                        ingredient_selections.append({'id': ingredient_id, 'quantity': quantity})

                                    col_create, col_cancel = st.columns(2)

                                    with col_create:
                                        create_submitted = st.form_submit_button("✅ Create Recipe with Ingredients", type="primary")

                                    with col_cancel:
                                        cancel_submitted = st.form_submit_button("❌ Cancel")

                                    if create_submitted:
                                        # Create the recipe
                                        new_recipe = Recipe(
                                            name=selected_item['name'],
                                            square_item_id=selected_item['id'],
                                            sale_price=selected_item['price'],
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
                                        del st.session_state['creating_square_recipe']

                                        st.success(f"✅ Created recipe for '{selected_item['name']}' with {len(ingredient_selections)} ingredients!")
                                        st.rerun()

                                    if cancel_submitted:
                                        del st.session_state['creating_square_recipe']
                                        st.rerun()

                            else:
                                # Show list of Square items without recipes
                                with st.expander(f"📋 Items Without Recipes ({len(items_without_recipes)})", expanded=True):
                                    for idx, item in enumerate(items_without_recipes[:10]):  # Show first 10
                                        col1, col2, col3 = st.columns([3, 1, 1])

                                        with col1:
                                            st.write(f"**{item['name']}**")

                                        with col2:
                                            st.write(f"£{item['price']:.2f}")

                                        with col3:
                                            if st.button("➕ Create Recipe", key=f"create_from_square_{item['id']}"):
                                                # Store the selected item in session state
                                                st.session_state['creating_square_recipe'] = item
                                                st.rerun()

                                    if len(items_without_recipes) > 10:
                                        st.info(f"Showing first 10 of {len(items_without_recipes)} items. Scroll to create more.")

                        # Show items that already have recipes
                        if items_with_recipes:
                            with st.expander(f"✅ Items With Recipes ({len(items_with_recipes)})"):
                                for item in items_with_recipes[:10]:
                                    recipe = session.query(Recipe).filter_by(square_item_id=item['id']).first()
                                    st.write(f"- **{item['name']}** → Recipe: {recipe.name if recipe else 'Unknown'}")

                else:
                    st.warning("⚠️ Square API not configured. Go to 'Square Setup' page to configure.")

                st.markdown("---")

                # Sales History Import Section (Alternative to Square Catalog)
                st.markdown("### 📊 Option 1B: Import from Sales History")
                st.info("Can't access Square catalog? Create recipes from your existing sales data instead!")

                if st.button("📈 Load Items from Sales History", type="secondary"):
                    with st.spinner("Loading items from sales history..."):
                        # Get unique items from sales cache with average prices
                        sales_items_query = session.query(
                            SalesCache.item_name,
                            func.avg(SalesCache.total_amount / SalesCache.quantity).label('avg_price'),
                            func.sum(SalesCache.quantity).label('total_sold')
                        ).group_by(SalesCache.item_name).all()

                        sales_items = []
                        for item_name, avg_price, total_sold in sales_items_query:
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
                    existing_recipe_names = {r.name.lower() for r in session.query(Recipe).all()}

                    # Separate into items with/without recipes
                    items_without_recipes_sales = [item for item in sales_items if item['name'].lower() not in existing_recipe_names]
                    items_with_recipes_sales = [item for item in sales_items if item['name'].lower() in existing_recipe_names]

                    st.write(f"**Sales Items:** {len(sales_items)} total | {len(items_with_recipes_sales)} with recipes | {len(items_without_recipes_sales)} need recipes")

                    # Show items that need recipes
                    if items_without_recipes_sales:
                        # Check if we're currently creating a recipe from a sales item
                        if 'creating_sales_recipe' in st.session_state:
                            # Show ingredient selection form for the selected sales item
                            selected_item = st.session_state['creating_sales_recipe']

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
                            # Show list of sales items without recipes
                            with st.expander(f"📋 Items Without Recipes ({len(items_without_recipes_sales)})", expanded=True):
                                # Sort by total sold descending
                                sorted_items = sorted(items_without_recipes_sales, key=lambda x: x['total_sold'], reverse=True)

                                for item in sorted_items[:10]:  # Show first 10
                                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

                                    with col1:
                                        st.write(f"**{item['name']}**")

                                    with col2:
                                        st.write(f"£{item['price']:.2f}")

                                    with col3:
                                        st.write(f"{item['total_sold']} sold")

                                    with col4:
                                        if st.button("➕ Create Recipe", key=f"create_from_sales_{item['name'].replace(' ', '_')}"):
                                            # Store the selected item in session state
                                            st.session_state['creating_sales_recipe'] = item
                                            st.rerun()

                                if len(items_without_recipes_sales) > 10:
                                    st.info(f"Showing top 10 by sales. {len(items_without_recipes_sales)} items total.")

                    # Show items that already have recipes
                    if items_with_recipes_sales:
                        with st.expander(f"✅ Items With Recipes ({len(items_with_recipes_sales)})"):
                            for item in items_with_recipes_sales[:10]:
                                st.write(f"- **{item['name']}** (Sold: {item['total_sold']} units)")

                st.markdown("---")
                st.markdown("### ✍️ Option 2: Manual Entry")
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
                    square_id = st.text_input("Square Item ID (optional)", placeholder="Leave blank if not syncing with Square")
                    
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
                                f"Ingredient",
                                options=[ing.id for ing in ingredients],
                                format_func=lambda x: next(ing.name for ing in ingredients if ing.id == x),
                                key=f"new_recipe_ing_{i}"
                            )

                        # Get the selected ingredient to show its unit
                        selected_ing = next(ing for ing in ingredients if ing.id == ingredient_id)

                        with col_qty:
                            quantity = st.number_input(
                                f"Quantity",
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
