"""Booking rules: a room can't be booked twice for overlapping times."""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Booking:
    room_id: int
    starts_at: datetime
    ends_at: datetime


def overlaps(a: Booking, b: Booking) -> bool:
    return a.room_id == b.room_id and a.starts_at < b.ends_at and b.starts_at < a.ends_at
