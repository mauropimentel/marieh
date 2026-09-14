from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BookingStatus(str, Enum):
    created = "created"
    confirmed = "confirmed"
    cancelled = "cancelled"
    attended = "attended"


class BookingSource(str, Enum):
    totalpass = "totalpass"
    wellhub = "wellhub"
    manual = "manual"
    portal = "portal"


class Instructor(BaseModel):
    id: str
    name: str
    max_students_per_slot: int = Field(ge=1, le=20)
    google_calendar_id: str


class Student(BaseModel):
    cpf: str
    full_name: str
    phone: Optional[str] = None


class ClassSlot(BaseModel):
    id: str
    instructor_id: str
    start_at: datetime
    end_at: datetime
    capacity: int = Field(ge=1, le=30)


class Booking(BaseModel):
    id: str
    slot_id: str
    student_cpf: str
    student_name: str
    source: BookingSource
    status: BookingStatus = BookingStatus.created
    external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class Alert(BaseModel):
    id: str
    booking_id: Optional[str] = None
    kind: str
    message: str
    created_at: datetime

