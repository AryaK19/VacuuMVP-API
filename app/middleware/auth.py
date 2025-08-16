from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
import os
import base64
import json
from typing import Optional, Dict, Any, List

from app.db.session import get_db
from app.db.models import User, Role
from app.config.client import get_supabase_client

security = HTTPBearer()

# Get Supabase configuration
supabase = get_supabase_client()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_ANON_KEY = os.getenv("DB_API_KEY")  # This is typically the anon key used in client

async def auth_middleware(request: Request, call_next):
    """Middleware to extract token from cookies and add to headers"""
    token = request.cookies.get("access_token")
    if token and token.startswith("Bearer "):
        token = token.split(" ")[1]  # Extract the actual token
        request.headers.__dict__["_list"].append(
            (b"authorization", f"Bearer {token}".encode())
        )
    response = await call_next(request)
    return response

def get_current_user_payload(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current user payload from Supabase JWT token"""
    try:
        token = credentials.credentials
        # Remove 'Bearer ' prefix if present
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        
        # Extract payload without verification first (to get user data)
        # This is safe because we'll verify the token with Supabase in get_current_user
        token_parts = token.split('.')
        if len(token_parts) != 3:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token format"
            )
            
        # Decode the payload (middle part of the JWT)
        payload_part = token_parts[1]
        # Add padding if needed
        padded = payload_part + '=' * (4 - len(payload_part) % 4) if len(payload_part) % 4 else payload_part
        try:
            payload = json.loads(base64.b64decode(padded).decode('utf-8'))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail=f"Invalid token payload: {str(e)}"
            )
        
        # Check for required claims
        user_id = payload.get('sub')
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token: missing subject claim"
            )
            
        # Add the original token to the payload for later use
        payload['token'] = token
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Token has expired"
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Could not validate credentials: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Authentication error: {str(e)}"
        )

async def get_current_user(
    payload: Dict[str, Any] = Depends(get_current_user_payload),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from database using Supabase token payload"""
    try:
        user_id = payload.get('sub')
        email = payload.get('email')
        token = payload.get('token')
        
        # Verify token with Supabase
        try:
            # Let Supabase verify the token
            # If the token is invalid, this will throw an exception
            user_response = supabase.auth.get_user(token)
            if not user_response or not user_response.user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: could not verify with Supabase"
                )
            
            # Check if the user IDs match
            if user_response.user.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token user ID mismatch"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )
        
        # Try to find user by Supabase user ID first, then by email
        user = db.query(User).filter(User.user_id == user_id).first()
        
        if not user and email:
            # If not found by ID, try by email (for backward compatibility)
            user = db.query(User).filter(User.email == email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in system"
            )
        
        return user
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate user: {str(e)}"
        )

def get_user_role(user: User, db: Session) -> str:
    """Get the role name for a user"""
    if not user.role_id:
        return None
        
    role = db.query(Role).filter(Role.id == user.role_id).first()
    return role.role_name if role else None

async def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """Require authentication"""
    return current_user

def require_role(*allowed_roles: str):
    """Require specific role(s)"""
    async def role_checker(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        role_name = get_user_role(current_user, db)
        
        if not role_name or role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker

# Role-specific dependencies
require_admin = require_role("admin")
require_distributer = require_role("distributer")
# Allow either role
require_any_role = require_role("admin", "distributer")


