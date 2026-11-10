"""International print supplier directory and quote comparison for SOW IA."""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse
from uuid import uuid4

QUOTE_STATUSES = {"received", "validated", "expired"}

def _text(value, field, limit, required=True):
    if not isinstance(value, str):
        raise ValueError(f"Le champ {field} doit être du texte.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"Le champ {field} est obligatoire.")
    if len(value) > limit:
        raise ValueError(f"Le champ {field} dépasse {limit} caractères.")
    return value

def _money(value, field):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"Montant invalide : {field}.")
    if not amount.is_finite() or amount < 0 or amount > Decimal("100000000"):
        raise ValueError(f"Montant hors limites : {field}.")
    return amount.quantize(Decimal("0.01"))

def validate_printer_candidate(raw):
    if not isinstance(raw, dict):
        raise ValueError("Fiche imprimeur invalide.")
    name = _text(raw.get("name"), "nom", 120)
    country = _text(raw.get("country"), "pays", 100)
    website = _text(raw.get("website", ""), "site web", 300, required=False)
    if website:
        parsed = urlparse(website)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Le site de l'imprimeur doit utiliser HTTPS.")
    capabilities = raw.get("capabilities", [])
    if not isinstance(capabilities, list) or len(capabilities) > 20:
        raise ValueError("Liste de services invalide.")
    clean = [_text(item, "service", 80) for item in capabilities]
    return {"id": str(raw.get("id") or uuid4()), "name": name, "country": country,
            "website": website, "capabilities": clean, "status": "candidate"}

def validate_printer_quote(raw):
    if not isinstance(raw, dict):
        raise ValueError("Devis imprimeur invalide.")
    supplier_id = _text(raw.get("supplier_id"), "imprimeur", 80)
    destination = _text(raw.get("destination_country"), "pays de livraison", 100)
    currency = _text(raw.get("currency"), "devise", 3).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("La devise doit être un code de trois lettres, par exemple EUR.")
    quantity = raw.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 100000:
        raise ValueError("La quantité doit être un entier entre 1 et 100 000.")
    lead_days = raw.get("lead_days")
    if isinstance(lead_days, bool) or not isinstance(lead_days, int) or not 1 <= lead_days <= 365:
        raise ValueError("Le délai doit être compris entre 1 et 365 jours.")
    try:
        expiry = date.fromisoformat(str(raw.get("valid_until")))
    except (TypeError, ValueError):
        raise ValueError("Date de validité du devis invalide.")
    return {"id": str(raw.get("id") or uuid4()), "supplier_id": supplier_id,
            "destination_country": destination, "quantity": quantity, "currency": currency,
            "printing_cost": _money(raw.get("printing_cost"), "impression"),
            "shipping_cost": _money(raw.get("shipping_cost"), "livraison"),
            "lead_days": lead_days, "paper_finish": _text(raw.get("paper_finish"), "papier et finition", 160),
            "valid_until": expiry.isoformat(), "status": "received"}

def compare_printer_quotes(suppliers, quotes, destination_country, quantity, currency, today=None):
    """Compare like-for-like quotes; no currency conversion and no automatic approval."""
    if not isinstance(destination_country, str) or not destination_country.strip():
        raise ValueError("Pays de livraison obligatoire.")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise ValueError("Quantité invalide.")
    currency = str(currency).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("Devise invalide.")
    today = today or date.today()
    supplier_map = {item["id"]: item for item in suppliers}
    rows = []
    for quote in quotes:
        supplier = supplier_map.get(quote.get("supplier_id"))
        if not supplier or quote.get("destination_country", "").casefold() != destination_country.strip().casefold():
            continue
        if quote.get("quantity") != quantity or quote.get("currency") != currency:
            continue
        expired = date.fromisoformat(quote["valid_until"]) < today
        verified = supplier.get("status") == "verified"
        validated = quote.get("status") == "validated"
        eligible = verified and validated and not expired
        rows.append({"supplier_name": supplier["name"], "supplier_country": supplier["country"],
            "printing_cost": quote["printing_cost"], "shipping_cost": quote["shipping_cost"],
            "total_cost": quote["printing_cost"] + quote["shipping_cost"], "currency": quote["currency"],
            "lead_days": quote["lead_days"], "paper_finish": quote["paper_finish"],
            "valid_until": quote["valid_until"], "eligible_for_order": eligible,
            "reason": "Offre vérifiée et valide" if eligible else "Devis expiré" if expired else
                "Imprimeur à vérifier" if not verified else "Devis à valider par SOW IA"})
    return sorted(rows, key=lambda row: (not row["eligible_for_order"], row["total_cost"],
                                        row["lead_days"], row["supplier_name"].casefold()))
