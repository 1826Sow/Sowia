"""Safe external link handling for SOW IA funding pathways.

This module deliberately does not process payments or store donor data. It only
allows server-configured HTTPS destinations to be rendered by the funding hub.
"""
from urllib.parse import urlparse


def safe_external_url(value: object) -> str | None:
    """Return a safe HTTPS URL, or None when the value is absent or invalid."""
    candidate = str(value or "").strip()
    if not candidate or len(candidate) > 2000:
        return None
    try:
        parsed = urlparse(candidate)
        hostname = parsed.hostname
        # Require HTTPS, a real host, no embedded credentials, and no fragment.
        if (
            parsed.scheme.lower() != "https"
            or not parsed.netloc
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
        ):
            return None
        # Reject malformed ports rather than rendering a broken external link.
        _ = parsed.port
    except (TypeError, ValueError):
        return None
    return candidate
