"""
Product lookup using Open Food Facts API
Fetches product information including allergens from barcodes
"""

import requests
import json

def lookup_product_by_barcode(barcode):
    """
    Look up a product by barcode using multiple databases

    Tries:
    1. UK Open Food Facts database first
    2. World Open Food Facts database
    3. Other sources if needed

    Args:
        barcode: Product barcode number

    Returns:
        dict with product info or None if not found
    """
    try:
        # Try UK-specific database first (better for UK products)
        urls_to_try = [
            f"https://uk.openfoodfacts.org/api/v2/product/{barcode}.json",  # UK first
            f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json",  # Then worldwide
        ]

        product_data = None
        for url in urls_to_try:
            try:
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    if data.get('status') == 1:  # Product found
                        product = data.get('product', {})

                        # Extract relevant information
                        product_info = {
                            'found': True,
                            'name': product.get('product_name', ''),
                            'brand': product.get('brands', ''),
                            'ingredients_text': product.get('ingredients_text', ''),
                            'allergens': extract_allergens(product),
                            'allergens_tags': product.get('allergens_tags', []),
                            'traces': extract_traces(product),
                            'image_url': product.get('image_url', ''),
                            'barcode': barcode,
                            'source': 'UK database' if 'uk.openfoodfacts' in url else 'World database'
                        }

                        return product_info
            except requests.exceptions.RequestException:
                # Try next URL
                continue

        # If we get here, product not found in any database
        return {'found': False, 'barcode': barcode}

    except requests.exceptions.RequestException as e:
        print(f"Error fetching product: {e}")
        return {'found': False, 'error': str(e), 'barcode': barcode}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {'found': False, 'error': str(e), 'barcode': barcode}


def extract_allergens(product):
    """
    Extract allergen information from product data

    Returns list of allergen names
    """
    allergens = []

    # Get allergens from tags
    allergen_tags = product.get('allergens_tags', [])
    for tag in allergen_tags:
        # Tags are like "en:gluten", "en:milk", etc.
        allergen_name = tag.replace('en:', '').replace('-', ' ').title()
        allergens.append(allergen_name)

    # Also check allergens_hierarchy
    allergen_hierarchy = product.get('allergens_hierarchy', [])
    for allergen in allergen_hierarchy:
        allergen_name = allergen.replace('en:', '').replace('-', ' ').title()
        if allergen_name not in allergens:
            allergens.append(allergen_name)

    return allergens


def extract_traces(product):
    """
    Extract trace allergen information (may contain)

    Returns list of trace allergen names
    """
    traces = []

    # Get traces from tags
    traces_tags = product.get('traces_tags', [])
    for tag in traces_tags:
        trace_name = tag.replace('en:', '').replace('-', ' ').title()
        traces.append(trace_name)

    return traces


def map_to_natasha_allergens(openfoodfacts_allergens):
    """
    Map Open Food Facts allergen names to Natasha's Law allergen categories

    Returns list of standardized allergen names
    """
    # Mapping from Open Food Facts terms to Natasha's Law categories
    allergen_mapping = {
        'gluten': 'Wheat',
        'wheat': 'Wheat',
        'cereals containing gluten': 'Wheat',
        'crustaceans': 'Crustaceans',
        'eggs': 'Eggs',
        'egg': 'Eggs',
        'fish': 'Fish',
        'peanuts': 'Peanuts',
        'peanut': 'Peanuts',
        'soybeans': 'Soybeans (Soya)',
        'soya': 'Soybeans (Soya)',
        'soy': 'Soybeans (Soya)',
        'milk': 'Milk (including lactose)',
        'lactose': 'Milk (including lactose)',
        'nuts': 'Tree Nuts',
        'tree nuts': 'Tree Nuts',
        'almonds': 'Almonds',
        'hazelnuts': 'Hazelnuts',
        'walnuts': 'Walnuts',
        'cashews': 'Cashew nuts',
        'pecan nuts': 'Pecan nuts',
        'brazil nuts': 'Brazil nuts',
        'pistachio nuts': 'Pistachio nuts',
        'macadamia nuts': 'Macadamia nuts',
        'celery': 'Celery',
        'mustard': 'Mustard',
        'sesame': 'Sesame seeds',
        'sesame seeds': 'Sesame seeds',
        'sulphur dioxide': 'Sulphur dioxide and sulphites (at >10mg/kg or 10mg/L)',
        'sulphites': 'Sulphur dioxide and sulphites (at >10mg/kg or 10mg/L)',
        'sulfites': 'Sulphur dioxide and sulphites (at >10mg/kg or 10mg/L)',
        'lupin': 'Lupin',
        'molluscs': 'Molluscs',
        'mollusks': 'Molluscs'
    }

    mapped_allergens = []
    for allergen in openfoodfacts_allergens:
        allergen_lower = allergen.lower()
        if allergen_lower in allergen_mapping:
            mapped = allergen_mapping[allergen_lower]
            if mapped not in mapped_allergens:
                mapped_allergens.append(mapped)
        else:
            # Keep original if no mapping found
            if allergen not in mapped_allergens:
                mapped_allergens.append(allergen)

    return mapped_allergens
