from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    The base class that every SQLAlchemy model in this project will inherit from.
    SQLAlchemy uses this class to keep track of all tables and their structures.
    """
    pass