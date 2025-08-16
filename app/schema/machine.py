from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
import uuid

class MachineBase(BaseModel):
    serial_no: str
    model_no: str
    part_no: Optional[str] = None

class SoldMachineBase(BaseModel):
    date_of_manufacturing: Optional[date] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None

class MachineCreate(MachineBase):
    type_id: str

class SoldMachineCreate(SoldMachineBase):
    machine_id: str

class MachineUpdate(BaseModel):
    serial_no: Optional[str] = None
    model_no: Optional[str] = None
    part_no: Optional[str] = None
    type_id: Optional[str] = None

class SoldMachineUpdate(BaseModel):
    date_of_manufacturing: Optional[date] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None

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
