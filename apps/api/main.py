from dotenv import load_dotenv

load_dotenv()

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from db import get_db
from domain import Alert, Booking, BookingSource, BookingStatus, ClassSlot, Instructor, Student
from models import AlertModel, BookingModel, ClassSlotModel, InstructorModel, StudentModel
from sync import GoogleCalendarAdapter, IntegrationSettings, NotificationAdapter, PartnerSyncAdapter

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Marieh OS API", version="0.3.0")

settings = IntegrationSettings()
google_calendar = GoogleCalendarAdapter(settings=settings)
partner_sync = PartnerSyncAdapter(settings=settings)
notification = NotificationAdapter(settings=settings)


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


def _to_instructor(row: InstructorModel) -> Instructor:
    return Instructor.model_validate(row)


def _to_slot(row: ClassSlotModel) -> ClassSlot:
    return ClassSlot.model_validate(row)


def _to_booking(row: BookingModel) -> Booking:
    return Booking.model_validate(row)


def _to_alert(row: AlertModel) -> Alert:
    return Alert.model_validate(row)


def _assert_capacity(db: Session, slot: ClassSlotModel) -> None:
    current = (
        db.query(func.count(BookingModel.id))
        .filter(BookingModel.slot_id == slot.id)
        .filter(BookingModel.status != BookingStatus.cancelled.value)
        .scalar()
    )
    if current >= slot.capacity:
        raise HTTPException(status_code=409, detail="Slot capacity reached")


def _ensure_student(db: Session, cpf: str, full_name: str) -> StudentModel:
    if not cpf:
        raise HTTPException(status_code=422, detail="CPF is required for identity matching")
    student = db.get(StudentModel, cpf)
    if student:
        return student
    student = StudentModel(cpf=cpf, full_name=full_name)
    db.add(student)
    db.flush()
    return student


def _resolve_slot_and_instructor(db: Session, slot_id: str) -> tuple[ClassSlotModel, InstructorModel]:
    slot = db.get(ClassSlotModel, slot_id)
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    instructor = db.get(InstructorModel, slot.instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return slot, instructor


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "marieh-os-api"}


@app.post("/instructors", response_model=Instructor)
def create_instructor(payload: InstructorCreate, db: Session = Depends(get_db)) -> Instructor:
    instructor = InstructorModel(
        id=str(uuid4()),
        name=payload.name,
        max_students_per_slot=payload.max_students_per_slot,
        google_calendar_id=payload.google_calendar_id,
    )
    db.add(instructor)
    db.commit()
    db.refresh(instructor)
    return _to_instructor(instructor)


@app.get("/instructors", response_model=List[Instructor])
def list_instructors(db: Session = Depends(get_db)) -> List[Instructor]:
    rows = db.query(InstructorModel).all()
    return [_to_instructor(item) for item in rows]


