"""Customer request workflow for physical SOW IA VIP business cards."""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from uuid import uuid4

ORDER_STATUSES = {"requested", "quoted", "approved", "paid", "in_production", "shipped", "delivered", "cancelled"}
CURRENCIES = {"EUR", "USD", "GBP", "CHF", "CAD", "CNY", "JPY"}

def validate_vip_card_order(raw):
    if not isinstance(raw, dict):
        raise ValueError("Demande de commande invalide.")
    def clean_text(key, limit, required=True):
        value = raw.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"Le champ {key} doit être du texte.")
        value = value.strip()
        if required and not value:
            raise ValueError(f"Le champ {key} est obligatoire.")
        if len(value) > limit:
            raise ValueError(f"Le champ {key} dépasse {limit} caractères.")
        return value
    name = clean_text("cardholder_name", 100)
    company = clean_text("company", 140, False)
    destination = clean_text("destination_country", 100)
    style = clean_text("style", 40)
    if style not in {"Noir & or", "Vert & ivoire", "Bleu professionnel"}:
        raise ValueError("Style de carte non pris en charge.")
    quantity = raw.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int) or not 50 <= quantity <= 10000:
        raise ValueError("La quantité doit être comprise entre 50 et 10 000 cartes.")
    notes = clean_text("notes", 1000, False)
    return {"id": str(raw.get("id") or uuid4()), "cardholder_name": name,
            "company": company, "destination_country": destination,
            "style": style, "quantity": quantity, "notes": notes,
            "status": "requested"}
