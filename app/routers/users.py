from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, Any

from app.db.session import get_db
from app.schema.user import PaginatedUserResponse
from app.middleware.auth import require_admin
from app.helper.users import get_users_by_role, delete_user
from app.config.route_config import USERS_ADMINS, USERS_distributors, USER_DELETE

router = APIRouter(tags=["Users"])

@router.get(USERS_ADMINS, response_model=PaginatedUserResponse)
async def get_admins(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Any = Depends(require_admin)
):
    """
    Get all users with role 'admin' with filtering, sorting, and pagination.
    Only accessible by admin users.
    """
    return await get_users_by_role(
        role_name="admin", 
        db=db, 
        search=search, 
        sort_by=sort_by, 
        sort_order=sort_order, 
        page=page, 
        limit=limit
    )

@router.get(USERS_distributors, response_model=PaginatedUserResponse)
async def get_distributors(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Any = Depends(require_admin)
):
    """
    Get all users with role 'distributor' with filtering, sorting, and pagination.
    Only accessible by admin users.
    """
    return await get_users_by_role(
        role_name="distributor", 
        db=db, 
        search=search, 
        sort_by=sort_by, 
        sort_order=sort_order, 
        page=page, 
        limit=limit
    )

@router.delete(USER_DELETE)
async def delete_user_endpoint(
    id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_admin)
):
    """
    Delete a user and all related data from both database and Supabase Auth.
    Only accessible by admin users.
    """
    return await delete_user(
        user_id=id,
        db=db
    )
