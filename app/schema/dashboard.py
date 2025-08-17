from pydantic import BaseModel
from typing import List, Optional, Union
from datetime import datetime, date
import uuid

class RecentActivityBase(BaseModel):
    user_name: str
    service_type_name: str
    created_at: datetime
    report_id: Union[str, uuid.UUID]

class RecentActivityResponse(RecentActivityBase):
    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }

class PaginatedRecentActivitiesResponse(BaseModel):
    total: int
    page: int
    limit: int
    has_next: bool
    has_previous: bool
    items: List[RecentActivityResponse]

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }

# New schema for service report details
class ServiceReportDetailResponse(BaseModel):
    id: Union[str, uuid.UUID]
    user_name: str
    user_email: str
    service_type_name: str
    machine_serial_no: Optional[str] = None
    machine_model_no: Optional[str] = None
    problem: Optional[str] = None
    solution: Optional[str] = None
    service_person_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }