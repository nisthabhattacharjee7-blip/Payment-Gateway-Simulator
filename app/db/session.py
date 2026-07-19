import os 
from dotenv import load_dotenv
from  sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()  # Load environment variables from .env file
