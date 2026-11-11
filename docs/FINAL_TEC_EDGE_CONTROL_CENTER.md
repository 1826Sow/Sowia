# FINAL TEC EDGE — Centre de contrôle

**Statut : interface interne de simulation, non fusionnée et non déployée.**

## Fonction
- Saisie manuelle d'un profil de tâche et d'un inventaire de ressources autorisées.
- Réglage de l'âge maximal des benchmarks (24 heures par défaut).
- Exécution du moteur EDGE local, affichage du classement, des exclusions et des motifs.
- Export du rapport de simulation en JSON.

## Données
Aucun candidat, benchmark, coût, résultat ou partenaire n'est préchargé. L'opérateur doit fournir les données et leurs références. Le moteur n'accepte comme candidats admissibles que des benchmarks déclarés `verified` et `published`, cohérents avec le profil et non périmés. Cette déclaration est une condition de filtrage, pas une certification automatique de la preuve.

## Accès
L'entrée de navigation est réservée au compte administrateur SOWIA authentifié (claim `sowia_admin=true` ou `role=admin`). Cela ne crée aucun rôle investisseur FINAL TEC et ne modifie aucune politique RLS.

## Confidentialité et sécurité
- Les saisies ne sont pas persistées et ne sont pas envoyées à Supabase.
- Aucun fichier externe n'est lu ; aucun appel réseau ou fournisseur.
- Aucun secret, jeton ou mot de passe ne doit être saisi.
- Aucun dispatch, provisionnement, réservation ou paiement.
- L'export est un rapport local de simulation et doit rester identifié comme tel.

Le centre ne constitue pas un portail investisseur ni une supervision temps réel. Une intégration de données réelles nécessitera une source serveur dédiée, des preuves validées, des contrôles d'accès isolés et des tests de sécurité.
