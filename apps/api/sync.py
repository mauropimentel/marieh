from dataclasses import dataclass
from datetime import datetime, timedelta

from domain import Booking


@dataclass
class GoogleCalendarAdapter:
    def upsert_booking_event(self, booking: Booking) -> None:
        return None

    def cancel_booking_event(self, booking: Booking) -> None:
        return None

    def warn_manual_reconciliation(self, booking: Booking, reason: str) -> None:
        return None


@dataclass
class PartnerSyncAdapter:
    def publish_slot_availability(self, slot_id: str, capacity: int, start_at: datetime) -> None:
        return None

    def ensure_booking_horizon(self, start_at: datetime, max_days: int = 15) -> None:
        if start_at > datetime.utcnow() + timedelta(days=max_days):
            raise ValueError("Booking outside 15-day horizon")


@dataclass
class NotificationAdapter:
    def schedule_reminders(self, booking: Booking) -> None:
        return None

