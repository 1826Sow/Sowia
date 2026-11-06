"""Fail-closed shared rate limiting backed by the authenticated Supabase RPC."""
from dataclasses import dataclass

BUCKETS = {
    "assistant", "pdf_question", "advanced_pdf", "batch_pdf",
    "web_search", "document_upload", "document_download", "document_delete",
}


class RateLimitExceeded(PermissionError):
    """The authenticated account has exhausted an operation quota."""


class RateLimitUnavailable(RuntimeError):
    """The shared quota service could not safely authorize an operation."""


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    reset_at: str


def consume_rate_limit(client, user, bucket_key):
    """Consume one shared quota unit; never fall back to local counters."""
    user_id = getattr(user, "id", None)
    if not isinstance(user_id, str) or not user_id.strip():
        raise PermissionError("Connexion requise pour cette opération.")
    if not isinstance(bucket_key, str) or bucket_key not in BUCKETS:
        raise ValueError("Catégorie de quota invalide.")

    try:
        response = client.rpc(
            "sowia_consume_rate_limit", {"p_bucket_key": bucket_key}
        ).execute()
        data = getattr(response, "data", None)
        if isinstance(data, list) and len(data) == 1:
            data = data[0]
        if not isinstance(data, dict):
            raise ValueError("Réponse RPC invalide.")
        allowed = data.get("allowed")
        remaining = data.get("remaining")
        reset_at = data.get("reset_at")
        if (not isinstance(allowed, bool)
                or isinstance(remaining, bool)
                or not isinstance(remaining, int)
                or remaining < 0
                or not isinstance(reset_at, str)
                or not reset_at.strip()):
            raise ValueError("Champs RPC invalides.")
        decision = RateLimitDecision(allowed, remaining, reset_at)
    except Exception as exc:
        raise RateLimitUnavailable(
            "Le contrôle de quota est indisponible. Opération refusée."
        ) from exc

    if not decision.allowed:
        raise RateLimitExceeded(
            "Limite temporaire atteinte. Réessayez après le renouvellement du quota."
        )
    return decision
