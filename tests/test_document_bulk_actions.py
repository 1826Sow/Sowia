import pytest

from document_bulk_actions import delete_selected_documents


def test_deletes_selected_documents_and_counts_failures():
    calls = []

    def delete_one(document_id):
        calls.append(document_id)
        if document_id == 2:
            raise RuntimeError("storage unavailable")

    result = delete_selected_documents([1, 2, 3], delete_one)
    assert calls == [1, 2, 3]
    assert result == {"deleted": 2, "failed": 1}


@pytest.mark.parametrize("ids", [[], [0], [-1], [True], ["x"], [1, 1], list(range(1, 22))])
def test_rejects_invalid_or_oversized_selections(ids):
    with pytest.raises(ValueError):
        delete_selected_documents(ids, lambda _document_id: None)


def test_requires_callable_delete_function():
    with pytest.raises(ValueError):
        delete_selected_documents([1], None)
