from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class UserProfile(BaseModel):
    name: str
    avatar: Optional[str] = None
    bio: Optional[str] = None
    department: Optional[str] = None


class UserUpdate(BaseModel):
    profile: Optional[UserProfile] = None
    role: Optional[Role] = None
