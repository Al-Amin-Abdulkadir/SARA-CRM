from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from app.config.settings import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
