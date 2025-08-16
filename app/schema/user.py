from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid

class UserBase(BaseModel):
    name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    is_active: bool = True

class UserInDB(UserBase):
    id: Union[str, uuid.UUID]
    user_id: Union[str, uuid.UUID]
    role_id: Union[str, uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class UserResponse(UserInDB):
    role: Dict[str, Any] = None

class PaginatedUserResponse(BaseModel):
    total: int
    page: int
    limit: int
    has_next: bool
    has_previous: bool
    items: List[UserResponse]

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }
