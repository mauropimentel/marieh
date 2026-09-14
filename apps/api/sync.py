import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from domain import Booking, ClassSlot, Instructor
from google.oauth2 import service_account
from googleapiclient.discovery import build


@dataclass
class IntegrationSettings:
    google_service_account_file: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    google_calendar_timezone: str = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "Europe/Paris")
    totalpass_base_url: Optional[str] = os.getenv("TOTALPASS_BASE_URL")
    totalpass_api_token: Optional[str] = os.getenv("TOTALPASS_API_TOKEN")
    wellhub_base_url: Optional[str] = os.getenv("WELLHUB_BASE_URL")
    wellhub_api_token: Optional[str] = os.getenv("WELLHUB_API_TOKEN")
    reminder_webhook_url: Optional[str] = os.getenv("REMINDER_WEBHOOK_URL")


@dataclass
class GoogleCalendarAdapter:
    settings: IntegrationSettings

    def _service(self):
        if not self.settings.google_service_account_file:
            return None

        credentials = service_account.Credentials.from_service_account_file(
            self.settings.google_service_account_file,
            scopes=["https://www.googleapis.com/auth/calendar"],
        )
        return build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def upsert_booking_event(self, booking: Booking, slot: ClassSlot, instructor: Instructor) -> Optional[str]:
        service = self._service()
        if not service:
            return booking.google_event_id

        event_body = {
            "summary": f"Marieh Pilates - {booking.student_name}",
            "description": f"CPF: {booking.student_cpf} | Origem: {booking.source}",
            "start": {
                "dateTime": slot.start_at.astimezone(timezone.utc).isoformat(),
                "timeZone": self.settings.google_calendar_timezone,
            },
            "end": {
                "dateTime": slot.end_at.astimezone(timezone.utc).isoformat(),
                "timeZone": self.settings.google_calendar_timezone,
            },
            "extendedProperties": {
                "private": {
                    "booking_id": booking.id,
                    "student_cpf": booking.student_cpf,
                    "external_id": booking.external_id or "",
                }
            },
        }

        if booking.google_event_id:
            event = (
                service.events()
                .update(
                    calendarId=instructor.google_calendar_id,
                    eventId=booking.google_event_id,
                    body=event_body,
                )
                .execute()
            )
            return event.get("id")

        event = service.events().insert(calendarId=instructor.google_calendar_id, body=event_body).execute()
        return event.get("id")

    def cancel_booking_event(self, booking: Booking, instructor: Instructor) -> None:
        service = self._service()
        if not service or not booking.google_event_id:
            return None
        (
            service.events()
            .delete(calendarId=instructor.google_calendar_id, eventId=booking.google_event_id)
            .execute()
        )
        return None

    def warn_manual_reconciliation(self, booking: Booking, reason: str) -> None:
        print(f"[RECONCILIATION_ALERT] booking={booking.id} reason={reason}")


@dataclass
class PartnerSyncAdapter:
    settings: IntegrationSettings

    def _post_partner(self, base_url: Optional[str], token: Optional[str], payload: dict) -> None:
        if not base_url or not token:
            return None

        with httpx.Client(timeout=10.0) as client:
            client.post(
                f"{base_url.rstrip('/')}/availability",
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )

    def publish_slot_availability(self, slot_id: str, capacity: int, start_at: datetime) -> None:
        payload = {
            "slot_id": slot_id,
            "capacity": capacity,
            "start_at": start_at.isoformat(),
        }
        self._post_partner(self.settings.totalpass_base_url, self.settings.totalpass_api_token, payload)
        self._post_partner(self.settings.wellhub_base_url, self.settings.wellhub_api_token, payload)

    def ensure_booking_horizon(self, start_at: datetime, max_days: int = 15) -> None:
        now = datetime.now(timezone.utc)
        slot_start = start_at if start_at.tzinfo else start_at.replace(tzinfo=timezone.utc)
        if slot_start > now + timedelta(days=max_days):
            raise ValueError("Booking outside 15-day horizon")


@dataclass
class NotificationAdapter:
    settings: IntegrationSettings

    def schedule_reminders(self, booking: Booking, slot: ClassSlot) -> None:
        if not self.settings.reminder_webhook_url:
            return None

        payload = {
            "booking_id": booking.id,
            "student_cpf": booking.student_cpf,
            "student_name": booking.student_name,
            "slot_start_at": slot.start_at.isoformat(),
            "channels": ["whatsapp"],
            "offsets_hours": [24, 2],
        }
        with httpx.Client(timeout=10.0) as client:
            client.post(self.settings.reminder_webhook_url, json=payload)
        return None
