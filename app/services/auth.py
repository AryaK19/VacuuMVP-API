from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.db import models
from app.schema.auth import TokenData
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.session import get_db
from dotenv import load_dotenv
from app.config.client import get_supabase_client

load_dotenv()

# Security configuration
JWT_SECRET_KEY = os.getenv("DB_JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
supabase = get_supabase_client()
security = HTTPBearer()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate a user with Supabase Auth
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user is None or response.session is None:
            return None
        
        user = db.query(models.User).filter(models.User.email == email).first()
        
        # If user doesn't exist in our database but exists in Supabase Auth
        if not user:
            return None
        
        return user
    except Exception:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security), db: Session = Depends(get_db)):
    """
    Validate Supabase JWT token and get the current user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Get the token
        token = credentials.credentials
        
        # Validate with Supabase
        supabase_response = supabase.auth.get_user(token)
        user_id = supabase_response.user.id
        
        # Get user from database
        user = db.query(models.User).filter(models.User.user_id == user_id).first()
        
        if user is None:
            raise credentials_exception
            
        return user
    except Exception:
        raise credentials_exception

async def get_current_active_user(user: models.User = Depends(get_current_user)):
    """
    Check if the user is active
    """
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
