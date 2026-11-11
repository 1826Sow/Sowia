# FINAL TEC — matrice de préparation à une levée de fonds

**Statut : outil interne de préparation.** Ce document ne constitue pas une offre d'investissement, une sollicitation, une prévision validée ni une affirmation de maturité. Les responsables, dates, budgets et résultats inconnus restent à renseigner.

## 1. Règle de lecture

Chaque ligne doit être classée selon une preuve consultable :
- **Non commencé** : aucun livrable ni élément vérifiable.
- **En préparation** : travail documentaire ou technique en cours.
- **À vérifier** : livrable présent, mais revue ou preuve indépendante manquante.
- **Validé en interne** : critères documentés et revue interne terminée.
- **Validé indépendamment** : contrôle par une partie indépendante, avec rapport conservé.
- **Bloqué** : dépendance ou risque empêchant de progresser.

Un document rédigé ou une PR ouverte ne vaut pas validation technique, commerciale, juridique ou financière.

## 2. Matrice des conditions de préparation

| Chantier | Preuve attendue avant sollicitation sérieuse | État de départ documenté | Blocage / prochaine action |
|---|---|---|---|
| Problème et marché | Entretiens datés, besoins récurrents, segment client prioritaire, sources de marché | Cadre de validation prévu dans les documents existants | Réaliser une découverte client documentée ; ne pas confondre intérêt poli et demande payante |
| Produit initial | Périmètre MVP, parcours utilisateur, critères d'acceptation, démonstration reproductible | Spécification préliminaire existante ; statut de conception | Choisir un cas d'usage étroit et mesurer sa valeur avant élargissement |
| Architecture | Diagrammes, composants réellement implémentés, dépendances, frontières de confiance | Cadre documentaire complété dans le dossier technique | Faire correspondre le schéma aux composants présents dans le dépôt |
| Benchmarks | Tests réels autorisés, matériel identifié, protocole, résultats bruts, répétitions et revue distincte | Registre et protocole proposés dans PR #226 | Aucun résultat réel ne doit être déclaré avant exécution et vérification |
| EDGE / placement | Candidats autorisés, données comparables, décision explicable, tests de sécurité et d'échec | Moteur de sélection hors ligne proposé dans PR #227 | Valider les entrées, les unités, la fraîcheur et les cas sans ressource admissible |
| Infrastructure | Inventaire matériel, disponibilité, capacité, réseau, énergie, redondance et limites | Non démontré par les prototypes hors ligne | Obtenir des environnements de test autorisés et documenter chaque profil |
| Sécurité | Modèle de menace, gestion des secrets, moindre privilège, isolation, arrêt d'urgence, audit | Travaux de contrôle d'accès et d'audit en préparation | Exécuter les tests d'intégration réels et les revues indépendantes requises |
| Données et conformité | Cartographie des données, bases légales, contrats, rétention, transferts et responsabilités | À établir selon le cas d'usage et les juridictions | Revue juridique spécialisée avant traitement de données réelles |
| Clients et pilotes | Pilotes autorisés, objectifs, résultats, retours, conditions et statut contractuel | Aucun pilote confirmé dans les éléments consultés | Identifier des partenaires de test ; obtenir leur accord écrit avant tout usage |
| Modèle économique | Unité facturable, prix testé, coûts directs, marge contributive, hypothèses et sensibilités | Modèle paramétrique prévu dans les documents financiers existants | Renseigner avec devis, mesures et retours clients, pas avec des suppositions |
| Propriété intellectuelle | Titularité du code, licences open source, inventions, marques, contrats de cession | Inventaire complet non démontré ici | Auditer les contributions et licences ; clarifier les droits SOWIA / FINAL TEC |
| Structure juridique | Entité porteuse, gouvernance, pacte, fiscalité, responsabilités et séparation des actifs | Séparation souhaitée, formalisation à confirmer | Obtenir un avis juridique et comptable adapté avant toute opération |
| Équipe | Rôles, compétences, disponibilité, responsabilités et recrutements critiques | À documenter | Identifier les fonctions indispensables et les capacités réellement disponibles |
| Finances | Trésorerie, dépenses engagées, coûts prévisionnels sourcés, plan de trésorerie et besoin justifié | Aucun chiffre ne doit être supposé | Construire le modèle à partir des coûts réels et des scénarios explicités |
| Investisseurs | Thèse, stade, ticket indicatif public, géographie, critères et source officielle | Pistes documentaires déjà recensées dans PR #217 | Revalider chaque piste et son adéquation au stade réel ; aucun intérêt présumé |
| Dossier et communication | Présentation cohérente, annexes de preuves, risques, limites et usage des fonds | Cadre technique complété dans PR #237 ; trame antérieure dans PR #215 | Assembler uniquement après validation des éléments sous-jacents |

## 3. Portes de décision avant contact

### Porte A — crédibilité du problème
Passer uniquement lorsque le segment ciblé, le problème prioritaire et les éléments de découverte client sont documentés. Les hypothèses non testées restent étiquetées.

