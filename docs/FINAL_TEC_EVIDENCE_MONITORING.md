# FINAL TEC — Registre de preuves et suivi

**Statut : prototype de collecte en session, non fusionné et non déployé.**

## Fonctions
- Accepter un lot JSON de soumissions de preuves selon le schéma d'intake existant.
- Contrôler les champs, les catégories, les sources HTTPS et les horodatages.
- Refuser les champs inconnus, les identifiants en double dans le lot et les tentatives d'auto-approbation.
- Forcer systématiquement chaque soumission à `evidence_status=pending`, `publication_state=draft`, sans approbateur ni date de publication.
- Présenter les volumes par catégorie, l'état du registre et un historique des soumissions.
- Exporter ou effacer le registre de la session.

## Interprétation des graphiques
Le graphique par catégorie compte les soumissions présentes dans la session. Il ne mesure ni la performance technique, ni la latence, ni la disponibilité, ni le chiffre d'affaires. Les données de performance ne seront visualisées qu'après vérification indépendante et publication explicite.

## Données et sécurité
- Les enregistrements restent dans la mémoire de la session Streamlit.
- Aucune écriture Supabase, aucun appel réseau, aucune source externe récupérée.
- Aucune soumission ne peut s'auto-déclarer vérifiée ou publiée.
- Aucune donnée fictive n'est préchargée ; le JSON d'exemple est un modèle de saisie et doit être remplacé par une référence réelle avant soumission.
- Le tableau n'est pas un flux temps réel ; il reflète les soumissions de la session et les mises à jour de l'interface.

## Étape suivante avant une mise en production
Créer un circuit serveur d'approbation distinct, conserver les artefacts de preuve dans un stockage privé, tester RLS avec deux utilisateurs et journaliser les décisions de revue. Aucun investisseur ne doit accéder aux données avant la validation du contrôle d'accès et la publication autorisée.
