from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from domain import Alert, Booking, BookingSource, BookingStatus, ClassSlot, Instructor, Student
from sync import GoogleCalendarAdapter, NotificationAdapter, PartnerSyncAdapter

app = FastAPI(title="Marieh OS API", version="0.1.0")

google_calendar = GoogleCalendarAdapter()
partner_sync = PartnerSyncAdapter()
notification = NotificationAdapter()

instructors: Dict[str, Instructor] = {}
students: Dict[str, Student] = {}
slots: Dict[str, ClassSlot] = {}
bookings: Dict[str, Booking] = {}
alerts: Dict[str, Alert] = {}


class InstructorCreate(BaseModel):
    name: str
    max_students_per_slot: int
    google_calendar_id: str


class SlotCreate(BaseModel):
    instructor_id: str
    start_at: datetime
    end_at: datetime
    capacity: int


class BookingCreate(BaseModel):
    slot_id: str
    cpf: str
    full_name: str
    source: BookingSource
    external_id: str | None = None


class BookingUpdate(BaseModel):
    status: BookingStatus


class PartnerBookingWebhook(BaseModel):
    partner: BookingSource
    event_type: str
    slot_id: str
    cpf: str
    full_name: str
    external_id: str
    changed_at: datetime


class CheckinWebhook(BaseModel):
    booking_id: str
    source: str
    checked_in_at: datetime


def _slot_bookings(slot_id: str) -> List[Booking]:
    return [booking for booking in bookings.values() if booking.slot_id == slot_id and booking.status != BookingStatus.cancelled]


def _assert_capacity(slot: ClassSlot) -> None:
    current = len(_slot_bookings(slot.id))
    if current >= slot.capacity:
        raise HTTPException(status_code=409, detail="Slot capacity reached")


def _ensure_student(cpf: str, full_name: str) -> Student:
    if not cpf:
        raise HTTPException(status_code=422, detail="CPF is required for identity matching")
    if cpf in students:
        return students[cpf]
    student = Student(cpf=cpf, full_name=full_name)
    students[cpf] = student
    return student


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "marieh-os-api"}


@app.post("/instructors", response_model=Instructor)
def create_instructor(payload: InstructorCreate) -> Instructor:
    instructor_id = str(uuid4())
    instructor = Instructor(
        id=instructor_id,
        name=payload.name,
        max_students_per_slot=payload.max_students_per_slot,
        google_calendar_id=payload.google_calendar_id,
    )
    instructors[instructor_id] = instructor
    return instructor


@app.get("/instructors", response_model=List[Instructor])
def list_instructors() -> List[Instructor]:
    return list(instructors.values())


@app.post("/slots", response_model=ClassSlot)
def create_slot(payload: SlotCreate) -> ClassSlot:
    if payload.instructor_id not in instructors:
        raise HTTPException(status_code=404, detail="Instructor not found")
    slot_id = str(uuid4())
    slot = ClassSlot(
        id=slot_id,
        instructor_id=payload.instructor_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        capacity=payload.capacity,
    )
    slots[slot_id] = slot
    partner_sync.publish_slot_availability(slot_id=slot.id, capacity=slot.capacity, start_at=slot.start_at)
    return slot


@app.get("/slots", response_model=List[ClassSlot])
def list_slots() -> List[ClassSlot]:
    return list(slots.values())


@app.post("/bookings", response_model=Booking)
def create_booking(payload: BookingCreate) -> Booking:
    slot = slots.get(payload.slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    partner_sync.ensure_booking_horizon(start_at=slot.start_at)
    _assert_capacity(slot)
    _ensure_student(cpf=payload.cpf, full_name=payload.full_name)

    booking_id = str(uuid4())
    now = datetime.utcnow()
    booking = Booking(
        id=booking_id,
        slot_id=payload.slot_id,
        student_cpf=payload.cpf,
        student_name=payload.full_name,
        source=payload.source,
        status=BookingStatus.created,
        external_id=payload.external_id,
        created_at=now,
        updated_at=now,
    )
    bookings[booking_id] = booking

    google_calendar.upsert_booking_event(booking)
    notification.schedule_reminders(booking)
    return booking


@app.patch("/bookings/{booking_id}", response_model=Booking)
def update_booking(booking_id: str, payload: BookingUpdate) -> Booking:
    booking = bookings.get(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = payload.status
    booking.updated_at = datetime.utcnow()
    bookings[booking_id] = booking

    if payload.status == BookingStatus.cancelled:
        google_calendar.cancel_booking_event(booking)
    else:
        google_calendar.upsert_booking_event(booking)
    return booking


@app.get("/bookings", response_model=List[Booking])
def list_bookings() -> List[Booking]:
    return list(bookings.values())


@app.post("/webhooks/partners")
def partner_webhook(payload: PartnerBookingWebhook) -> dict:
    if payload.partner not in (BookingSource.totalpass, BookingSource.wellhub):
        raise HTTPException(status_code=422, detail="Unsupported partner source")

    if payload.event_type in ("booking_created", "booking_updated"):
        booking = create_booking(
            BookingCreate(
                slot_id=payload.slot_id,
                cpf=payload.cpf,
                full_name=payload.full_name,
                source=payload.partner,
                external_id=payload.external_id,
            )
        )
        alert = Alert(
            id=str(uuid4()),
            booking_id=booking.id,
            kind="calendar_reconciliation",
            message="Partner update applied; verify Google Calendar consistency.",
            created_at=datetime.utcnow(),
        )
        alerts[alert.id] = alert
        google_calendar.warn_manual_reconciliation(booking, reason=alert.message)
        return {"ok": True, "booking_id": booking.id, "alert_id": alert.id}

    if payload.event_type == "booking_cancelled":
        target = next((item for item in bookings.values() if item.external_id == payload.external_id), None)
        if not target:
            raise HTTPException(status_code=404, detail="Booking not found by external_id")
        target.status = BookingStatus.cancelled
        target.updated_at = datetime.utcnow()
        bookings[target.id] = target
        google_calendar.cancel_booking_event(target)
        return {"ok": True, "booking_id": target.id}

    raise HTTPException(status_code=422, detail="Unsupported event_type")


@app.post("/webhooks/checkins")
def checkin_webhook(payload: CheckinWebhook) -> dict:
    booking = bookings.get(payload.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = BookingStatus.attended
    booking.updated_at = datetime.utcnow()
    bookings[booking.id] = booking
    return {"ok": True, "booking_id": booking.id, "status": booking.status, "source": payload.source}


@app.get("/alerts", response_model=List[Alert])
def list_alerts() -> List[Alert]:
    return list(alerts.values())

