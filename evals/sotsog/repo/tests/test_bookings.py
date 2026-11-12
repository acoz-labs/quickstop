from datetime import datetime

from lanternhall.bookings import Booking, overlaps


def test_back_to_back_bookings_do_not_overlap():
    a = Booking(1, datetime(2026, 11, 3, 9), datetime(2026, 11, 3, 10))
    b = Booking(1, datetime(2026, 11, 3, 10), datetime(2026, 11, 3, 11))
    assert not overlaps(a, b)
