# SOW IA — réseau international d'imprimeurs VIP

## Dépendance et activation

1. La connexion Supabase doit être active dans SOW IA.
2. Exécuter `supabase_vip_printer_network.sql` dans Supabase SQL Editor.
3. La migration est prévue après la migration de base `supabase_business_club.sql`.
4. Exécuter ensuite `supabase_vip_printer_reviews.sql` pour activer les avis.
5. Exécuter `supabase_vip_card_orders.sql` pour activer les demandes de devis et le suivi des cartes physiques.
6. Redémarrer ou recharger l'application Streamlit après les migrations.

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


## Avis et notation des imprimeurs

La migration complémentaire `supabase_vip_printer_reviews.sql` s'applique après `supabase_vip_printer_network.sql`.

- Les membres peuvent soumettre un avis sur un imprimeur déjà vérifié, avec une référence de facture ou de commande.
- Un avis reste en attente et ne contribue jamais à la note avant modération.
- Un administrateur doit contrôler la référence de commande/facture et la cohérence de l'avis avant de le publier. Le contrôle est manuel : SOW IA ne dispose pas encore d'une intégration de commande ou de facture fournisseur.
- Une seule évaluation par membre et par imprimeur est actuellement autorisée.
- La note est calculée sur 5 avec les pondérations suivantes : qualité 40 %, respect des délais 25 %, rapport qualité-prix 20 %, communication 15 %.
- Les avis rejetés et en attente sont exclus des statistiques.
- Les données publiques sont limitées aux notes par critère. L'identité du membre, la référence de commande, les notes internes et le commentaire libre restent privés.
- Un fournisseur sans avis affiche « Aucun avis vérifié » et non une note artificielle de zéro.

Les notes sont des retours clients modérés, pas une certification indépendante de qualité. Les volumes d'avis doivent toujours être affichés à côté de la moyenne.


## Demandes de devis et suivi des cartes physiques

La migration `supabase_vip_card_orders.sql` s'applique après la migration du réseau d'imprimeurs.

- Le membre transmet une demande de devis (nom, entreprise, modèle, quantité, pays et précisions) après confirmation explicite.
- La demande reste privée et son état initial est `requested`.
- Un administrateur SOW IA prépare un devis avec montant, devise et date de validité.
- Le client doit accepter lui-même le devis via une action authentifiée. L'administrateur ne peut pas accepter à sa place.
- Les transitions suivantes sont contrôlées en base : devis, acceptation client, paiement confirmé, fabrication, expédition avec référence de suivi, livraison ou annulation avant paiement.
- Le statut `paid` est une confirmation manuelle : aucun prestataire de paiement n'est relié à ce parcours.
- Aucune commande n'est envoyée automatiquement à un imprimeur et aucune fabrication/livraison réelle n'est déclenchée par ce prototype.
- Les informations de commande sont privées ; un membre ne peut lire que ses propres demandes. Les fonctions d'administration vérifient le claim serveur `app_metadata.sowia_admin = true`.

Ce module est un circuit de devis et de suivi interne. Il ne doit pas être présenté comme un service d'impression ou de livraison opérationnel tant qu'un imprimeur partenaire, un paiement, la transmission des fichiers et le suivi transporteur n'ont pas été contractualisés et intégrés.
