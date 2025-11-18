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

    Args:
        text: Recipe text (from OCR or manual input)

    Returns:
        List of dicts with 'quantity', 'unit', 'ingredient_name', 'raw_line'
    """
    ingredients = []
    lines = text.split('\n')

    # Common patterns for ingredient lines
    # Pattern 1: "200g flour" or "200 g flour"
    pattern1 = r'^[\s•\-*]*(?P<qty>[\d.]+)\s*(?P<unit>g|kg|ml|l|oz|lb|cup|cups|tbsp|tsp|tablespoon|tablespoons|teaspoon|teaspoons)[\s:]*(?P<name>.+)$'

    # Pattern 2: "2 eggs" or "3 large eggs"
    pattern2 = r'^[\s•\-*]*(?P<qty>[\d.]+)\s+(?P<name>(?:large|small|medium)?\s*[a-zA-Z\s]+)$'

    # Pattern 3: "flour - 200g" or "sugar (2 cups)"
    pattern3 = r'^[\s•\-*]*(?P<name>[a-zA-Z\s]+?)[\s\-\(]+(?P<qty>[\d.]+)\s*(?P<unit>g|kg|ml|l|oz|lb|cup|cups|tbsp|tsp)?'

    # Pattern 4: Just ingredient name with no quantity (user will enter manually)
    pattern4 = r'^[\s•\-*]*(?P<name>[a-zA-Z][a-zA-Z\s]+)$'

    for line in lines:
        line = line.strip()

        # Skip empty lines and common headers
        if not line or len(line) < 3:
            continue
        if re.match(r'^(ingredients?|directions?|instructions?|method|steps?):?$', line, re.IGNORECASE):
            continue

        # Try each pattern in order
        match = re.match(pattern1, line, re.IGNORECASE)
        if match:
            ingredients.append({
                'quantity': float(match.group('qty')),
                'unit': match.group('unit').lower(),
                'ingredient_name': match.group('name').strip(),
                'raw_line': line
            })
            continue

        match = re.match(pattern2, line, re.IGNORECASE)
        if match:
            ingredients.append({
                'quantity': float(match.group('qty')),
                'unit': 'units',
                'ingredient_name': match.group('name').strip(),
                'raw_line': line
            })
            continue

        match = re.match(pattern3, line, re.IGNORECASE)
        if match:
            unit = match.group('unit') if match.group('unit') else 'units'
            ingredients.append({
                'quantity': float(match.group('qty')),
                'unit': unit.lower(),
                'ingredient_name': match.group('name').strip(),
                'raw_line': line
            })
            continue

        match = re.match(pattern4, line, re.IGNORECASE)
        if match and len(match.group('name').strip()) > 2:
            # Ingredient name only, no quantity
            ingredients.append({
                'quantity': None,
                'unit': None,
                'ingredient_name': match.group('name').strip(),
                'raw_line': line
            })

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
