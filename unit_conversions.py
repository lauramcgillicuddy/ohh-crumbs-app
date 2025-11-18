"""
Unit conversion utilities for ingredient measurements
"""

# Common baking conversions (approximate)
CONVERSION_TABLE = {
    # Weight conversions (to grams)
    'g': 1.0,
    'kg': 1000.0,
    'oz': 28.35,
    'lb': 453.59,

    # Volume conversions (to mL)
    'mL': 1.0,
    'L': 1000.0,
    'cups': 236.59,
    'tbsp': 14.79,
    'tsp': 4.93,
}

def convert_to_base_unit(quantity: float, from_unit: str) -> tuple:
    """
    Convert quantity to base unit (g for weight, mL for volume)
    Returns (converted_quantity, base_unit)
    """
    from_unit_lower = from_unit.lower()

    # Weight units -> grams
    if from_unit_lower in ['g', 'kg', 'oz', 'lb']:
        base_unit = 'g'
        factor = CONVERSION_TABLE.get(from_unit_lower, 1.0)
        return (quantity * factor, base_unit)

    # Volume units -> mL
    elif from_unit_lower in ['ml', 'l', 'cups', 'tbsp', 'tsp']:
        base_unit = 'mL'
        factor = CONVERSION_TABLE.get(from_unit_lower, 1.0)
        return (quantity * factor, base_unit)

    # Unknown unit - return as is
    else:
        return (quantity, from_unit)


def convert_units(quantity: float, from_unit: str, to_unit: str) -> float:
    """
    Convert quantity from one unit to another
    Example: convert_units(1, 'kg', 'g') -> 1000
    """
    # Convert to base unit first
    base_quantity, base_unit = convert_to_base_unit(quantity, from_unit)

    # Convert from base unit to target unit
    to_unit_lower = to_unit.lower()

    # If target unit is in the same category
    if to_unit_lower in CONVERSION_TABLE:
        factor = CONVERSION_TABLE[to_unit_lower]
        return base_quantity / factor

    # Can't convert - return original
    return quantity


def get_conversion_hint(from_unit: str, to_unit: str) -> str:
    """
    Get a helpful conversion hint for users
    """
    conversions = {
        ('kg', 'g'): '1 kg = 1000 g',
        ('g', 'kg'): '1000 g = 1 kg',
        ('lb', 'oz'): '1 lb = 16 oz',
        ('oz', 'g'): '1 oz ≈ 28.35 g',
        ('L', 'mL'): '1 L = 1000 mL',
        ('cups', 'mL'): '1 cup ≈ 237 mL',
        ('tbsp', 'mL'): '1 tbsp ≈ 15 mL',
        ('tsp', 'mL'): '1 tsp ≈ 5 mL',
    }

    key = (from_unit.lower(), to_unit.lower())
    return conversions.get(key, f"No conversion available for {from_unit} to {to_unit}")


# Quick reference for common baking measurements
BAKING_CONVERSIONS = """
### Common Baking Conversions

**Weight:**
- 1 kg = 1000 g
- 1 lb = 16 oz = 453.59 g
- 1 oz = 28.35 g

**Volume:**
- 1 L = 1000 mL
- 1 cup = 237 mL
- 1 tbsp = 15 mL
- 1 tsp = 5 mL

**Butter (approximate):**
- 1 cup butter = 227 g
- 1 tbsp butter = 14 g
- 1 stick butter = 113 g

**Flour (approximate):**
- 1 cup all-purpose flour = 120-125 g
- 1 tbsp flour = 8 g

**Sugar (approximate):**
- 1 cup granulated sugar = 200 g
- 1 cup brown sugar (packed) = 220 g
- 1 tbsp sugar = 12.5 g
"""
