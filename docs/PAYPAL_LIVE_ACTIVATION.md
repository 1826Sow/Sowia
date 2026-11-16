# Activation PayPal Live — SOW IA

Cette procédure active les paiements réels uniquement après validation du code et ajout des identifiants PayPal Live. Le mode par défaut reste Sandbox et le commutateur de paiement reste désactivé par défaut.

## Paramètres Streamlit

Dans les Secrets de l'application Streamlit, après validation de la mise en production :

```toml
SOWIA_PAYMENTS_ENABLED = "true"
PAYPAL_MODE = "live"
PAYPAL_PREMIUM_PRICE = "9.90"
```

Conserver également les paramètres Supabase déjà utilisés par l'application. Ne pas y copier le secret PayPal Live.

## Secrets Supabase Edge Function

Dans Supabase > Project Settings > Edge Functions > Secrets (ou l'écran de gestion des secrets des fonctions), définir :

- `PAYPAL_MODE=live`
- `PAYPAL_LIVE_CLIENT_ID` : Client ID de l'application PayPal en mode Live
- `PAYPAL_LIVE_CLIENT_SECRET` : Secret de cette même application PayPal Live
- `SUPABASE_URL` : URL du projet Supabase
- `SUPABASE_SERVICE_ROLE_KEY` : clé service-role du projet, uniquement côté Edge Function

Les secrets Sandbox existants (`PAYPAL_CLIENT_ID` et `PAYPAL_CLIENT_SECRET`) restent distincts et ne doivent pas être remplacés par les identifiants Live.

## Ordre de mise en service

1. Fusionner le code après revue et CI réussie.
2. Déployer la version Edge Function qui prend en charge les deux environnements.
3. Ajouter les secrets PayPal Live dans Supabase Edge Functions.
4. Vérifier que le mode Streamlit et le mode Edge Function sont tous deux `live`. Le serveur refuse explicitement une divergence de mode.
5. Activer le commutateur Streamlit seulement après ces contrôles.
6. Effectuer un contrôle de bout en bout avec une commande réelle de faible montant, uniquement après validation du compte marchand PayPal et des conditions commerciales.

## Sécurité et limites

- Ne jamais transmettre un Client Secret ou une clé service-role dans cette conversation, dans GitHub, ni dans les Secrets Streamlit.
- Le montant reste fixé à 9,90 EUR et est vérifié côté serveur lors de la capture.
- L'accès Premium n'est enregistré qu'après confirmation PayPal d'une capture terminée.
- Le diagnostic de l'application ne réalise aucun paiement et ne prouve pas une capture.
- Tant que les secrets Live ne sont pas configurés et vérifiés, les paiements réels ne sont pas actifs.
