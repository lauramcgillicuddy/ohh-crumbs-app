"""
Common Bakery Ingredient Allergen Templates
Pre-filled allergen information for typical bakery ingredients
"""

COMMON_INGREDIENT_TEMPLATES = {
    # Flours and grains
    "flour": {
        "keywords": ["flour", "wheat flour", "all-purpose flour", "plain flour", "self-raising flour", "bread flour"],
        "allergens": ["Wheat"],
        "sub_ingredients": "Wheat, Calcium Carbonate, Iron, Niacin, Thiamin",
        "may_contain": []
    },
    "wholemeal flour": {
        "keywords": ["wholemeal flour", "whole wheat flour", "wholewheat flour"],
        "allergens": ["Wheat"],
        "sub_ingredients": "Wholemeal Wheat",
        "may_contain": []
    },
    "spelt flour": {
        "keywords": ["spelt flour", "spelt"],
        "allergens": ["Spelt"],
        "sub_ingredients": "Spelt",
        "may_contain": []
    },
    "rye flour": {
        "keywords": ["rye flour", "rye"],
        "allergens": ["Rye"],
        "sub_ingredients": "Rye",
        "may_contain": []
    },
    "oat flour": {
        "keywords": ["oat flour", "oats"],
        "allergens": ["Oats"],
        "sub_ingredients": "Oats",
        "may_contain": []
    },

    # Dairy
    "butter": {
        "keywords": ["butter", "unsalted butter", "salted butter"],
        "allergens": ["Milk (including lactose)"],
        "sub_ingredients": "Milk, Salt",
        "may_contain": []
    },
    "milk": {
        "keywords": ["milk", "whole milk", "semi-skimmed milk", "skimmed milk"],
        "allergens": ["Milk (including lactose)"],
        "sub_ingredients": "Milk",
        "may_contain": []
    },
    "cream": {
        "keywords": ["cream", "double cream", "single cream", "whipping cream"],
        "allergens": ["Milk (including lactose)"],
        "sub_ingredients": "Milk",
        "may_contain": []
    },
    "cheese": {
        "keywords": ["cheese", "cheddar", "parmesan"],
        "allergens": ["Milk (including lactose)"],
        "sub_ingredients": "Milk, Salt, Cultures",
        "may_contain": []
    },
    "yogurt": {
        "keywords": ["yogurt", "yoghurt", "natural yogurt"],
        "allergens": ["Milk (including lactose)"],
        "sub_ingredients": "Milk, Cultures",
        "may_contain": []
    },

    # Eggs
    "eggs": {
        "keywords": ["egg", "eggs", "whole eggs", "free-range eggs"],
        "allergens": ["Eggs"],
        "sub_ingredients": "",
        "may_contain": []
    },

    # Nuts
    "almonds": {
        "keywords": ["almond", "almonds", "ground almonds", "almond flour"],
        "allergens": ["Almonds"],
        "sub_ingredients": "",
        "may_contain": ["Other tree nuts"]
    },
    "walnuts": {
        "keywords": ["walnut", "walnuts"],
        "allergens": ["Walnuts"],
        "sub_ingredients": "",
        "may_contain": ["Other tree nuts"]
    },
    "hazelnuts": {
        "keywords": ["hazelnut", "hazelnuts"],
        "allergens": ["Hazelnuts"],
        "sub_ingredients": "",
        "may_contain": ["Other tree nuts"]
    },
    "pecans": {
        "keywords": ["pecan", "pecans", "pecan nuts"],
        "allergens": ["Pecan nuts"],
        "sub_ingredients": "",
        "may_contain": ["Other tree nuts"]
    },
    "peanuts": {
        "keywords": ["peanut", "peanuts", "peanut butter"],
        "allergens": ["Peanuts"],
        "sub_ingredients": "",
        "may_contain": []
    },

    # Chocolate
    "chocolate": {
        "keywords": ["chocolate", "dark chocolate", "milk chocolate", "chocolate chips"],
        "allergens": ["Milk (including lactose)", "Soybeans (Soya)"],
        "sub_ingredients": "Cocoa Mass, Sugar, Cocoa Butter, Emulsifier (Soya Lecithin)",
        "may_contain": ["Nuts"]
    },

    # Dried fruits
    "raisins": {
        "keywords": ["raisin", "raisins", "sultanas"],
        "allergens": ["Sulphur dioxide and sulphites (at >10mg/kg or 10mg/L)"],
        "sub_ingredients": "Dried Grapes, Sunflower Oil",
        "may_contain": []
    },
    "apricots": {
        "keywords": ["apricot", "apricots", "dried apricots"],
        "allergens": ["Sulphur dioxide and sulphites (at >10mg/kg or 10mg/L)"],
        "sub_ingredients": "Dried Apricots, Preservative (Sulphur Dioxide)",
        "may_contain": []
    },

    # Seeds
    "sesame seeds": {
        "keywords": ["sesame", "sesame seeds"],
        "allergens": ["Sesame seeds"],
        "sub_ingredients": "",
        "may_contain": []
    },

    # Soya
    "soy sauce": {
        "keywords": ["soy sauce", "soya sauce"],
        "allergens": ["Soybeans (Soya)", "Wheat"],
        "sub_ingredients": "Water, Soybeans, Wheat, Salt",
        "may_contain": []
    },
}


def get_allergen_template(ingredient_name):
    """
    Get allergen template for a common ingredient
    Returns dict with allergens, sub_ingredients, may_contain or None if not found
    """
    ingredient_lower = ingredient_name.lower().strip()

    # Check each template
    for template_name, template_data in COMMON_INGREDIENT_TEMPLATES.items():
        for keyword in template_data["keywords"]:
            if keyword in ingredient_lower or ingredient_lower in keyword:
                return {
                    "allergens": template_data["allergens"],
                    "sub_ingredients": template_data["sub_ingredients"],
                    "may_contain": template_data["may_contain"]
                }

    return None


def suggest_allergen_template(ingredient_name):
    """
    Suggest an allergen template for an ingredient
    Returns a user-friendly message if a template is found
    """
    template = get_allergen_template(ingredient_name)

    if template:
        allergen_text = ", ".join(template["allergens"]) if template["allergens"] else "None"
        return f"💡 **Suggested allergens for '{ingredient_name}':** {allergen_text}"

    return None
