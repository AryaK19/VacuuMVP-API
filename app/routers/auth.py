from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid
import os
from typing import Dict, Any
import traceback
from app.middleware.auth import require_admin
from app.db.session import get_db
from app.db import models
from app.schema.auth import UserCreate, UserResponse, LoginRequest, PasswordResetRequest
from app.services.auth import get_password_hash, pwd_context
from app.config.route_config import AUTH_LOGIN, AUTH_REGISTER, AUTH_LOGOUT, AUTH_FORGOT_PASSWORD
from app.config.client import get_supabase_client

router = APIRouter(tags=["Authentication"])
supabase = get_supabase_client()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=AUTH_LOGIN.lstrip('/'))

@router.post(AUTH_REGISTER, response_model=Dict[str, Any])
async def register(user_data: UserCreate, db: Session = Depends(get_db), current_user : Any = Depends(require_admin)):
    """
    Register a new user with Supabase Auth
    """
    try:
        # Check if user with the same email already exists in our database
        existing_user = db.query(models.User).filter(
            models.User.email == user_data.email
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Email already registered"
            )
        
        # First, register with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if auth_response.user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed with Supabase Auth"
            )
        
        # Find role_id for the given role name
        role = db.query(models.Role).filter(
            models.Role.role_name == user_data.role
        ).first()

        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{user_data.role}' not found"
            )

        # Create new user in our database
        new_user = models.User(
            id=str(uuid.uuid4()),
            user_id=auth_response.user.id,
            email=user_data.email,
            password=get_password_hash(user_data.password),
            name=user_data.name,
            phone_number=user_data.phone_number,
            role_id=role.id  # Assign the role_id
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "message": "Registration successful",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "name": new_user.name,
                "role": user_data.role
            }
        }
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please try again."
        )
    except Exception as e:
        db.rollback()
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post(AUTH_LOGIN, response_model=Dict[str, Any])
async def login(request: Request, db: Session = Depends(get_db)):
    """Login user with Supabase Auth"""
    try:
        # Get the raw request body to handle possible nested structure
        body = await request.json()
        
        # Handle potentially nested email field
        email = None
        password = None
        
        if isinstance(body.get('email'), dict):
            # Handle nested structure: {"email": {"email": "user@example.com", "password": "pass"}}
            nested = body.get('email', {})
            email = nested.get('email')
            password = nested.get('password')
        else:
            # Handle flat structure: {"email": "user@example.com", "password": "pass"}
            email = body.get('email')
            password = body.get('password')
        
        # Validate required fields
        if not email or not password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required"
            )
        
        # Sign in with Supabase
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if auth_response.user is None or auth_response.session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Get user from our database
        user = db.query(models.User).filter(
            (models.User.user_id == auth_response.user.id) | (models.User.email == email)
        ).first()
        
        if not user:
            # If user doesn't exist in our DB but exists in Supabase, create them
            hashed_password = pwd_context.hash(password)
            user = models.User(
                id=str(uuid.uuid4()),
                user_id=auth_response.user.id,
                email=email,
                password=hashed_password,
                # Default values for new required fields
                name=None,
                phone_number=None
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return {
            "success": True,
            "message": "Login successful",
            "user": {
                "id": str(auth_response.user.id),
                "email": auth_response.user.email,
                "name": user.name
            },
            "session": {
                "access_token": auth_response.session.access_token,
                "refresh_token": auth_response.session.refresh_token,
                "expires_at": auth_response.session.expires_at,
                "token_type": "bearer"
            }
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}"
        )

@router.post(AUTH_LOGOUT, response_model=Dict[str, Any])
async def logout():
    """Logout user from Supabase Auth"""
    try:
        supabase.auth.sign_out()
        return {
            "success": True,
            "message": "Logout successful"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Logout failed: {str(e)}"
        )

@router.post(AUTH_FORGOT_PASSWORD, response_model=Dict[str, Any])
async def forgot_password(request: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request a password reset email"""
    try:
        # Check if user exists in our database first
        user = db.query(models.User).filter(models.User.email == request.email).first()
        if not user:
            # Return success even if user doesn't exist to avoid email enumeration
            return {
                "success": True,
                "message": "If your email is registered, you will receive a password reset link."
            }
        
        # Construct redirect URL from environment variable without including the email
        frontend_url = os.getenv("FRONTEND_API", "http://localhost:3000")
        redirect_to = f"{frontend_url}/reset-password"
        
        # Send password reset email via Supabase with redirect URL
        supabase.auth.reset_password_for_email(
            request.email,
            {
                "redirect_to": redirect_to,
            }
        )
        
        # Return success message
        return {
            "success": True,
            "message": "If your email is registered, you will receive a password reset link."
        }
        
    except Exception as e:
        # Always return success to prevent email enumeration
        return {
            "success": True,
            "message": "If your email is registered, you will receive a password reset link."
        }
