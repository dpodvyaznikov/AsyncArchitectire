from pydantic import BaseModel

class User(BaseModel):
    public_id: str
    email: str
    role: str
    is_active: bool

class TaskCreate(BaseModel):
    description: str
    status: str

class Task(TaskCreate):
    assignee: str