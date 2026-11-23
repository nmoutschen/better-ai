from attachments import list_attachments


def test_list():
    assert list_attachments("42") == ["invoice.txt", "photo-notes.txt"]
