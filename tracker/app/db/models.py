import email
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
    email = Column(String, unique=True)
    public_id = Column(String, unique=True)
    role = Column(String)
    is_active = Column(Boolean)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String, generate_public_id)
    title = Column(String)
    description =  Column(String)
    jira_id = Column(String)
    status =  Column(String, default='WIP')
    assignee = Column(String, ForeignKey("users.public_id"))
