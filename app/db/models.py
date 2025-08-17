from sqlalchemy import Boolean, Column, Integer, String, DateTime, Text, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.db.session import Base

class Role(Base):
    __tablename__ = "role"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    role_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="role")
    
    def __repr__(self):
        return f"<Role {self.role_name}>"
    # Additional methods and properties can be defined here

class Type(Base):
    __tablename__ = "type"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    machines = relationship("Machine", back_populates="machine_type")
    
    def __repr__(self):
        return f"<Type {self.type}>"
    # Additional methods and properties can be defined here

class ServiceType(Base):
    __tablename__ = "service_types"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    service_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    service_reports = relationship("ServiceReport", back_populates="service_type")
    
    def __repr__(self):
        return f"<ServiceType {self.service_type}>"
    # Additional methods and properties can be defined here

class Machine(Base):
    __tablename__ = "machines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    serial_no = Column(String(100), nullable=False, unique=True)
    model_no = Column(String(100), nullable=False)
    part_no = Column(String(100))
    type_id = Column(UUID(as_uuid=True), ForeignKey("type.id"))
    file_key = Column(String(255))  # Added file_key field
    date_of_manufacturing = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    machine_type = relationship("Type", back_populates="machines")
    service_reports = relationship("ServiceReport", back_populates="machine")
    service_parts = relationship("ServiceReportPart", back_populates="machine")
    sold_info = relationship("SoldMachine", back_populates="machine", uselist=False)
    
    def __repr__(self):
        return f"<Machine {self.serial_no}>"

class SoldMachine(Base):
    __tablename__ = "sold_machines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # Added user_id field
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id"), nullable=False)
    
    customer_name = Column(String(255))
    customer_contact = Column(String(50))
    customer_email = Column(String(255))
    customer_address = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="sold_machines")  # Added relationship to User
    machine = relationship("Machine", back_populates="sold_info")
    # Added relationship to ServiceReport
    
    def __repr__(self):
        return f"<SoldMachine {self.id}>"
    # Additional methods and properties can be defined here

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, index=True)
    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"), nullable=True)
    name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    role = relationship("Role", back_populates="users")
    service_reports = relationship("ServiceReport", back_populates="user")
    sold_machines = relationship("SoldMachine", back_populates="user")  # Added relationship to SoldMachine
    
    def __repr__(self):
        return f"<User {self.email}>"
    # Additional methods and properties can be defined here

class ServiceReport(Base):
    __tablename__ = "service_report"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id"))  # Kept for backward compatibility
    service_type_id = Column(UUID(as_uuid=True), ForeignKey("service_types.id"))
    problem = Column(Text)
    solution = Column(Text)
    service_person_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="service_reports")
    machine = relationship("Machine", back_populates="service_reports")  # Added relationship to Machine
  
    service_type = relationship("ServiceType", back_populates="service_reports")
    parts = relationship("ServiceReportPart", back_populates="service_report")
    service_report_files = relationship("ServiceReportFiles", back_populates="service_report")
    
    def __repr__(self):
        return f"<ServiceReport {self.id}>"
    # Additional methods and properties can be defined here

class ServiceReportPart(Base):
    __tablename__ = "service_report_parts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    service_report_id = Column(UUID(as_uuid=True), ForeignKey("service_report.id"))
    machine_id = Column(UUID(as_uuid=True), ForeignKey("machines.id"))
    quantity = Column(Integer, default=1)  # Added quantity field
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    service_report = relationship("ServiceReport", back_populates="parts")
    machine = relationship("Machine", back_populates="service_parts")
    
    def __repr__(self):
        return f"<ServiceReportPart {self.id}>"

class ServiceReportFiles(Base):
    __tablename__ = "service_report_files"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    service_report_id = Column(UUID(as_uuid=True), ForeignKey("service_report.id"))
    file_key = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    service_report = relationship("ServiceReport", back_populates="service_report_files")
    
    def __repr__(self):
        return f"<ServiceReportFiles {self.file_key}>"
    # Additional methods and properties can be defined here
