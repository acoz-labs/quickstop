import re

EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class InvalidRow(ValueError):
    pass


def validate_row(row):
    name = (row.get("name") or "").strip()
    email = (row.get("email") or "").strip().lower()
    if not name:
        raise InvalidRow("name is required")
    if not email:
        raise InvalidRow("email is required")
    if not EMAIL.fullmatch(email):
        raise InvalidRow(f"email is not valid: {email!r}")
    return {"name": name, "email": email, "phone": (row.get("phone") or "").strip() or None}
