from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, Dict, Any, Literal
import re

class UserBase(BaseModel):
    email: EmailStr
    

class UserCreate(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    role: Literal["admin", "distributer"] = "distributer"  # Default to distributer
    password: str
    confirm_password: str
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 4:
            raise ValueError('Password must be at least 4 characters long')
        # You can add more password strength rules here
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v
    

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str
    
class TokenData(BaseModel):
    sub: Optional[str] = None
    
class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: bool
    
    class Config:
        orm_mode = True

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Dict[str, Any]
    session: Dict[str, Any]
    
    class Config:
        orm_mode = True
