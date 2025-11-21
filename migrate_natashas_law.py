"""
Migration script to add Natasha's Law compliance fields to the database.
Run this once to update existing database.
"""

from database import engine
from sqlalchemy import text

def migrate():
    """Add allergen and label fields to ingredients and recipes tables"""

    with engine.connect() as conn:
        print("🔄 Starting Natasha's Law database migration...")

        # Add columns to ingredients table
        try:
            conn.execute(text("ALTER TABLE ingredients ADD COLUMN allergens TEXT"))
            print("✅ Added 'allergens' column to ingredients")
        except Exception as e:
            print(f"⚠️  'allergens' column may already exist: {e}")

        try:
            conn.execute(text("ALTER TABLE ingredients ADD COLUMN sub_ingredients TEXT"))
            print("✅ Added 'sub_ingredients' column to ingredients")
        except Exception as e:
            print(f"⚠️  'sub_ingredients' column may already exist: {e}")

        try:
            conn.execute(text("ALTER TABLE ingredients ADD COLUMN may_contain TEXT"))
            print("✅ Added 'may_contain' column to ingredients")
        except Exception as e:
            print(f"⚠️  'may_contain' column may already exist: {e}")

        # Add columns to recipes table
        try:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN storage_instructions TEXT"))
            print("✅ Added 'storage_instructions' column to recipes")
        except Exception as e:
            print(f"⚠️  'storage_instructions' column may already exist: {e}")

        try:
            conn.execute(text("ALTER TABLE recipes ADD COLUMN use_by_days INTEGER"))
            print("✅ Added 'use_by_days' column to recipes")
        except Exception as e:
            print(f"⚠️  'use_by_days' column may already exist: {e}")

        conn.commit()
        print("✅ Migration complete!")

if __name__ == "__main__":
    migrate()
