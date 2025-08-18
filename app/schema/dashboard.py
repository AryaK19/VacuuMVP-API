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

# New Dashboard Statistics Schema
class DashboardStatsResponse(BaseModel):
    total_distributors: int
    sold_machines: int
    available_machines: int
    monthly_service_reports: int

    class Config:
        orm_mode = True

# Service Type Statistics Schema
class ServiceTypeStatsItem(BaseModel):
    service_type: str
    count: int

    class Config:
        orm_mode = True

class ServiceTypeStatsResponse(BaseModel):
    service_types: List[ServiceTypeStatsItem]

    class Config:
        orm_mode = True

# File information for service reports


# Service report parts information


# Updated schema for service report details with complete information


class PumpNumberStatsItem(BaseModel):
    part_no: Optional[str] = None
    model_no: Optional[str] = None
    service_count: int

    class Config:
        orm_mode = True

class PumpNumberStatsResponse(BaseModel):
    part_statistics: List[PumpNumberStatsItem]

    class Config:
        orm_mode = True