### Porte B — crédibilité du produit
Passer uniquement lorsqu'un MVP délimité peut être démontré dans un environnement contrôlé, avec critères d'acceptation et limites connus.

### Porte C — crédibilité technique
Passer uniquement lorsque des benchmarks réels et autorisés sont reproductibles, les coûts mesurés sont traçables et les risques de sécurité majeurs ont été traités.

### Porte D — crédibilité commerciale et financière
Passer uniquement lorsque les pilotes, contrats ou signaux de demande sont qualifiés correctement, et que le modèle financier repose sur des hypothèses explicites et des coûts sourcés.

### Porte E — préparation juridique et de gouvernance
Passer uniquement après clarification de l'entité porteuse, des droits de propriété intellectuelle, des responsabilités, des risques réglementaires et de la séparation effective avec SOWIA.

Une porte non franchie interdit de présenter le jalon comme acquis. Une discussion exploratoire peut être menée à titre informatif, mais elle doit décrire honnêtement le stade et ne pas être présentée comme une levée ouverte.

## 4. Calcul du besoin de financement

Aucun montant ne doit être fixé avant de disposer d'un plan de travail chiffré. La méthode de calcul proposée :

1. Définir les jalons financés et les critères mesurables de sortie.
2. Chiffrer les ressources humaines, infrastructure, matériel, sécurité, conformité, propriété intellectuelle, assurance et frais opérationnels.
3. Distinguer coûts ponctuels et récurrents.
4. Ajouter les marges de contingence justifiées par les risques identifiés.
5. Déduire les ressources déjà disponibles et les financements confirmés uniquement lorsqu'ils sont documentés.
6. Construire des scénarios prudent, central et ambitieux avec hypothèses, calendrier et sensibilités.
7. Calculer la trésorerie nécessaire jusqu'au prochain jalon finançable, sans présenter une durée de runway non étayée.

**Besoin de financement = coûts validés du plan de jalons + réserve de risque justifiée − ressources confirmées et disponibles.**

Les montants, la valorisation, la dilution et les conditions de financement restent à établir avec des conseils professionnels et des données réelles.

## 5. Gouvernance de la relation SOWIA / FINAL TEC

Avant toute recherche active de financement :
- déterminer quelle entité développe, détient et exploite chaque actif ;
- formaliser les licences, cessions, services partagés et refacturations éventuelles ;
- séparer comptes, trésorerie, contrats, données, accès et responsabilités ;
- tenir un registre des contributions et décisions ;
- faire approuver les communications externes par les responsables habilités.

SOWIA peut préparer des analyses et organiser des informations sur des investisseurs potentiels, mais ne doit pas promettre une introduction, une levée ou un investissement. Aucune donnée confidentielle ne doit être transmise sans autorisation.

## 6. Tableau de pilotage à compléter

| Champ | Valeur |
|---|---|
| Responsable de chaque chantier | À désigner |
| Date de référence | À renseigner à chaque revue |
| Prochaine revue | À planifier |
| MVP retenu | À décider et justifier |
| Segment client prioritaire | À valider |
| Environnement de benchmark autorisé | À obtenir |
| Budget maximal de tests | À approuver avant toute dépense |
| Entité juridique porteuse | À confirmer |
| Besoin de financement documenté | À calculer |
| Risques critiques ouverts | À tenir dans un registre versionné |

## 7. Règles de communication externe

Ne jamais annoncer comme acquis :
- un partenariat, client, contrat ou investisseur sans confirmation vérifiable ;
- une performance, capacité, économie ou disponibilité sans mesure et protocole ;
- un revenu, une valorisation ou un montant de financement sans base documentée ;
- une conformité ou certification non obtenue ;
- une concurrence technologique équivalente à un acteur établi sur la base d'une ambition seule.

Toute présentation externe doit porter une date, un statut, une source pour les faits importants et une section visible sur les limites et risques.

## 8. Dépendances documentaires

Cette matrice complète sans les remplacer :
- PR #215 : trame du dossier investisseurs ;
- PR #217 : modèle financier et cartographie des investisseurs ;
- PR #226 : protocole et registre de benchmarks ;
- PR #227 : moteur de sélection EDGE hors ligne ;
- PR #236 : protocole de validation Supabase à deux identités ;
- PR #237 : cadre du dossier technique investisseur ;
- Issue #235 : registre de preuves techniques et workflow de validation.

Ces références sont des travaux de dépôt à examiner selon leur état de revue et de fusion. Leur existence ne vaut pas déploiement ni validation opérationnelle.

## 9. Périmètre de cette étape

Document de gouvernance uniquement. Aucun investisseur n'est contacté, aucun fonds n'est sollicité, aucune dépense n'est engagée, aucun compte ou accès n'est créé, aucun test externe n'est lancé et aucune modification Supabase ou production n'est effectuée.
