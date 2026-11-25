"""Streamlit interface for the global NIGHT EXCHANGE virtual stock market."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import uuid


def _rows(response):
    return getattr(response, "data", None) or []


def _rpc(client, name, params=None):
    return client.rpc(name, params or {}).execute().data


def _money(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def render(client, user):
    """Render a worldwide, simulation-only limit-order market for approved apps."""
    import streamlit as st

    st.markdown("### 🌍 Bourse mondiale des applications")
    st.caption(
        "Un marché international unique : les applications approuvées sont cotées par symbole, "
        "et les ordres sont exécutés selon le prix puis l'ancienneté."
    )
    st.warning(
        "SIMULATION UNIQUEMENT — NXC est un crédit virtuel sans valeur monétaire, "
        "non convertible et non remboursable. Aucun paiement ni titre réel."
    )
    if client is None or user is None or not getattr(user, "id", None):
        st.info("Connectez-vous pour accéder au marché mondial simulé.")
        return

    try:
        wallet = _rpc(client, "sowia_nex_ensure_wallet") or {}
        if isinstance(wallet, list):
            wallet = wallet[0] if wallet else {}
    except Exception as exc:
        st.error("Le portefeuille de simulation n'est pas encore initialisé.")
        st.caption("Diagnostic : " + type(exc).__name__ + ". Vérifiez les migrations NIGHT EXCHANGE.")
        return

    balance = _money(wallet.get("balance", 0))
    reserved = _money(wallet.get("reserved_balance", 0))
    metrics = st.columns(3)
    metrics[0].metric("Disponible", f"{balance:,.2f} NXC")
    metrics[1].metric("Réservé aux ordres", f"{reserved:,.2f} NXC")
    metrics[2].metric("Total virtuel", f"{balance + reserved:,.2f} NXC")

    try:
        listings = _rows(
            client.table("sowia_nex_share_classes")
            .select("id,application_id,ticker,total_shares,shares_float,initial_price,last_price,status")
            .eq("status", "listed").order("ticker").limit(500).execute()
        )
        approved_apps = _rows(
            client.table("sowia_night_exchange_apps")
            .select("id,app_name,country")
            .eq("user_id", str(user.id)).eq("status", "approved")
            .order("app_name").limit(200).execute()
        )
        public_apps = _rows(
            client.table("sowia_night_exchange_apps")
            .select("id,app_name,country")
            .eq("status", "approved").order("app_name").limit(500).execute()
        )
    except Exception as exc:
        st.error("Le registre de cotation mondiale est momentanément inaccessible.")
        st.caption("Diagnostic : " + type(exc).__name__)
        return

    public_app_by_id = {str(item["id"]): item for item in public_apps}
    for item in listings:
        app = public_app_by_id.get(str(item["application_id"]), {})
        item["_app_name"] = app.get("app_name") or "Application approuvée"
        item["_country"] = app.get("country") or "International"

    market_tab, book_tab, portfolio_tab, listing_tab = st.tabs(
        ["🌐 Cours mondiaux", "📊 Carnet & ordres", "💼 Portefeuille", "🚀 Coter une application"]
    )

    with market_tab:
        st.markdown("#### Cotations internationales")
        st.caption("Les cours évoluent uniquement après une transaction simulée exécutée.")
        if not listings:
            st.info("Aucune application n'est encore cotée. Les premières cotations apparaîtront après validation des dossiers.")
        else:
            for start in range(0, len(listings), 2):
                cols = st.columns(2)
                for col, item in zip(cols, listings[start:start + 2]):
                    with col:
                        with st.container(border=True):
                            st.markdown(f"**{item['ticker']} · {item['_app_name']}**")
                            st.caption(item["_country"] + " · Marché mondial")
                            values = st.columns(2)
                            values[0].metric("Dernier cours", f"{_money(item['last_price']):,.4f} NXC")
                            values[1].metric("Capitalisation simulée", f"{_money(item['last_price']) * int(item['total_shares']):,.2f} NXC")
                            st.caption(
                                f"Flottant : {int(item['shares_float']):,} / "
                                f"{int(item['total_shares']):,} actions virtuelles"
                            )

    with book_tab:
        if not listings:
            st.info("Le carnet sera disponible dès la première cotation.")
        else:
            labels = {
                f"{item['ticker']} · {item['_app_name']} · {_money(item['last_price']):,.4f} NXC": item
                for item in listings
            }
            selected_label = st.selectbox("Valeur à consulter", list(labels), key="nex_global_book_symbol")
            selected = labels[selected_label]
            left, right = st.columns(2)
            try:
                book = _rows(_rpc(client, "sowia_nex_get_order_book", {
                    "p_share_class_id": selected["id"]
                }))
                buys = [row for row in book if row.get("side") == "buy"]
                sells = [row for row in book if row.get("side") == "sell"]
                with left:
                    st.markdown("**Meilleurs achats**")
                    if buys:
                        for row in buys[:10]:
                            st.write(f"{_money(row['limit_price']):,.4f} NXC  ·  {int(row['quantity']):,} actions")
                    else:
                        st.caption("Aucun ordre acheteur ouvert.")
                with right:
                    st.markdown("**Meilleures ventes**")
                    if sells:
                        for row in sells[:10]:
                            st.write(f"{_money(row['limit_price']):,.4f} NXC  ·  {int(row['quantity']):,} actions")
                    else:
                        st.caption("Aucun ordre vendeur ouvert.")
            except Exception as exc:
                st.error("Impossible de charger le carnet d'ordres.")
                st.caption("Diagnostic : " + type(exc).__name__)

            st.divider()
            st.markdown("#### Passer un ordre à cours limité")
            order_request_id = st.session_state.setdefault("nex_global_order_request_id", str(uuid.uuid4()))
            with st.form("nex_global_limit_order", clear_on_submit=True):
                side_label = st.radio("Sens", ["Acheter", "Vendre"], horizontal=True)
                quantity = st.number_input("Quantité d'actions virtuelles", min_value=1, max_value=1000000, value=1, step=1)
                limit_price = st.number_input(
                    "Prix limite (NXC par action)", min_value=0.0001, max_value=1000000.0,
                    value=float(_money(selected["last_price"])), step=0.01, format="%.4f"
                )
                submitted = st.form_submit_button("Envoyer l'ordre")
            if submitted:
                try:
                    order_id = _rpc(client, "sowia_nex_submit_limit_order", {
                        "p_share_class_id": selected["id"],
                        "p_side": "buy" if side_label == "Acheter" else "sell",
                        "p_quantity": int(quantity),
                        "p_limit_price": str(limit_price),
                        "p_client_order_id": order_request_id,
                    })
                    st.session_state.pop("nex_global_order_request_id", None)
                    st.success("Ordre enregistré. Les exécutions éventuelles sont comptabilisées dans le portefeuille virtuel.")
                    st.rerun()
                except Exception as exc:
                    st.error("L'ordre n'a pas été accepté.")
                    st.caption(str(exc)[:400])

            try:
                tape = _rows(_rpc(client, "sowia_nex_get_market_tape", {
                    "p_share_class_id": selected["id"], "p_limit": 15
                }))
                with st.expander("Dernières transactions simulées"):
                    if not tape:
                        st.caption("Aucune transaction exécutée pour cette valeur.")
                    else:
                        for trade in tape:
                            st.write(
                                f"{str(trade.get('executed_at',''))[:16].replace('T',' ')} UTC · "
                                f"{_money(trade['execution_price']):,.4f} NXC · "
                                f"{int(trade['quantity']):,} actions · "
                                f"{_money(trade['gross_value']):,.2f} NXC"
                            )
            except Exception:
                st.caption("Historique des transactions indisponible.")

    with portfolio_tab:
        st.markdown("#### Mes positions")
        try:
            positions = _rows(
                client.table("sowia_nex_positions")
                .select("share_class_id,quantity,reserved_quantity,updated_at")
                .eq("user_id", str(user.id)).gt("quantity", 0).order("updated_at", desc=True).limit(200).execute()
            )
            if not positions:
                st.info("Aucune action virtuelle détenue pour le moment.")
            else:
                share_map = {str(item["id"]): item for item in listings}
                for position in positions:
                    share = share_map.get(str(position["share_class_id"]), {})
                    st.write(
                        f"**{share.get('ticker','Valeur')}** · "
                        f"{int(position['quantity']):,} actions · "
                        f"{int(position['reserved_quantity']):,} réservées"
                    )
        except Exception as exc:
            st.error("Les positions ne sont pas accessibles.")
            st.caption("Diagnostic : " + type(exc).__name__)

        st.markdown("#### Mes ordres ouverts")
        try:
            orders = _rows(
                client.table("sowia_nex_orders")
                .select("id,share_class_id,side,quantity,remaining_quantity,limit_price,status,created_at")
                .eq("user_id", str(user.id))
                .in_("status", ["open", "partially_filled"])
                .order("created_at", desc=True).limit(100).execute()
            )
            share_map = {str(item["id"]): item for item in listings}
            if not orders:
                st.caption("Aucun ordre ouvert.")
            for order in orders:
                share = share_map.get(str(order["share_class_id"]), {})
                st.write(
                    f"{share.get('ticker','Valeur')} · {order['side']} · "
                    f"{int(order['remaining_quantity']):,}/{int(order['quantity']):,} · "
                    f"{_money(order['limit_price']):,.4f} NXC"
                )
                if st.button("Annuler", key=f"nex_cancel_{order['id']}"):
                    try:
                        _rpc(client, "sowia_nex_cancel_order", {"p_order_id": order["id"]})
                        st.success("Ordre annulé ; les réserves restantes ont été restituées.")
                        st.rerun()
                    except Exception as exc:
                        st.error("Annulation impossible.")
                        st.caption(str(exc)[:300])
        except Exception as exc:
            st.error("Les ordres personnels ne sont pas accessibles.")
            st.caption("Diagnostic : " + type(exc).__name__)

    with listing_tab:
        st.markdown("#### Introduire une application sur la Bourse mondiale")
        st.caption(
            "Seules vos applications déjà approuvées par la modération peuvent être cotées. "
            "Une application ne peut être introduite qu'une fois dans cette version."
        )
        already_listed = {str(item["application_id"]) for item in listings}
        eligible = [item for item in approved_apps if str(item["id"]) not in already_listed]
        if not eligible:
            st.info("Aucune application approuvée et non cotée n'est disponible.")
        else:
            options = {
                f"{item['app_name']} · {item.get('country') or 'International'}": item
                for item in eligible
            }
            with st.form("nex_global_issue_form", clear_on_submit=True):
                selected_app_label = st.selectbox("Application à coter", list(options))
                ticker = st.text_input("Symbole boursier mondial (2 à 10 caractères)", max_chars=10).upper().strip()
                total_shares = st.number_input("Nombre total d'actions virtuelles", min_value=1, max_value=1000000000, value=1000000, step=1000)
                float_shares = st.number_input("Actions mises en circulation", min_value=1, max_value=1000000000, value=250000, step=1000)
                initial_price = st.number_input("Cours initial simulé (NXC)", min_value=0.0001, max_value=1000000.0, value=1.0, step=0.01, format="%.4f")
                issue = st.form_submit_button("Coter sur le marché mondial")
            if issue:
                if not ticker or len(ticker) < 2 or not ticker.isalnum():
                    st.error("Le symbole doit contenir 2 à 10 caractères A-Z ou 0-9.")
                elif float_shares > total_shares:
                    st.error("Le flottant ne peut pas dépasser le nombre total d'actions.")
                else:
                    try:
                        app = options[selected_app_label]
                        _rpc(client, "sowia_nex_issue_shares", {
                            "p_application_id": app["id"], "p_ticker": ticker,
                            "p_total_shares": int(total_shares),
                            "p_shares_float": int(float_shares),
                            "p_initial_price": str(initial_price),
                        })
                        st.success("Application cotée en simulation sur le marché mondial.")
                        st.rerun()
                    except Exception as exc:
                        st.error("La cotation n'a pas été créée.")
                        st.caption(str(exc)[:400])

    st.caption(
        "Mécanisme de démonstration : commission simulée de 2 % sur l'acheteur, "
        "répartie 60 % SOW IA / 25 % réserve / 15 % écosystème. "
        "Ce paramètre n'est pas un tarif commercial réel approuvé."
    )
