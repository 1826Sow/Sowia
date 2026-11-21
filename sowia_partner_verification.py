"""Server-side rules for proving control of a partner application's domain.

This module is a validation primitive only. It does not query DNS, persist
challenges, authenticate callers, or approve NIGHT EXCHANGE listings. Production
callers must obtain TXT records from a trusted server-side resolver and persist
single-use challenge consumption in an access-controlled database transaction.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import ipaddress
import re
import secrets
from urllib.parse import urlsplit
from uuid import uuid4


class PartnerVerificationError(ValueError):
    """Raised when a domain-control proof is invalid or unsafe."""


_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _aware_utc(value: datetime, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise PartnerVerificationError(f"{field} doit inclure un fuseau horaire.")
    return value.astimezone(timezone.utc)


def normalize_partner_domain(value: str) -> str:
    """Normalize a bare hostname or HTTPS origin; reject URLs with paths."""
    raw = str(value or "").strip()
    if not raw:
        raise PartnerVerificationError("Domaine requis.")
    if "://" in raw:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() != "https" or not parsed.netloc:
            raise PartnerVerificationError("Seule une origine HTTPS est acceptée.")
        try:
            custom_port = parsed.port
        except ValueError:
            raise PartnerVerificationError("Port d'origine HTTPS invalide.") from None
        if parsed.username or parsed.password or custom_port is not None or parsed.netloc.endswith(":"):
            raise PartnerVerificationError("Identifiants et ports personnalisés interdits.")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise PartnerVerificationError("Fournir uniquement le domaine, sans chemin ni paramètres.")
        host = parsed.hostname or ""
    else:
        if any(char in raw for char in "/?#@"):
            raise PartnerVerificationError("Fournir un nom de domaine, pas une URL complète.")
        host = raw

    host = host.rstrip(".").lower()
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise PartnerVerificationError("Une adresse IP ne remplace pas un nom de domaine.")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise PartnerVerificationError("Nom de domaine international invalide.") from None
    if len(ascii_host) > 253:
        raise PartnerVerificationError("Nom de domaine trop long.")
    labels = ascii_host.split(".")
    if len(labels) < 2 or any(not _LABEL.fullmatch(label) for label in labels):
        raise PartnerVerificationError("Nom de domaine public invalide.")
    if len(labels[-1]) < 2:
        raise PartnerVerificationError("Extension de domaine invalide.")
    return ascii_host


@dataclass(frozen=True)
class DomainChallenge:
    challenge_id: str
    owner_id: str
    domain: str
    token: str
    issued_at: datetime
    expires_at: datetime


def issue_domain_challenge(*, owner_id: str, domain: str, now: datetime,
                           ttl: timedelta = timedelta(hours=24)) -> DomainChallenge:
    """Create an unpredictable DNS TXT challenge for an authenticated owner."""
    owner = str(owner_id or "").strip()
    if not owner:
        raise PartnerVerificationError("Propriétaire authentifié requis.")
    issued = _aware_utc(now, "La date")
    if not isinstance(ttl, timedelta) or ttl < timedelta(minutes=5) or ttl > timedelta(hours=48):
        raise PartnerVerificationError("Durée du défi comprise entre 5 minutes et 48 heures.")
    return DomainChallenge(
        challenge_id=str(uuid4()),
        owner_id=owner,
        domain=normalize_partner_domain(domain),
        token=secrets.token_urlsafe(32),
        issued_at=issued,
        expires_at=issued + ttl,
    )


def domain_challenge_dns_record(challenge: DomainChallenge) -> dict:
    """Return the DNS TXT host/value the owner must publish."""
    if not isinstance(challenge, DomainChallenge):
        raise PartnerVerificationError("Défi de vérification invalide.")
    return {
        "host": f"_sowia-verification.{challenge.domain}",
        "type": "TXT",
        "value": f"sowia-verification={challenge.token}",
    }


def confirm_domain_control_from_dns(
    challenge: DomainChallenge,
    *,
    authenticated_owner_id: str,
    dns_txt_records,
    checked_at: datetime,
    consumed_at: datetime | None = None,
) -> dict:
    """Validate exact TXT proof supplied by a trusted server-side DNS resolver.

    Never pass records supplied by the browser or by the applicant. The
    consumed_at value must come from persistent server-side challenge state;
    atomic one-time consumption belongs in the database transaction.
    """
    if not isinstance(challenge, DomainChallenge):
        raise PartnerVerificationError("Défi de vérification invalide.")
    owner = str(authenticated_owner_id or "").strip()
    if not owner or owner != challenge.owner_id:
        raise PartnerVerificationError("Le défi appartient à un autre compte.")
    checked = _aware_utc(checked_at, "La date de vérification")
    if checked < challenge.issued_at:
        raise PartnerVerificationError("Le défi n'est pas encore valide.")
    if checked >= challenge.expires_at:
        raise PartnerVerificationError("Le défi de vérification a expiré.")
    if consumed_at is not None:
        _aware_utc(consumed_at, "La date de consommation")
        raise PartnerVerificationError("Ce défi a déjà été utilisé.")
    expected = domain_challenge_dns_record(challenge)["value"]
    if isinstance(dns_txt_records, (str, bytes)):
        raise PartnerVerificationError("Réponse DNS invalide.")
    try:
        records = {str(item).strip().strip('"') for item in dns_txt_records}
    except TypeError:
        raise PartnerVerificationError("Réponse DNS invalide.") from None
    if expected not in records:
        raise PartnerVerificationError("Preuve DNS absente ou incorrecte.")
    return {
        "verified": True,
        "verification_method": "dns_txt",
        "domain": challenge.domain,
        "owner_id": challenge.owner_id,
        "challenge_id": challenge.challenge_id,
        "verified_at": checked.isoformat(),
    }


def resolve_domain_challenge_txt(domain: str, *, timeout: float = 5.0) -> list[str]:
    """Resolve the challenge TXT through a fixed server-side DNS-over-HTTPS resolver.

    The resolver endpoint is intentionally not caller-configurable (to prevent
    SSRF). Call only from trusted server code, never from browser-supplied
    domain records. A short bounded timeout limits resource consumption.
    """
    import requests

    normalized = normalize_partner_domain(domain)
    try:
        timeout_value = float(timeout)
    except (TypeError, ValueError):
        raise PartnerVerificationError("Délai DNS invalide.") from None
    if not 1.0 <= timeout_value <= 10.0:
        raise PartnerVerificationError("Délai DNS hors limites.")

    host = f"_sowia-verification.{normalized}"
    try:
        response = requests.get(
            "https://cloudflare-dns.com/dns-query",
            params={"name": host, "type": "TXT"},
            headers={"accept": "application/dns-json"},
            timeout=(min(3.0, timeout_value), timeout_value),
            allow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise PartnerVerificationError("Le service de résolution DNS est indisponible.") from exc

    if not isinstance(payload, dict) or payload.get("Status") != 0:
        raise PartnerVerificationError("La réponse DNS est invalide ou le domaine ne répond pas.")
    answers = payload.get("Answer", [])
    if not isinstance(answers, list) or len(answers) > 64:
        raise PartnerVerificationError("Réponse DNS trop volumineuse ou invalide.")

    records = []
    for answer in answers:
        if not isinstance(answer, dict) or answer.get("type") != 16:
            continue
        data = answer.get("data")
        if not isinstance(data, str):
            continue
        # This challenge is deliberately shorter than the DNS TXT 255-byte
        # string limit, so it must arrive as one quoted character-string.
        value = data.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        if value and len(value) <= 255:
            records.append(value)
    return records


def confirm_domain_control_via_dns(
    challenge: DomainChallenge,
    *,
    authenticated_owner_id: str,
    checked_at: datetime,
) -> dict:
    """Resolve the TXT proof server-side, then validate it against the challenge.

    Persistent atomic consumption must still be performed by the protected
    Supabase RPC; this function alone never marks a partner as approved.
    """
    if not isinstance(challenge, DomainChallenge):
        raise PartnerVerificationError("Défi de vérification invalide.")
    records = resolve_domain_challenge_txt(challenge.domain)
    return confirm_domain_control_from_dns(
        challenge,
        authenticated_owner_id=authenticated_owner_id,
        dns_txt_records=records,
        checked_at=checked_at,
    )
