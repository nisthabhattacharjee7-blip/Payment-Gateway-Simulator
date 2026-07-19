import os 
from dotenv import load_dotenv
from  sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()  # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency that provides a database session to route functions.
    Ensures the session is closed after the request finishes, 
    even if an error occurs during the request processing.
    """
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()    
        