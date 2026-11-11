# FINAL TEC PLATFORM — modèle financier paramétrique

> Version 0.1 — modèle de travail à compléter avec des devis, données et décisions vérifiables. Aucun chiffre de financement, chiffre d'affaires, valorisation ou rendement n'est présumé.

## 1. Principes de modélisation

- Modèle mensuel sur 36 mois, avec synthèse annuelle.
- Trois scénarios : prudent, central et accéléré. Les scénarios ne sont pas des prévisions tant que leurs hypothèses ne sont pas étayées.
- Toutes les valeurs sont saisies avec devise, date, source et responsable.
- Distinguer systématiquement : signé, facturé, encaissé, engagé, estimé et hypothétique.
- Ne pas compter une subvention, un contrat, une lettre d'intention ou un investissement comme acquis avant que son statut documentaire le permette.
- Ne pas additionner les montants HT et TTC. Documenter TVA, taxes, charges et juridiction.

## 2. Registre des hypothèses

Pour chaque hypothèse, créer une ligne avec les champs suivants :

| Champ | Description |
|---|---|
| ID | Identifiant stable |
| Hypothèse | Variable ou décision modélisée |
| Valeur | Valeur saisie, ou « à renseigner » |
| Unité | EUR, USD, ETP, %, mois, unités, etc. |
| Scénario | Prudent / central / accéléré |
| Source | Devis, contrat, entretien, benchmark, estimation interne |
| Date de vérification | Date réelle de consultation |
| Confiance | Vérifiée / corroborée / provisoire / inconnue |
| Propriétaire | Personne responsable de la validation |

Aucune valeur inconnue ne doit être remplacée par une estimation silencieuse. Utiliser « à renseigner » et afficher l'impact de la donnée manquante.

## 3. Structure du modèle mensuel

### 3.1 Revenus

Ventiler par produit, client/segment et modèle de facturation :

- abonnement récurrent ;
- consommation / usage ;
- licence ;
- intégration et services ;
- support et maintenance ;
- autres revenus documentés.

Calculs indicatifs :
- Revenus récurrents mensuels = nombre de clients payants actifs × revenu mensuel moyen par client.
- Revenus à l'usage = unités facturables réellement consommées × prix unitaire validé.
- Revenus de services = jours facturables livrés × tarif journalier contractuel.
- Revenus reconnus = règles comptables applicables, à confirmer avec l'expert-comptable.

Table de suivi des revenus :

| Catégorie | Signé | Facturé | Encaissé | Pipeline pondéré | Hypothétique |
|---|---:|---:|---:|---:|---:|
| Abonnements | À renseigner | À renseigner | À renseigner | À renseigner | À renseigner |
| Usage | À renseigner | À renseigner | À renseigner | À renseigner | À renseigner |
| Licences | À renseigner | À renseigner | À renseigner | À renseigner | À renseigner |
| Services | À renseigner | À renseigner | À renseigner | À renseigner | À renseigner |

Ne jamais fusionner ces colonnes dans un unique total présenté comme chiffre d'affaires réalisé.

### 3.2 Coûts variables et marge

Lister les coûts directement liés au service : calcul/cloud, énergie, bande passante, stockage, licences tierces, composants, sous-traitance, support variable et frais de paiement.

- Coût variable total = somme des coûts variables attribuables.
- Marge brute = revenus reconnus − coûts directs associés.
- Taux de marge brute = marge brute / revenus reconnus, uniquement si les revenus sont strictement positifs et comparables.

### 3.3 Charges opérationnelles

Prévoir des lignes séparées pour :
- salaires, charges employeur et recrutement ;
- R&D, prototypes, composants et équipements ;
- cloud, logiciels, données et licences ;
- sécurité, conformité, audits et certifications ;
- propriété intellectuelle et conseil juridique ;
- ventes, marketing, déplacements et partenariats ;
- locaux, assurances, comptabilité et frais généraux.

Préciser pour chaque coût : ponctuel/récurrent, fixe/variable, quantité, coût unitaire, date de démarrage, durée, devise et source.

## 4. Trésorerie et besoin de financement

- Trésorerie de clôture = trésorerie d'ouverture + encaissements − décaissements.
- Consommation nette mensuelle de trésorerie = décaissements − encaissements, si positive.
- Autonomie de trésorerie (runway) = trésorerie disponible / consommation nette mensuelle moyenne, uniquement si la consommation nette est positive et relativement stable.
- Besoin de financement par jalon = décaissements prévus jusqu'au jalon + réserve explicitement justifiée − ressources disponibles et confirmées affectables à ce jalon.

Construire un échéancier de trésorerie avec délais de paiement clients/fournisseurs, taxes, investissements, stocks éventuels et besoin en fonds de roulement. Les montants non confirmés restent exclus de la trésorerie disponible.

## 5. Trois scénarios

| Paramètre | Prudent | Central | Accéléré |
|---|---|---|---|
| Acquisition clients | Hypothèse basse sourcée | Hypothèse centrale sourcée | Hypothèse haute justifiée |
| Prix / panier | Test ou benchmark | Test ou benchmark | Test ou benchmark |
| Conversion | Donnée mesurée ou inconnue | Donnée mesurée ou inconnue | Donnée mesurée ou inconnue |
| Coûts cloud/calcul | Devis + marge de risque | Devis | Devis + capacité supplémentaire |
| Recrutement | Équipe minimale viable | Équipe cible par jalon | Renforts conditionnels |
| Délais | Retards plausibles intégrés | Délais de référence | Accélération démontrée |
| Financement | Jalons prioritaires | Plan complet par étapes | Expansion conditionnée aux preuves |

Les différences entre scénarios doivent provenir de variables identifiées, et non d'un simple multiplicateur global.

## 6. Sensibilités obligatoires

Tester au minimum :
- coût unitaire du calcul et de l'énergie ;
- volume d'utilisation et taux d'occupation ;
- délai de conversion commerciale ;
- prix moyen et taux de renouvellement ;
- retard de livraison ou de certification ;
- hausse des coûts fournisseurs ;
- retard ou absence de financement.

Afficher les effets sur marge brute, trésorerie minimale, runway et date de franchissement de chaque jalon.

## 7. Registre des preuves financières

Pour chaque chiffre affiché dans un dossier externe, conserver :
- valeur et devise ;
- période et périmètre ;
- définition du KPI ;
- formule de calcul ;
- pièce justificative ou source ;
- date de collecte ;
- personne ayant vérifié ;
- statut : non vérifié / vérifié / audité.

Les prévisions doivent porter la mention « scénario » et afficher leurs hypothèses. Les revenus signés, facturés et encaissés sont présentés séparément.

## 8. Décisions bloquantes avant chiffrage final

- Entité juridique porteuse et pays d'établissement.
- Périmètre du premier produit et architecture technique.
- Équipe, rôles, coûts salariaux et calendrier de recrutement.
- Devis fournisseurs et besoins matériels/cloud.
- Segment client prioritaire, prix testé et cycle de vente.
- Actifs de propriété intellectuelle et licences.
- Traitement fiscal/comptable et conformité applicable.

## 9. Règles de gouvernance

Ce modèle est un outil de préparation interne, pas un conseil financier ni une offre de titres. Toute communication à des investisseurs doit être revue par des professionnels qualifiés. Aucune levée, valorisation, dilution ou promesse de rendement ne doit être publiée sans décision documentée et revue juridique appropriée.
