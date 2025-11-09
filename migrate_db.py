import os
from sqlalchemy import create_engine, text, inspect
from database import get_database_url

def migrate_database():
    database_url = get_database_url()
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        return False
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        existing_tables = inspector.get_table_names()
        
        if 'ingredients' in existing_tables:
            columns = [col['name'] for col in inspector.get_columns('ingredients')]
            
            if 'supplier_id' not in columns:
                print("Adding supplier_id column to ingredients table...")
                conn.execute(text("ALTER TABLE ingredients ADD COLUMN supplier_id INTEGER"))
                conn.execute(text("ALTER TABLE ingredients ADD FOREIGN KEY (supplier_id) REFERENCES suppliers(id)"))
                conn.commit()
                print("✓ Added supplier_id column")
            else:
                print("✓ supplier_id column already exists")
        
        print("Database migration completed successfully!")
    
    return True

if __name__ == "__main__":
    migrate_database()
