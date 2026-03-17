from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class Role(str, Enum):
    admin = "admin"
    manager = "manager"
    employee = "employee"

class User(BaseModel):
    name:str
    email:EmailStr
    password: str = Field(
         min_length=6,
         max_length=72
    )
    role: Role = Role.employee
    
class RefreshRequest(BaseModel):
    refresh_token: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
   
   
