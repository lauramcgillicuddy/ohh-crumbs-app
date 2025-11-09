import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base
import streamlit as st

def get_database_url():
    return os.getenv('DATABASE_URL')

@st.cache_resource
def get_engine():
    database_url = get_database_url()
    if not database_url:
        st.error("⚠️ DATABASE_URL environment variable is not set. Please configure your database connection.")
        st.stop()
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False
        )
        return engine
    except Exception as e:
        st.error(f"Failed to connect to database: {str(e)}")
        st.stop()

def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    from sqlalchemy import text, inspect
    
    inspector = inspect(engine)
    
    with engine.connect() as conn:
        existing_tables = inspector.get_table_names()
        
        if 'ingredients' in existing_tables:
            columns = [col['name'] for col in inspector.get_columns('ingredients')]
            
            if 'supplier_id' not in columns:
                try:
                    conn.execute(text("ALTER TABLE ingredients ADD COLUMN supplier_id INTEGER REFERENCES suppliers(id)"))
                    conn.commit()
                except Exception:
                    pass

def get_session():
    engine = get_engine()
    Session = scoped_session(sessionmaker(bind=engine))
    return Session()

def close_session(session):
    if session:
        session.close()
