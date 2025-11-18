"""
Recipe OCR Parser - Extract ingredients from recipe images
"""

import re
from typing import Dict, List, Optional, Tuple
from receipt_parser import extract_text_from_image


def parse_recipe_ingredients(text: str) -> List[Dict[str, any]]:
    """
    Parse ingredients from recipe text.

    Handles various formats:
    - "200g flour"
    - "2 cups sugar"
    - "1 tsp vanilla extract"
    - "500 ml milk"
    - "3 eggs"
    - "Baking Spread 8oz"

    Args:
        text: Recipe text (from OCR or manual input)

    Returns:
        List of dicts with 'quantity', 'unit', 'ingredient_name', 'raw_line'
    """
    ingredients = []
    lines = text.split('\n')

    # Keywords that indicate this is NOT an ingredient line
    skip_keywords = [
        'preheat', 'oven', 'bake', 'cook', 'mix', 'stir', 'beat', 'whisk',
        'fold', 'combine', 'pour', 'line', 'grease', 'tin', 'pan', 'bowl',
        'recipe', 'method', 'instructions', 'directions', 'steps', 'serves',
        'temperature', 'minutes', 'hours', 'degrees', 'fan', 'gas mark',
        'prep time', 'cook time', 'total time', 'yield', 'servings'
    ]

    # Track if we're in the ingredients section
    in_ingredients_section = False

    # Common patterns for ingredient lines
    # Pattern 1: "Ingredient Name 8oz" or "Ingredient Name 200g"
    pattern1 = r'^[\s•\-*]*(?P<name>[A-Za-z][A-Za-z\s]+?)\s+(?P<qty>[\d.]+)\s*(?P<unit>g|kg|ml|l|oz|lb|cup|cups|tbsp|tsp|tablespoon|tablespoons|teaspoon|teaspoons)?\s*$'

    # Pattern 2: "200g flour" or "200 g flour"
    pattern2 = r'^[\s•\-*]*(?P<qty>[\d.]+)\s*(?P<unit>g|kg|ml|l|oz|lb|cup|cups|tbsp|tsp|tablespoon|tablespoons|teaspoon|teaspoons)[\s:]+(?P<name>.+)$'

    # Pattern 3: "2 eggs" or "3 large eggs" or "4 Large Eggs"
    pattern3 = r'^[\s•\-*]*(?P<qty>[\d.]+)\s+(?P<name>(?:large|small|medium)?\s*[a-zA-Z\s]+)$'

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line or len(line) < 3:
            continue

        line_lower = line.lower()

        # Check if we're entering ingredients section
        if re.match(r'^(ingredients?|ingrtedients?):?$', line, re.IGNORECASE):
            in_ingredients_section = True
            continue

        # Check if we're leaving ingredients section (method/directions start)
        if re.match(r'^(method|directions?|instructions?|steps?|icing):?$', line, re.IGNORECASE):
            in_ingredients_section = False
            continue

        # Skip lines with instruction keywords
        if any(keyword in line_lower for keyword in skip_keywords):
            continue

        # Skip lines that are mostly uppercase and don't have numbers (likely titles)
        if line.isupper() and not re.search(r'\d', line):
            continue

        # Skip lines that end with temperature indicators
        if re.search(r'(°|degrees?|fan|gas)\s*\d*\s*$', line_lower):
            continue

        # Try Pattern 1: "Ingredient Name 8oz" (most common in UK recipes)
        match = re.match(pattern1, line, re.IGNORECASE)
        if match:
            name = match.group('name').strip()
            # Make sure the name doesn't contain mostly numbers
            if len(re.findall(r'[a-zA-Z]', name)) >= 3:
                unit = match.group('unit').lower() if match.group('unit') else 'units'
                ingredients.append({
                    'quantity': float(match.group('qty')),
                    'unit': unit,
                    'ingredient_name': name,
                    'raw_line': line
                })
                continue

        # Try Pattern 2: "200g flour"
        match = re.match(pattern2, line, re.IGNORECASE)
        if match:
            name = match.group('name').strip()
            if len(re.findall(r'[a-zA-Z]', name)) >= 3:
                ingredients.append({
                    'quantity': float(match.group('qty')),
                    'unit': match.group('unit').lower(),
                    'ingredient_name': name,
                    'raw_line': line
                })
                continue

        # Try Pattern 3: "4 Large Eggs"
        match = re.match(pattern3, line, re.IGNORECASE)
        if match:
            name = match.group('name').strip()
            # Ensure it's not a number-heavy line and has actual letters
            if len(re.findall(r'[a-zA-Z]', name)) >= 3 and len(name.split()) <= 5:
                ingredients.append({
                    'quantity': float(match.group('qty')),
                    'unit': 'units',
                    'ingredient_name': name,
                    'raw_line': line
                })
                continue

    return ingredients


def fuzzy_match_ingredient(ingredient_name: str, db_ingredients: List, threshold: float = 0.6) -> List[Tuple[any, float]]:
    """
    Fuzzy match a recipe ingredient name against database ingredients.

    Args:
        ingredient_name: Ingredient name from recipe (e.g., "flour", "yeast")
        db_ingredients: List of Ingredient objects from database
        threshold: Minimum similarity score (0-1)

    Returns:
        List of (ingredient_object, score) tuples, sorted by score descending
    """
    from difflib import SequenceMatcher

    matches = []
    ingredient_name_lower = ingredient_name.lower().strip()

    for db_ing in db_ingredients:
        db_name_lower = db_ing.name.lower().strip()

        # Exact match
        if ingredient_name_lower == db_name_lower:
            matches.append((db_ing, 1.0))
            continue

        # Contains match (e.g., "flour" in "Plain Flour")
        if ingredient_name_lower in db_name_lower or db_name_lower in ingredient_name_lower:
            matches.append((db_ing, 0.9))
            continue

        # Fuzzy match using SequenceMatcher
        similarity = SequenceMatcher(None, ingredient_name_lower, db_name_lower).ratio()

        if similarity >= threshold:
            matches.append((db_ing, similarity))

    # Sort by score descending
    matches.sort(key=lambda x: x[1], reverse=True)

    return matches


def parse_recipe_from_image(image_bytes: bytes, db_ingredients: List) -> Dict:
    """
    Complete pipeline: Extract text from image, parse ingredients, match to database.

    Args:
        image_bytes: Recipe image bytes
        db_ingredients: List of Ingredient objects from database

    Returns:
        Dict with 'text', 'parsed_ingredients', 'matched_ingredients'
    """
    # Step 1: Extract text using existing OCR function
    text = extract_text_from_image(image_bytes, filename="recipe.jpg")

    # Step 2: Parse ingredients from text
    parsed_ingredients = parse_recipe_ingredients(text)

    # Step 3: Match each ingredient to database
    matched_ingredients = []

    for parsed in parsed_ingredients:
        matches = fuzzy_match_ingredient(parsed['ingredient_name'], db_ingredients)

        matched_ingredients.append({
            'parsed': parsed,
            'matches': matches,  # List of (ingredient_obj, score) tuples
            'top_match': matches[0] if matches else None,
            'has_multiple_matches': len(matches) > 1
        })

    return {
        'raw_text': text,
        'parsed_ingredients': parsed_ingredients,
        'matched_ingredients': matched_ingredients
    }
