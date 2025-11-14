import streamlit as st
from database import get_session, close_session
from models import Recipe, Ingredient, RecipeItem
from utils import calculate_recipe_cost, calculate_profit_margin
from styling import inject_custom_css, render_page_header

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
                                
                                for selection in ingredient_selections:
                                    recipe_item = RecipeItem(
                                        recipe_id=new_recipe.id,
                                        ingredient_id=selection['id'],
                                        quantity=selection['quantity']
                                    )
                                    session.add(recipe_item)
                                
                                session.commit()
                                st.success(f"✅ Created recipe: {recipe_name}")
                                st.rerun()
    
    finally:
        close_session(session)
