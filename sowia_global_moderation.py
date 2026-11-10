"""Small validation helpers for SOWIA moderation actions."""

ALLOWED_REPORT_STATUSES = {"open", "reviewing", "resolved", "dismissed"}
ALLOWED_PROFILE_STATUSES = {"pending", "verified", "suspended", "unverified"}


def validate_moderation_note(value):
    note = str(value or "").strip()
    if len(note) > 1000:
        raise ValueError("La note de modération est limitée à 1 000 caractères.")
    return note


def validate_report_status(value):
    if value not in ALLOWED_REPORT_STATUSES:
        raise ValueError("Statut de signalement invalide.")
    return value


def validate_profile_status(value, evidence_reference=""):
    if value not in ALLOWED_PROFILE_STATUSES:
        raise ValueError("Statut de profil invalide.")
    evidence = str(evidence_reference or "").strip()
    if len(evidence) > 240:
        raise ValueError("La référence de preuve est trop longue.")
    if value == "verified" and not evidence:
        raise ValueError("Une référence de preuve est obligatoire pour vérifier un profil.")
    return value, evidence



REPORT_PATTERN_THRESHOLD = 3


def summarize_report_patterns(reports, threshold=REPORT_PATTERN_THRESHOLD):
    """Flag repeated report patterns for human review; never infer guilt or auto-sanction."""
    try:
        minimum = max(2, int(threshold))
    except (TypeError, ValueError):
        minimum = REPORT_PATTERN_THRESHOLD
    target_counts = {}
    reporter_counts = {}
    for report in reports or []:
        if not isinstance(report, dict) or report.get("status") in {"dismissed", "resolved"}:
            continue
        target = str(report.get("reported_user_id") or "").strip()
        reporter = str(report.get("reporter_id") or "").strip()
        if target:
            target_counts[target] = target_counts.get(target, 0) + 1
        if reporter:
            reporter_counts[reporter] = reporter_counts.get(reporter, 0) + 1
    repeated_targets = [
        {"account_id": account, "report_count": count}
        for account, count in target_counts.items() if count >= minimum
    ]
    repeated_reporters = [
        {"account_id": account, "report_count": count}
        for account, count in reporter_counts.items() if count >= minimum
    ]
    return {
        "threshold": minimum,
        "repeated_targets": sorted(repeated_targets, key=lambda item: (-item["report_count"], item["account_id"])),
        "repeated_reporters": sorted(repeated_reporters, key=lambda item: (-item["report_count"], item["account_id"])),
    }
