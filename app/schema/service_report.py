from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
import uuid

class ServiceReportPartBase(BaseModel):
    machine_id: str
    quantity: int = 1

class ServiceReportPartCreate(ServiceReportPartBase):
    pass

class ServiceReportPartResponse(ServiceReportPartBase):
    id: Union[str, uuid.UUID]
    service_report_id: Union[str, uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class FileResponse(BaseModel):
    id: Union[str, uuid.UUID]
    service_report_id: Union[str, uuid.UUID]
    file_key: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ServiceReportBase(BaseModel):
    machine_id: Optional[str] = None
    sold_machines_id: Optional[str] = None
    problem: Optional[str] = None
    solution: Optional[str] = None
    service_person_name: Optional[str] = None
    service_type_id: str

class ServiceReportCreate(ServiceReportBase):
    parts: Optional[List[ServiceReportPartCreate]] = []

class ServiceReportResponse(ServiceReportBase):
    id: Union[str, uuid.UUID]
    user_id: Union[str, uuid.UUID]
    created_at: datetime
    updated_at: datetime
    parts: List[ServiceReportPartResponse] = []
    files: List[FileResponse] = []
    service_type: Optional[Dict[str, Any]] = None
    machine: Optional[Dict[str, Any]] = None
    sold_machine: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

class ServiceReportCreateResponse(BaseModel):
    success: bool
    message: str
    service_report: ServiceReportResponse

    class Config:
        orm_mode = True

class PaginatedServiceReportResponse(BaseModel):
    total: int
    page: int
    limit: int
    has_next: bool
    has_previous: bool
    items: List[ServiceReportResponse]

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }
