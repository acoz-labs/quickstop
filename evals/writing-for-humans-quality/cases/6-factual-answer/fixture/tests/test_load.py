import pytest

from importer.load import import_file
from importer.validate import InvalidRow


def test_blank_email_rejects_whole_file(tmp_path, empty_db):
    path = tmp_path / "contacts.csv"
    path.write_text("name,email\nAda,ada@example.com\nBo,\n")
    with pytest.raises(InvalidRow, match="contacts.csv:3: email is required"):
        import_file(path)
    assert empty_db.count() == 0
