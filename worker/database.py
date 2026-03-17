from sqlalchemy import Column, String, Integer, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from datetime import timezone

# Database connection URL
DATABASE_URL = "postgresql://myuser:mypassword@db:5432/pipeline_db"

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