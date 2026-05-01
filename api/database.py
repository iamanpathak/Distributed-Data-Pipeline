from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from datetime import timezone
import os

# Fetch credentials from .env, with fallbacks just in case
DB_USER = os.getenv("POSTGRES_USER", "myuser")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "mypassword")
DB_NAME = os.getenv("POSTGRES_DB", "pipeline_db")

# Database connection URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@db:5432/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# This is the Table structure
class JobRecord(Base):
    __tablename__ = "jobs"
    
    job_id = Column(String, primary_key=True, index=True)
    status = Column(String)
    data_size = Column(Integer)
    result_data = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(timezone.utc))

# Helper to create tables
def init_db():
    Base.metadata.create_all(bind=engine)