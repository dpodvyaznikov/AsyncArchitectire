from email.policy import default
from enum import unique
from uuid import uuid4
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .db import Base

def generate_public_id():
    return str(uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String, unique=True, default=generate_public_id)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default='user')
    is_active = Column(Boolean, default=True)
