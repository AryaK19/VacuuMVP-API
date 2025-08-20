from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
import uuid

class MachineBase(BaseModel):
    model_no: str
    part_no: Optional[str] = None
    

class SoldMachineBase(BaseModel):
    serial_no: str
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_company: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    date_of_manufacturing: Optional[date] = None

class MachineCreate(MachineBase):
    file_key: Optional[str] = None  # Added file_key for machine creation

class MachineCreateRequest(BaseModel):
    model_no: str
    part_no: Optional[str] = None
    file_key: Optional[str] = None

class MachineCreateResponse(BaseModel):
    success: bool
    message: str
    machine: Dict[str, Any]
    file_uploaded: Optional[bool] = False

    class Config:
        orm_mode = True

class SoldMachineCreate(SoldMachineBase):
    machine_id: str
    serial_no: str

class MachineUpdate(BaseModel):
   
    model_no: Optional[str] = None
    part_no: Optional[str] = None
    type_id: Optional[str] = None
   

class SoldMachineUpdate(BaseModel):
    serial_no: Optional[str] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    date_of_manufacturing: Optional[date] = None

class SoldMachineInDB(SoldMachineBase):
    id: Union[str, uuid.UUID]
    machine_id: Union[str, uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class MachineInDB(MachineBase):
    id: Union[str, uuid.UUID]
    type_id: Union[str, uuid.UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class MachineResponse(MachineInDB):
    machine_type: Dict[str, Any] = None
    sold_info: Optional[SoldMachineInDB] = None

class PaginatedMachineResponse(BaseModel):
    total: int
    page: int
    limit: int
    has_next: bool
    has_previous: bool
    items: List[MachineResponse]

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }

class ServiceReportSummary(BaseModel):
    id: Union[str, uuid.UUID]
    user_id: Union[str, uuid.UUID]
    problem: Optional[str] = None
    solution: Optional[str] = None
    service_person_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    service_type: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None

    class Config:
        orm_mode = True

class MachineDetailsResponse(BaseModel):
    success: bool
    machine: Dict[str, Any]

    class Config:
        orm_mode = True
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }

class MachineUpdateRequest(BaseModel):
    serial_no: Optional[str] = None
    model_no: Optional[str] = None
    part_no: Optional[str] = None
    date_of_manufacturing: Optional[date] = None
    # Customer details
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None

class MachineUpdateResponse(BaseModel):
    success: bool
    message: str
    machine: Dict[str, Any]

    class Config:
        orm_mode = True


class CustomerInfo(BaseModel):
    customer_company: str
    customer_name: str
    customer_contact: Optional[str] = None
    customer_address: Optional[str] = None
    customer_email: Optional[str] = None

class CustomerInfoListResponse(BaseModel):
    customers: List[CustomerInfo]

    class Config:
        orm_mode = True
