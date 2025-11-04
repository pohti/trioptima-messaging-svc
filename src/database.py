from sqlalchemy import create_engine
from .models import Base

DATABASE_URL = "sqlite:///./messages.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def init_database():
    """Initialize the database with tables"""
    try:
        create_tables()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise