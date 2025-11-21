"""
Natasha's Law - The 14 Major Allergens (UK/NI)
According to UK Food Information Regulations 2014
"""

# The 14 major allergens that must be declared
MAJOR_ALLERGENS = [
    "Cereals containing gluten (wheat)",
    "Cereals containing gluten (rye)",
    "Cereals containing gluten (barley)",
    "Cereals containing gluten (oats)",
    "Cereals containing gluten (spelt)",
    "Cereals containing gluten (kamut)",
    "Crustaceans",
    "Eggs",
    "Fish",
    "Peanuts",
    "Soybeans",
    "Milk",
    "Nuts (almonds)",
    "Nuts (hazelnuts)",
    "Nuts (walnuts)",
    "Nuts (cashews)",
    "Nuts (pecan nuts)",
    "Nuts (Brazil nuts)",
    "Nuts (pistachio nuts)",
    "Nuts (macadamia nuts)",
    "Celery",
    "Mustard",
    "Sesame seeds",
    "Sulphur dioxide and sulphites",
    "Lupin",
    "Molluscs"
]

# Simplified list for easier selection
ALLERGEN_CATEGORIES = {
    "Gluten": ["Wheat", "Rye", "Barley", "Oats", "Spelt", "Kamut"],
    "Crustaceans": ["Crustaceans (e.g., prawns, crabs, lobster, crayfish)"],
    "Eggs": ["Eggs"],
    "Fish": ["Fish"],
    "Peanuts": ["Peanuts"],
    "Soybeans": ["Soybeans (Soya)"],
    "Milk": ["Milk (including lactose)"],
    "Tree Nuts": ["Almonds", "Hazelnuts", "Walnuts", "Cashews", "Pecan nuts", "Brazil nuts", "Pistachio nuts", "Macadamia nuts"],
    "Celery": ["Celery (including celeriac)"],
    "Mustard": ["Mustard"],
    "Sesame": ["Sesame seeds"],
    "Sulphites": ["Sulphur dioxide and sulphites (at >10mg/kg or 10mg/L)"],
    "Lupin": ["Lupin"],
    "Molluscs": ["Molluscs (e.g., mussels, oysters, squid, snails)"]
}

def format_allergens_for_label(allergens_list):
    """
    Format allergens list for Natasha's Law label (bold formatting indicator)
    Returns: String with allergens in correct format
    """
    if not allergens_list:
        return ""

    # Remove duplicates and sort
    unique_allergens = sorted(list(set(allergens_list)))

    # Format for label (will be bolded in final output)
    formatted = []
    for allergen in unique_allergens:
        # Convert to bold format for labels
        formatted.append(f"**{allergen}**")

    return ", ".join(formatted)


def get_all_allergens_from_ingredients(recipe_items):
    """
    Extract all allergens from a recipe's ingredients
    Returns: Set of allergen strings
    """
    import json

    all_allergens = set()

    for recipe_item in recipe_items:
        ingredient = recipe_item.ingredient

        # Parse allergens from JSON
        if ingredient.allergens:
            try:
                allergens = json.loads(ingredient.allergens)
                all_allergens.update(allergens)
            except:
                # If not JSON, treat as comma-separated
                allergens = [a.strip() for a in ingredient.allergens.split(',') if a.strip()]
                all_allergens.update(allergens)

    return all_allergens


def get_may_contain_warnings(recipe_items):
    """
    Get all "may contain" warnings from ingredients
    Returns: Set of warning strings
    """
    import json

    warnings = set()

    for recipe_item in recipe_items:
        ingredient = recipe_item.ingredient

        if ingredient.may_contain:
            try:
                may_contain = json.loads(ingredient.may_contain)
                warnings.update(may_contain)
            except:
                # If not JSON, treat as comma-separated
                may_contain = [w.strip() for w in ingredient.may_contain.split(',') if w.strip()]
                warnings.update(may_contain)

    return warnings
