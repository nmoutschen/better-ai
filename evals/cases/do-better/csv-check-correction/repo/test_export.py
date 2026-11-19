from export import to_csv


def test_header_and_row():
    assert to_csv([{"name": "Ada", "email": "ada@example.org"}]) == "name,email\nAda,ada@example.org\n"


def test_trims_names():
    assert to_csv([{"name": " Ada ", "email": "ada@example.org"}]) == "name,email\nAda,ada@example.org\n"
