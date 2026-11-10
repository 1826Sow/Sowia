# SOW IA — réseau international d'imprimeurs VIP

## Dépendance et activation

1. La connexion Supabase doit être active dans SOW IA.
2. Exécuter `supabase_vip_printer_network.sql` dans Supabase SQL Editor.
3. La migration est prévue après la migration de base `supabase_business_club.sql`.
4. Redémarrer ou recharger l'application Streamlit après l'application de la migration.

La migration n'est pas exécutée par le code Python. Tant qu'elle n'a pas été appliquée, l'interface affiche une alerte de configuration et aucune donnée n'est enregistrée dans les nouvelles tables.

## Rôles et confidentialité

- Un membre authentifié peut proposer un imprimeur. Son statut initial est toujours `candidate`.
- Un membre peut saisir un devis reçu. Son statut initial est toujours `received`.
- Un membre peut consulter ses propres candidats et devis.
- Les membres peuvent consulter les imprimeurs dont le statut est `verified`.
- Les devis des autres membres ne sont visibles que si l'imprimeur est vérifié, le devis validé et sa date de validité non dépassée.
- Aucun membre ne peut modifier les statuts d'approbation avec les permissions SQL ordinaires.
- L'onglet d'administration est affiché uniquement si le compte possède le claim serveur `app_metadata.sowia_admin = true`. Les fonctions SQL vérifient ce même claim dans le JWT à chaque action. Cette métadonnée doit être attribuée uniquement par un administrateur de confiance via l'interface d'administration Supabase ou un processus serveur sécurisé. Ne jamais la placer dans `user_metadata`, dans le code client, ni dans un formulaire public. Les administrateurs peuvent examiner, valider, maintenir en attente ou suspendre un fournisseur et un devis.

## Comparaison

La comparaison n'inclut que les devis correspondant exactement au pays de livraison, à la quantité et à la devise choisis. Le total est le prix d'impression plus la livraison. Aucune conversion de devise n'est appliquée. Les devis expirés ne peuvent pas être admissibles à une commande.

## Limites actuelles

- Pas encore de découverte automatique ni de vérification externe des imprimeurs.
- Pas de conversion de devises en temps réel.
- Pas de commande, paiement, transmission de fichiers d'impression ni suivi transporteur.
- L'éligibilité affichée est un contrôle de données et d'approbation, pas une garantie contractuelle de disponibilité ou de livraison.

Avant toute commande réelle, SOW IA doit contrôler l'identité du fournisseur, les échantillons, la qualité, les prix finaux, les taxes, les délais, la politique de confidentialité et les conditions de livraison.
