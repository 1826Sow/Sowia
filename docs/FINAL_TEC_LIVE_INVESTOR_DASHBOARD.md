# FINAL TEC LIVE — Investor Dashboard (prototype V0.1)

## Objectif

Préparer un tableau de bord graphique en lecture seule pour présenter l'évolution
technique, les validations, les jalons et les éléments commerciaux vérifiables de
FINAL TEC aux investisseurs autorisés.

## État de cette version

Cette première version est une **maquette Streamlit alimentée uniquement par des
données synthétiques locales**. Elle sert à valider la structure visuelle et les
familles d'indicateurs. Elle ne mesure pas FINAL TEC et ne constitue pas une preuve
de performance, de traction commerciale, de partenariat ou de financement.

## Indicateurs prévus

- Jalons techniques : état des livrables et preuves associées.
- Tests IA / Edge : latence, disponibilité, coût par tâche et protocole de mesure.
- Feuille de route : jalons terminés, en cours, bloqués et à venir.
- Commercial : entretiens, pilotes et contrats, avec statut documentaire explicite.
- Finance : budget, dépenses engagées et prévisions, séparés et sourcés.

## Actualisation

Le terme « temps réel » ne devra être utilisé que pour les mesures qui disposent
d'une source technique réellement actualisée en continu ou à fréquence définie.
Chaque bloc devra afficher sa source, son horodatage, sa fréquence de mise à jour
et son statut de validation. Les indicateurs qui ne sont pas disponibles devront
afficher « non connecté » ou « non vérifié », jamais une valeur supposée.

## Sécurité avant accès investisseur

L'accès externe n'est pas activé dans ce prototype. Avant toute ouverture :

1. créer des comptes investisseurs explicitement autorisés ;
2. imposer la lecture seule et le moindre privilège ;
3. isoler les données FINAL TEC des données et espaces SOWIA ;
4. journaliser les connexions et consultations sensibles ;
5. exclure secrets, données personnelles, code propriétaire et informations
   commerciales confidentielles non autorisées ;
6. faire valider les chiffres et documents par un responsable humain ;
7. prévoir révocation immédiate des accès et revue périodique des droits.

## Étapes suivantes

1. Valider cette maquette visuelle.
2. Définir les sources de vérité et les propriétaires de chaque indicateur.
3. Connecter d'abord les données de tests et de jalons, en lecture seule.
4. Ajouter ensuite les données financières et commerciales validées.
5. Mettre en place l'authentification dédiée, l'autorisation investisseur et les
   journaux d'audit avant tout partage externe.

## Limites

Aucun contact investisseur, partage externe, levée de fonds, paiement, collecte de
fonds ou déploiement n'est déclenché par ce module. Toute présentation financière
ou opération de sollicitation devra faire l'objet des validations juridiques et
réglementaires applicables.


## Registre de preuves — règle de publication

Le module `final_tec_evidence.py` définit quatre états distincts :

- `verified` : source HTTPS, date ISO 8601, référence de preuve et responsable obligatoires ;
- `projected` : hypothèses et horizon obligatoires ;
- `synthetic` : étiquette explicite de démonstration obligatoire ;
- `pending` : source non encore connectée, aucune valeur ne doit être interprétée comme un résultat.

Le registre initial liste les indicateurs attendus sans leur attribuer de valeurs réelles.
Un workflow GitHub Actions ciblé exécute les tests propres au tableau de bord, séparément
des contrôles globaux actuellement bloqués par des défauts hérités de `main`.
