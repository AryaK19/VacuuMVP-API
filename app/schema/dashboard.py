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
class ServiceReportFileInfo(BaseModel):
    id: Union[str, uuid.UUID]
    file_key: str
    file_url: str
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }

# Service report parts information
class ServiceReportPartInfo(BaseModel):
    id: Union[str, uuid.UUID]
    machine_serial_no: Optional[str] = None
    machine_model_no: Optional[str] = None
    machine_part_no: Optional[str] = None
    quantity: int
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }

# Machine information for service reports
class ServiceReportMachineInfo(BaseModel):
    serial_no: Optional[str] = None
    model_no: Optional[str] = None
    part_no: Optional[str] = None
    type_name: Optional[str] = None
    date_of_manufacturing: Optional[date] = None

    class Config:
        orm_mode = True

# Customer information from sold machines
class ServiceReportCustomerInfo(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_address: Optional[str] = None
    sold_date: Optional[datetime] = None

    class Config:
        orm_mode = True

# Updated schema for service report details with complete information
class ServiceReportDetailResponse(BaseModel):
    id: Union[str, uuid.UUID]
    user_name: str
    user_email: str
    service_type_name: str
    machine_info: Optional[ServiceReportMachineInfo] = None
    customer_info: Optional[ServiceReportCustomerInfo] = None
    problem: Optional[str] = None
    solution: Optional[str] = None
    service_person_name: Optional[str] = None
    files: List[ServiceReportFileInfo] = []
    parts: List[ServiceReportPartInfo] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }