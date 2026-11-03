import csv

from importer import db
from importer.validate import InvalidRow, validate_row


def import_file(path):
    """Import every contact in the file, or none of them."""
    with open(path, newline="") as handle:
        rows = list(csv.DictReader(handle))
    contacts = []
    for number, row in enumerate(rows, start=2):  # line 1 is the header
        try:
            contacts.append(validate_row(row))
        except InvalidRow as exc:
            raise InvalidRow(f"{path}:{number}: {exc}") from exc
    with db.transaction() as tx:
        for contact in contacts:
            tx.insert_contact(contact)
    return len(contacts)
