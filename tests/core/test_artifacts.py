"""Tests for temporary artifact storage."""

from datetime import datetime, timedelta, timezone

from polarion_mcp.core.artifacts import ArtifactStore


def test_register_and_get_artifact(tmp_path) -> None:
    """Test storing and retrieving a generated artifact."""
    store = ArtifactStore(ttl_seconds=3600)
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    record = store.register_file(pdf_path, "sample.pdf")
    fetched = store.get(record.artifact_id)

    assert fetched is not None
    assert fetched.path == pdf_path.resolve()
    assert fetched.filename == "sample.pdf"


def test_expired_artifact_is_removed(tmp_path) -> None:
    """Test expired artifacts are cleaned up automatically."""
    store = ArtifactStore(ttl_seconds=3600)
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 mock")

    record = store.register_file(pdf_path, "sample.pdf")
    store._items[record.artifact_id].expires_at = datetime.now(
        timezone.utc
    ) - timedelta(seconds=1)

    assert store.get(record.artifact_id) is None
    assert not pdf_path.exists(), "Expired artifact file should be deleted from disk"
