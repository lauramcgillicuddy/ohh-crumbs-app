"""
Migration script for Epic Bakery Features
Adds: WastageLog, IngredientBatch, ProductionPlan, EquipmentLog, UserRole tables
Also adds expected_cost and actual_cost to ProductionBatch
"""

from database import engine
from models import Base
from sqlalchemy import text

def migrate():
    print("🚀 Starting Epic Features Migration...")

    # Create all new tables
    Base.metadata.create_all(engine)

    print("✅ Migration complete!")
    print("   - Added WastageLog table")
    print("   - Added IngredientBatch table")
    print("   - Added ProductionPlan table")
    print("   - Added EquipmentLog table")
    print("   - Added UserRole table")
    print("   - Updated ProductionBatch with cost tracking")
    print()
    print("🎉 All tables created successfully!")

if __name__ == "__main__":
    migrate()
