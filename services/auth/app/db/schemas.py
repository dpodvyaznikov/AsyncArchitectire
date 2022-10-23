from typing import List, Optional, Union

from pydantic import BaseModel

class UserBase(BaseModel):
    email: str
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    public_id: str
    is_active: int

    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    public_id: Optional[str] = None
    is_active: Optional[int] = None

    class Config:
        orm_mode = True
