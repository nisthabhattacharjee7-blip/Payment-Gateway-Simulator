import uuid 
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeinKey, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
