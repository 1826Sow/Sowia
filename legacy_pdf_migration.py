"""Safe, copy-only migration helpers for legacy flat PDF objects.

The default operation is a dry run. Applying a plan copies and verifies each
PDF into the Personal workspace; it never deletes or overwrites the source.
"""
from hashlib import sha256

from document_storage import (
    BUCKET_NAME,
    MAX_DOCUMENT_BYTES,
    _user_prefix,
    _validate_pdf,
)


def _is_pdf_object(item):
    if not isinstance(item, dict):
        return False
    name = item.get("name")
    # Supabase Storage directory entries have no object id; ignore folders.
    return (
        isinstance(name, str)
        and name.lower().endswith(".pdf")
        and bool(item.get("id"))
        and "/" not in name
        and name not in {".", ".."}
    )


def _list_all(bucket, prefix, page_size=100):
    """Fetch every Storage listing page instead of silently stopping at 100."""
    items = []
    offset = 0
    while True:
        page = bucket.list(prefix, {"limit": page_size, "offset": offset})
        if not page:
            break
        items.extend(page)
        if len(page) < page_size:
            break
        offset += len(page)
    return items


def plan_legacy_pdf_migration(client, user):
    """List legacy root PDFs and identify safe Personal destinations.

    This function is read-only. Existing Personal filenames are treated as
    collisions and are never overwritten.
    """
    user_prefix = _user_prefix(user)
    bucket = client.storage.from_(BUCKET_NAME)
    legacy_items = _list_all(bucket, user_prefix)
    personal_items = _list_all(bucket, f"{user_prefix}/personal")
    existing_names = {
        item.get("name")
        for item in personal_items
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }

    plan = []
    for item in legacy_items:
        if not _is_pdf_object(item):
            continue
        name = item["name"]
        destination = f"{user_prefix}/personal/{name}"
        plan.append({
            "source": f"{user_prefix}/{name}",
            "destination": destination,
            "status": "collision" if name in existing_names else "ready",
        })
    return sorted(plan, key=lambda entry: entry["source"].casefold())


def migrate_legacy_pdfs(client, user, *, apply=False):
    """Dry-run by default; when applied, copy and verify without deleting.

    Returns a per-file report. No source object is ever removed. The caller
    must separately review the report before any future cleanup is considered.
    """
    plan = plan_legacy_pdf_migration(client, user)
    if not apply:
        return [
            {**entry, "status": "dry_run" if entry["status"] == "ready" else entry["status"]}
            for entry in plan
        ]

    bucket = client.storage.from_(BUCKET_NAME)
    report = []
    for entry in plan:
        if entry["status"] != "ready":
            report.append(entry)
            continue
        try:
            source_bytes = bytes(bucket.download(entry["source"]))
            if len(source_bytes) > MAX_DOCUMENT_BYTES:
                report.append({**entry, "status": "source_too_large"})
                continue
            try:
                _validate_pdf(source_bytes)
            except (ValueError, TypeError):
                report.append({**entry, "status": "invalid_source_pdf"})
                continue

            bucket.upload(
                entry["destination"],
                source_bytes,
                file_options={"content-type": "application/pdf", "upsert": "false"},
            )
            copied_bytes = bytes(bucket.download(entry["destination"]))
            if sha256(copied_bytes).digest() != sha256(source_bytes).digest():
                report.append({**entry, "status": "verification_failed"})
                continue
            report.append({
                **entry,
                "status": "copied_verified",
                "sha256": sha256(source_bytes).hexdigest(),
                "bytes": len(source_bytes),
            })
        except Exception as exc:
            # Keep the report useful without exposing credentials or payloads.
            report.append({**entry, "status": "error", "error_type": type(exc).__name__})
    return report
