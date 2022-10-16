from email.policy import default
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .db import Base


class Transaction(Base):
    __tablename__ = "log"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String, unique=True)
    transaction = Column(Integer)
    comment = Column(String)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String, unique=True)
    role = Column(String, default='user')
    is_active = Column(Boolean)
    balance = Column(Integer, default=0)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(String, unique=True)
    title = Column(String)
    assignee = Column(String)
    cost = Column(Integer)
    reward = Column(Integer)
