"""Deployment-level Streamlit upload and WebSocket size limits."""
from pathlib import Path


def test_streamlit_upload_and_message_limits_are_configured():
    config = (Path(__file__).resolve().parents[1] / ".streamlit" / "config.toml").read_text(
        encoding="utf-8"
    )
    assert "[server]" in config
    assert "maxUploadSize = 20" in config
    assert "maxMessageSize = 25" in config
