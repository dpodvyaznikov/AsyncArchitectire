import email
from pydantic import BaseModel

class User(BaseModel):
    email: str
    public_id: str
    role: str
    is_active: bool

class TaskCreate(BaseModel):
    title: str
    jira_id: str
    description: str
    status: str
