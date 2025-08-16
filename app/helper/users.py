from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import Optional, Dict, Any

from app.db import models

async def get_users_by_role(
    role_name: str,
    db: Session,
    search: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Helper function to get users by role with filtering, sorting, and pagination
    """
    # Get the role_id for the given role_name
    role_obj = db.query(models.Role).filter(models.Role.role_name == role_name).first()
    if not role_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )

    # Start building the query
    query = db.query(models.User).join(models.Role).filter(
        models.User.role_id == role_obj.id
    )

    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.User.name.ilike(search_term)) |
            (models.User.email.ilike(search_term)) |
            (models.User.phone_number.ilike(search_term))
        )

    # Count total items for pagination
    total_items = query.count()

    # Apply sorting
    if hasattr(models.User, sort_by):
        sort_column = getattr(models.User, sort_by)
        if sort_order.lower() == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
    else:
        # Default sort by created_at desc if sort field is invalid
        query = query.order_by(desc(models.User.created_at))

    # Apply pagination
    query = query.offset((page - 1) * limit).limit(limit)

    # Execute query and fetch results
    users = query.all()

    # Calculate pagination metadata
    has_next = (page * limit) < total_items
    has_previous = page > 1

    # Prepare response with role info
    result_users = []
    for user in users:
        # Convert UUID objects to strings to avoid validation errors
        user_dict = {
            "id": str(user.id),
            "user_id": str(user.user_id),
            "role_id": str(user.role_id),
            "name": user.name,
            "email": user.email,
            "phone_number": user.phone_number,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "role": {
                "id": str(user.role.id),
                "role_name": user.role.role_name
            }
        }
        result_users.append(user_dict)

    return {
        "total": total_items,
        "page": page,
        "limit": limit,
        "has_next": has_next,
        "has_previous": has_previous,
        "items": result_users
    }