@app.post("/slots", response_model=ClassSlot)
def create_slot(payload: SlotCreate, db: Session = Depends(get_db)) -> ClassSlot:
    instructor = db.get(InstructorModel, payload.instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")

    slot = ClassSlotModel(
        id=str(uuid4()),
        instructor_id=payload.instructor_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        capacity=payload.capacity,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)

    partner_sync.publish_slot_availability(slot_id=slot.id, capacity=slot.capacity, start_at=slot.start_at)
    return _to_slot(slot)


@app.get("/slots", response_model=List[ClassSlot])
def list_slots(db: Session = Depends(get_db)) -> List[ClassSlot]:
    rows = db.query(ClassSlotModel).all()
    return [_to_slot(item) for item in rows]


@app.post("/bookings", response_model=Booking)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)) -> Booking:
    slot, instructor = _resolve_slot_and_instructor(db, payload.slot_id)

    try:
        partner_sync.ensure_booking_horizon(start_at=slot.start_at)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    _assert_capacity(db, slot)
    _ensure_student(db=db, cpf=payload.cpf, full_name=payload.full_name)

    now = datetime.now(timezone.utc)
    booking = BookingModel(
        id=str(uuid4()),
        slot_id=payload.slot_id,
        student_cpf=payload.cpf,
        student_name=payload.full_name,
        source=payload.source.value,
        status=BookingStatus.created.value,
        external_id=payload.external_id,
        created_at=now,
        updated_at=now,
    )

    booking_schema = Booking.model_validate(booking)
    slot_schema = ClassSlot.model_validate(slot)
    instructor_schema = Instructor.model_validate(instructor)
    booking.google_event_id = google_calendar.upsert_booking_event(
        booking=booking_schema,
        slot=slot_schema,
        instructor=instructor_schema,
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    notification.schedule_reminders(booking=Booking.model_validate(booking), slot=slot_schema)
    return _to_booking(booking)


@app.patch("/bookings/{booking_id}", response_model=Booking)
def update_booking(booking_id: str, payload: BookingUpdate, db: Session = Depends(get_db)) -> Booking:
    booking = db.get(BookingModel, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    slot, instructor = _resolve_slot_and_instructor(db, booking.slot_id)
    booking.status = payload.status.value
    booking.updated_at = datetime.now(timezone.utc)

    booking_schema = Booking.model_validate(booking)
    instructor_schema = Instructor.model_validate(instructor)
    if payload.status == BookingStatus.cancelled:
        google_calendar.cancel_booking_event(booking=booking_schema, instructor=instructor_schema)
    else:
        booking.google_event_id = google_calendar.upsert_booking_event(
            booking=booking_schema,
            slot=ClassSlot.model_validate(slot),
            instructor=instructor_schema,
        )

    db.add(booking)
    db.commit()
    db.refresh(booking)
    return _to_booking(booking)


@app.get("/bookings", response_model=List[Booking])
def list_bookings(db: Session = Depends(get_db)) -> List[Booking]:
    rows = db.query(BookingModel).all()
    return [_to_booking(item) for item in rows]


@app.post("/webhooks/partners")
def partner_webhook(payload: PartnerBookingWebhook, db: Session = Depends(get_db)) -> dict:
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
            ),
            db,
        )
        alert = AlertModel(
            id=str(uuid4()),
            booking_id=booking.id,
            kind="calendar_reconciliation",
            message="Partner update applied; verify Google Calendar consistency.",
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        db.commit()
        google_calendar.warn_manual_reconciliation(booking, reason=alert.message)
        return {"ok": True, "booking_id": booking.id, "alert_id": alert.id}

    if payload.event_type == "booking_cancelled":
        target = db.query(BookingModel).filter(BookingModel.external_id == payload.external_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Booking not found by external_id")
        _, instructor = _resolve_slot_and_instructor(db, target.slot_id)
        target.status = BookingStatus.cancelled.value
        target.updated_at = datetime.now(timezone.utc)
        db.add(target)
        db.commit()

        google_calendar.cancel_booking_event(
            booking=Booking.model_validate(target),
            instructor=Instructor.model_validate(instructor),
        )
        return {"ok": True, "booking_id": target.id, "slot_id": target.slot_id}

    raise HTTPException(status_code=422, detail="Unsupported event_type")


@app.post("/webhooks/checkins")
def checkin_webhook(payload: CheckinWebhook, db: Session = Depends(get_db)) -> dict:
    booking = db.get(BookingModel, payload.booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = BookingStatus.attended.value
    booking.updated_at = datetime.now(timezone.utc)
    db.add(booking)
    db.commit()
    return {"ok": True, "booking_id": booking.id, "status": booking.status, "source": payload.source}


@app.get("/alerts", response_model=List[Alert])
def list_alerts(db: Session = Depends(get_db)) -> List[Alert]:
    rows = db.query(AlertModel).order_by(AlertModel.created_at.desc()).all()
    return [_to_alert(item) for item in rows]


