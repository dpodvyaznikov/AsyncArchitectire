from pydantic import BaseModel

class User(BaseModel):
    public_id: str
    role: str
    is_active: bool

class Task(BaseModel):
    public_id: str
    title: str
    status: str
    assignee: str