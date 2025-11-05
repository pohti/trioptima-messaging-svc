import os
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from .models import Base

# allow env vars for database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./messages.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    try:
        create_tables()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise