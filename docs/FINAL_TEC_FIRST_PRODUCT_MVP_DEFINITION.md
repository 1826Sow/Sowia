# FINAL TEC — définition du premier produit (MVP 0.1)

**Statut : proposition de cadrage à valider par étapes.** Ce document définit un produit envisagé. Il ne signifie pas que le logiciel, les connecteurs, l'inventaire de ressources ou les performances existent déjà.

## 1. Produit proposé

**Nom de travail : FINAL TEC Resource Navigator** (nom provisoire, à vérifier juridiquement et commercialement avant usage externe).

Un logiciel d'aide à la décision qui compare des ressources de calcul IA et Edge explicitement autorisées, puis recommande une option adaptée à un besoin donné en expliquant les critères, les données utilisées, les inconnues et les raisons d'exclusion.

Question centrale : pour cette charge précise, parmi les ressources que l'opérateur est autorisé à utiliser, laquelle satisfait les contraintes et présente le meilleur compromis mesuré ?

Le premier produit vise la décision et la transparence, pas l'orchestration universelle.

## 2. Problème et marché — hypothèses à tester

Hypothèse : les équipes qui évaluent plusieurs environnements de calcul IA ont des difficultés à comparer capacité, latence, disponibilité, localisation et coût réel. Il faut tester cette hypothèse auprès d'utilisateurs et d'acheteurs, sans présenter la demande comme acquise.

Segments candidats :
- équipes techniques de PME développant des applications IA ;
- intégrateurs et sociétés de services IA ;
- opérateurs de petits parcs de serveurs ou de nœuds Edge ;
- équipes innovation qui évaluent plusieurs fournisseurs de calcul.

Le segment prioritaire sera choisi après entretiens selon la fréquence et le coût du problème, l'accès aux décideurs, la possibilité de tests non sensibles et la volonté de payer. Aucun client ou pilote n'est confirmé.

## 3. Promesse à tester

« Comparer des ressources de calcul autorisées sur la base de critères mesurables et obtenir une recommandation explicable, avec les sources, la fraîcheur des données et les limites visibles. »

Ne pas promettre avant preuve : réduction garantie des coûts, accélération garantie, disponibilité universelle, supériorité sur NVIDIA ou un fournisseur cloud, optimisation automatique en production.

## 4. Périmètre du MVP 0.1

### Inclus
1. Inventaire contrôlé : petit nombre de ressources de laboratoire ou dont l'utilisation est explicitement autorisée.
2. Fiche ressource : type CPU/GPU/Edge, capacité documentée, région, environnement, propriétaire/opérateur, statut d'autorisation et date de vérification.
3. Profil de besoin : type de charge, capacité minimale, région, contrainte de latence et plafond de coût uniquement si le tarif est vérifié.
4. Collecte limitée : saisie ou import de mesures documentées ; aucune découverte réseau implicite.
5. Filtrage strict : exclure les ressources non autorisées, expirées, indisponibles ou insuffisamment documentées.
6. Classement explicable : critères, données, règles et raisons d'exclusion visibles.
7. Rapport comparatif : unités, date, source, statut de confiance, inconnues et version de politique.
8. Audit : auteur, date, changements et décisions.

### Exclu
- lancement automatique de workloads ;
- achat, réservation ou paiement de capacité ;
- déplacement automatique de charges ;
- connexion à des comptes fournisseurs sans autorisation et intégration séparée ;
- données personnelles, confidentielles ou workloads sensibles ;
- marketplace, enchères et partage public de capacités ;
- multi-tenant commercial et accès investisseurs ;
- promesse de disponibilité de production ou SLA ;
- fabrication de matériel ou de puces.

## 5. Règles de décision

Une ressource est candidate uniquement si son propriétaire et son autorisation sont identifiés, que l'autorisation est active, que sa disponibilité est assez récente et que ses caractéristiques minimales sont documentées.

Si aucune ressource ne satisfait les conditions, le système répond « aucune ressource admissible ».

Le classement peut utiliser la latence mesurée, le coût unitaire vérifié et daté, la disponibilité observée, l'adéquation de capacité et la localisation. Les poids seront définis pour le cas d'usage retenu. Une donnée inconnue ne vaut jamais zéro et ne doit pas améliorer le classement. Mesures, estimations et projections restent distinctes.

## 6. Rôle proposé pour EDGE FINDS

Pour le premier MVP, EDGE FINDS est envisagé comme le volet de découverte contrôlée et de qualification des ressources Edge : enregistrer des nœuds connus et autorisés, recueillir leurs caractéristiques, suivre leur état et rendre leurs données comparables.

Il ne sera pas présenté comme un réseau mondial, une place de marché active ou un système de découverte automatique avant spécification, développement, sécurisation et tests distincts.

## 7. Parcours utilisateur

1. L'administrateur crée un espace de laboratoire.
2. Il enregistre une ressource et fournit la preuve de son autorisation.
3. Il saisit ou importe ses caractéristiques et mesures avec leurs sources.
4. L'utilisateur définit un profil de charge synthétique.
5. Le système filtre les ressources non admissibles.
6. Il compare les candidates restantes selon une politique versionnée.
7. L'utilisateur consulte la recommandation, les explications et les données manquantes.
8. Il exporte un rapport d'aide à la décision.

Aucune charge n'est lancée et aucun paiement n'est déclenché.

## 8. Indicateurs de réussite du prototype

Les seuils numériques seront définis avant les tests. Le prototype devra démontrer :
- refus systématique d'une ressource non autorisée ;
- exclusion des mesures périmées selon une règle documentée ;
- cohérence des unités et périodes comparées ;
- explication des filtres et du classement ;
- reproductibilité à entrées et politique identiques ;
- absence de sélection si aucune ressource n'est admissible ;
- traçabilité des modifications et export du rapport ;
- comparaison avec une méthode de référence (choix manuel ou règle fixe) ;
- retour utilisateur sur l'utilité et la compréhension de la recommandation.

Tout gain économique ou de performance devra être mesuré selon un protocole reproductible.

## 9. Architecture fonctionnelle minimale

- console d'inventaire et de profils de besoin ;
- API de contrôle avec authentification et autorisations ;
- registre des ressources et des preuves ;
- collecteur de mesures avec provenance et horodatage ;
- moteur de filtres et classement déterministe ;
- journal d'audit ;
- générateur de rapports.

Les interfaces fournisseurs et l'exécution de workloads sont hors périmètre. Chaque composant devra être relié à des fichiers réellement présents avant d'être décrit comme développé.

## 10. Plan de validation

**A — Découverte utilisateur :** entretiens consentis, besoins, méthode actuelle, coûts de décision, contraintes de sécurité et volonté de tester. Ne pas recueillir de données confidentielles.

**B — Prototype hors ligne :** données fictives marquées DEMO ; vérifier filtres, classement, explications et erreurs. Ces résultats ne sont pas des performances réelles.

**C — Laboratoire autorisé :** uniquement après approbation distincte, utiliser des ressources dont l'usage est autorisé et des charges synthétiques non sensibles.

**D — Comparaison :** comparer à une méthode de référence sur les mêmes profils et ressources ; mesurer qualité de sélection, durée du processus, coûts observés lorsqu'ils sont calculables et erreurs.

**E — Pilote restreint :** uniquement avec partenaire volontaire, périmètre écrit, revue sécurité/juridique, budget approuvé et mécanisme d'arrêt.

## 11. Questions encore ouvertes

- Quel segment présente le problème le plus fréquent et le plus coûteux ?
- Quelle charge unique servira de premier cas de test ?
- Quelles ressources de laboratoire sont réellement disponibles et autorisées ?
- Quelles mesures peuvent être obtenues de manière fiable ?
- Quel rôle exact EDGE FINDS doit-il remplir à moyen terme ?
- Quels responsables et compétences sont disponibles ?
- Quel seuil mesurable justifierait de poursuivre, pivoter ou arrêter ?

Ces décisions seront fondées sur des preuves et consignées.

## 12. Séparation SOWIA / FINAL TEC

SOWIA peut héberger des travaux préparatoires. Cela ne transfère pas automatiquement à FINAL TEC le code, les données, les comptes, les contrats, la propriété intellectuelle ou les revenus de SOWIA. Toute licence, cession, prestation ou refacturation doit être formalisée et revue avant exploitation ou financement.

## 13. Conditions de passage

Ce cadrage n'autorise aucun déploiement, connexion fournisseur, achat, paiement, benchmark externe, migration, ouverture d'accès investisseur ou sollicitation financière. Toute étape opérationnelle exige une approbation distincte précisant périmètre, budget maximal, ressources, données, responsables, contrôles et mécanisme d'arrêt.
