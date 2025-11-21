"""
Natasha's Law Label Generator
Generates compliant ingredient labels for Northern Ireland
"""

import json
from datetime import datetime, timedelta
from allergens import get_all_allergens_from_ingredients, get_may_contain_warnings


def generate_natasha_label(recipe, business_info=None):
    """
    Generate a Natasha's Law compliant label for a recipe

    Returns: Dictionary with label components
    """

    # Default business info
    if not business_info:
        business_info = {
            "name": "Ohh Crumbs Bakery",
            "address": "Your Business Address, Northern Ireland",
            "phone": "Your Phone Number"
        }

    # Collect all ingredients with sub-ingredients
    ingredients_list = []

    for recipe_item in sorted(recipe.recipe_items, key=lambda x: x.quantity, reverse=True):
        ingredient = recipe_item.ingredient

        # Get ingredient name
        ingredient_text = ingredient.name

        # Add sub-ingredients if present (for compound ingredients)
        if ingredient.sub_ingredients:
            ingredient_text += f" ({ingredient.sub_ingredients})"

        # Check for allergens and format them
        if ingredient.allergens:
            try:
                allergens = json.loads(ingredient.allergens)
                if allergens:
                    # Bold the allergen-containing ingredient
                    ingredient_text = f"**{ingredient_text}**"
            except:
                pass

        ingredients_list.append(ingredient_text)

    # Get all allergens
    allergens = get_all_allergens_from_ingredients(recipe.recipe_items)
    allergens_text = ", ".join(sorted(allergens)) if allergens else "None"

    # Get may contain warnings
    may_contain = get_may_contain_warnings(recipe.recipe_items)
    may_contain_text = ", ".join(sorted(may_contain)) if may_contain else ""

    # Storage instructions
    storage = recipe.storage_instructions if recipe.storage_instructions else "Store in a cool, dry place"

    # Use by date (if specified)
    use_by_text = ""
    if recipe.use_by_days:
        use_by_date = datetime.now() + timedelta(days=recipe.use_by_days)
        use_by_text = use_by_date.strftime("%d/%m/%Y")

    # Build the label
    label = {
        "product_name": recipe.name,
        "ingredients": ingredients_list,
        "ingredients_text": "Ingredients: " + ", ".join(ingredients_list),
        "allergens": allergens,
        "allergens_text": f"**Allergens:** {allergens_text}" if allergens else "",
        "may_contain_text": f"**May contain:** {may_contain_text}" if may_contain else "",
        "storage": storage,
        "use_by": use_by_text,
        "business": business_info,
        "generated_date": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

    return label


def format_label_for_display(label):
    """
    Format label dictionary as human-readable text for display/printing
    """

    lines = []

    # Product name (large, bold)
    lines.append(f"# {label['product_name']}")
    lines.append("")

    # Ingredients (allergens in bold)
    lines.append(label['ingredients_text'])
    lines.append("")

    # Allergen statement
    if label['allergens_text']:
        lines.append(label['allergens_text'])
        lines.append("")

    # May contain
    if label['may_contain_text']:
        lines.append(label['may_contain_text'])
        lines.append("")

    # Storage
    lines.append(f"**Storage:** {label['storage']}")

    # Use by
    if label['use_by']:
        lines.append(f"**Use By:** {label['use_by']}")

    lines.append("")

    # Business info
    lines.append(f"**{label['business']['name']}**")
    lines.append(label['business']['address'])
    if 'phone' in label['business']:
        lines.append(f"Tel: {label['business']['phone']}")

    lines.append("")
    lines.append(f"*Label generated: {label['generated_date']}*")

    return "\n".join(lines)


def generate_printable_label_html(label):
    """
    Generate HTML for a printable label
    """

    html = f"""
    <div style="border: 2px solid #000; padding: 20px; max-width: 400px; font-family: Arial, sans-serif; background: white;">
        <h1 style="margin: 0 0 15px 0; font-size: 24px; text-align: center;">{label['product_name']}</h1>

        <p style="margin: 10px 0; font-size: 12px;">
            <strong>Ingredients:</strong><br>
            {', '.join(label['ingredients'])}
        </p>

        {'<p style="margin: 10px 0; font-size: 12px;"><strong>Allergens:</strong><br>' + ', '.join(sorted(label['allergens'])) + '</p>' if label['allergens'] else ''}

        {'<p style="margin: 10px 0; font-size: 11px;"><strong>May contain:</strong> ' + label['may_contain_text'].replace('**May contain:**', '').strip() + '</p>' if label['may_contain_text'] else ''}

        <p style="margin: 10px 0; font-size: 11px;">
            <strong>Storage:</strong> {label['storage']}
        </p>

        {'<p style="margin: 10px 0; font-size: 11px;"><strong>Use By:</strong> ' + label['use_by'] + '</p>' if label['use_by'] else ''}

        <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ccc; font-size: 10px;">
            <p style="margin: 3px 0;"><strong>{label['business']['name']}</strong></p>
            <p style="margin: 3px 0;">{label['business']['address']}</p>
            {'<p style="margin: 3px 0;">Tel: ' + label['business']['phone'] + '</p>' if 'phone' in label['business'] else ''}
        </div>
    </div>
    """

    return html
