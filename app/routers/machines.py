from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, Any

from app.db.session import get_db
from app.schema.machine import PaginatedMachineResponse
from app.middleware.auth import require_admin
from app.helper.machines import get_machines_by_type

from app.config.route_config import MACHINES_PUMPS, MACHINES_PARTS

router = APIRouter(tags=["Machines"])

@router.get(MACHINES_PUMPS, response_model=PaginatedMachineResponse)
async def get_pumps(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Any = Depends(require_admin)
):
    """
    Get all machines with type 'pump' with filtering, sorting, and pagination.
    Only accessible by admin users.
    """
    return await get_machines_by_type(
        type_name="pump", 
        db=db, 
        search=search, 
        sort_by=sort_by, 
        sort_order=sort_order, 
        page=page, 
        limit=limit
    )

@router.get(MACHINES_PARTS, response_model=PaginatedMachineResponse)
async def get_parts(
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("created_at", description="Field to sort by"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc or desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user : Any = Depends(require_admin)
):
    """
    Get all machines with type 'part' with filtering, sorting, and pagination.
    Only accessible by admin users.
    """
    return await get_machines_by_type(
        type_name="part", 
        db=db, 
        search=search, 
        sort_by=sort_by, 
        sort_order=sort_order, 
        page=page, 
        limit=limit
    )

