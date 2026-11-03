import contextlib
import sqlite3

PATH = "contactbook.db"


@contextlib.contextmanager
def transaction():
    connection = sqlite3.connect(PATH)
    try:
        yield Inserter(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


class Inserter:
    def __init__(self, connection):
        self.connection = connection

    def insert_contact(self, contact):
        self.connection.execute(
            "INSERT INTO contacts (name, email, phone) VALUES (:name, :email, :phone)", contact)
