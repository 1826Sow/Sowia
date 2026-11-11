# FINAL TEC — définition du premier produit (MVP 0.1)

**Statut : proposition de cadrage à valider par étapes.** Ce document définit un produit envisagé. Il ne signifie pas que le logiciel, les connecteurs, l'inventaire de ressources ou les performances existent déjà.

## 1. Produit proposé

**Nom de travail : FINAL TEC Resource Navigator**

Un logiciel d'aide à la décision qui compare des ressources de calcul IA et Edge explicitement autorisées, puis recommande une option adaptée à un besoin donné en expliquant les critères, les données utilisées, les inconnues et les raisons d'exclusion.

Le produit vise d'abord la décision et la transparence, pas l'orchestration universelle. Il doit aider un opérateur à répondre à la question :

> Pour cette charge de travail précise, parmi les ressources que je suis autorisé à utiliser, laquelle satisfait les contraintes et présente le meilleur compromis mesuré ?

Le nom est provisoire et devra faire l'objet d'une vérification de marque et de disponibilité avant usage externe.

## 2. Problème à valider

Hypothèse : les équipes qui utilisent ou évaluent plusieurs environnements de calcul IA ont du mal à comparer de façon homogène capacité, latence, disponibilité, localisation et coût réel. Elles peuvent manquer d'une vue explicable et traçable pour choisir une ressource adaptée à une charge précise.

Cette hypothèse n'est pas une preuve de demande. Elle devra être testée auprès d'utilisateurs et d'acheteurs réels avant toute affirmation de marché.

## 3. Utilisateurs et acheteurs à étudier

Segments candidats, sans en désigner un comme client acquis :
1. équipes techniques de PME développant des applications IA ;
2. intégrateurs et sociétés de services IA ;
3. opérateurs de petits parcs de serveurs ou de nœuds Edge ;
4. équipes innovation qui évaluent plusieurs fournisseurs de calcul.

**Segment initial à sélectionner après entretiens.** Les critères de choix seront : fréquence du problème, coût actuel de la décision, accès aux décideurs, possibilité d'obtenir des données non sensibles, capacité à tester le produit et volonté de payer.

Rôles possibles :
- utilisateur : ingénieur IA, DevOps, architecte ou responsable infrastructure ;
- acheteur : direction technique, direction informatique ou responsable innovation ;
- administrateur : personne autorisée à enregistrer les ressources et règles.

Aucun segment, client, pilote ou budget client n'est considéré comme confirmé à ce stade.

## 4. Promesse produit à tester

« Comparer des ressources de calcul autorisées sur la base de critères mesurables et obtenir une recommandation explicable, avec les sources, la fraîcheur des données et les limites visibles. »

La promesse ne doit pas inclure, avant preuve :
- réduction garantie des coûts ;
- accélération garantie des traitements ;
- disponibilité ou compatibilité universelle ;
- supériorité sur NVIDIA ou un fournisseur cloud ;
- optimisation automatique en production.

## 5. Périmètre du MVP 0.1

### Inclus

1. **Inventaire contrôlé** : ajout manuel d'un petit nombre de ressources de laboratoire ou de ressources dont l'opérateur détient une autorisation explicite.
2. **Fiche ressource** : type CPU/GPU/Edge, capacité documentée, région, environnement, propriétaire/opérateur, statut d'autorisation et date de vérification.
3. **Profil de besoin** : type de charge, capacité minimale, région souhaitée, contrainte de latence et plafond de coût si un tarif vérifié est disponible.
4. **Collecte limitée** : saisie ou import de mesures documentées ; aucune découverte réseau implicite.
5. **Filtrage strict** : exclure toute ressource non autorisée, expirée, indisponible ou insuffisamment documentée.
6. **Classement explicable** : présenter les ressources admissibles et expliquer les critères appliqués.
7. **Rapport comparatif** : données, unités, date, source, statut de confiance, inconnues, limites et version de la politique.
8. **Audit** : tracer l'auteur, la date, les changements et les décisions.

### Exclu du MVP 0.1

- lancement automatique de workloads ;
- achat, réservation ou paiement de capacité ;
- déplacement automatique de charges ;
- connexion à des comptes fournisseurs ou cloud sans autorisation et intégration séparée ;
- données personnelles, confidentielles ou workloads sensibles ;
- marketplace, enchères et partage public de capacités ;
- multi-tenant commercial et accès investisseurs ;
- promesse de disponibilité de production ou SLA ;
- fabrication de matériel ou de puces.

## 6. Règles de décision

### Conditions obligatoires

Une ressource n'est candidate que si :
- son propriétaire et son périmètre d'autorisation sont identifiés ;
- l'autorisation est active et non expirée ;
- son état de disponibilité est suffisamment récent ;
- ses caractéristiques minimales sont documentées ;
- elle respecte les contraintes non négociables du profil.

Si aucune ressource ne satisfait les conditions, le produit doit répondre « aucune ressource admissible ».

### Classement

Le classement pourra utiliser, selon le profil :
- latence mesurée ;
- coût unitaire vérifié et daté ;
- disponibilité observée sur une fenêtre définie ;
- adéquation de capacité ;
- localisation et contraintes de données.

Les poids et seuils seront définis avec le cas d'usage client. Une donnée inconnue ne vaut jamais zéro et ne doit pas améliorer artificiellement le classement. Les estimations et projections sont affichées séparément des mesures.

## 7. Rôle proposé pour EDGE FINDS

Pour le premier MVP, **EDGE FINDS est envisagé comme le volet de découverte contrôlée et de qualification des ressources Edge** :
- enregistrer des nœuds connus et autorisés ;
- recueillir leurs caractéristiques déclarées et vérifiées ;
- suivre leur état et la date de dernière observation ;
- rendre leurs données comparables dans le registre.

EDGE FINDS ne sera pas présenté comme un réseau mondial de nœuds, une place de marché active ou un système de découverte automatique tant que ces fonctions ne seront pas spécifiées, développées, sécurisées et testées séparément.

## 8. Parcours utilisateur cible

1. L'administrateur crée un espace de laboratoire.
2. Il enregistre une ressource et fournit la preuve de son autorisation.
3. Il saisit ou importe ses caractéristiques et mesures avec leurs sources.
4. L'utilisateur définit un profil de charge synthétique.
5. Le système filtre les ressources non admissibles.
6. Il compare les candidates restantes selon une politique versionnée.
7. L'utilisateur consulte la recommandation, les explications et les données manquantes.
8. Il exporte un rapport d'aide à la décision.
9. Aucune charge n'est lancée et aucun paiement n'est déclenché.

## 9. Indicateurs de réussite du prototype

Les seuils numériques seront fixés avant les tests, en fonction du cas d'usage retenu. Le MVP devra démontrer :

- refus systématique d'une ressource non autorisée ;
- exclusion des mesures périmées selon une règle documentée ;
- cohérence des unités et des périodes comparées ;
- explication complète des filtres et du classement ;
- reproductibilité d'une décision avec les mêmes entrées et la même version de politique ;
- absence de sélection si aucune ressource ne satisfait les contraintes ;
- traçabilité des modifications et export du rapport ;
- comparaison à une méthode de référence (choix manuel ou règle fixe) ;
- retour utilisateur sur l'utilité et la compréhension de la recommandation.

Un gain économique ou de performance ne sera affirmé que s'il est mesuré sur un protocole adapté et reproductible.

## 10. Architecture fonctionnelle minimale

- Console de gestion d'inventaire et de profils de besoin.
- API de contrôle avec authentification et autorisations.
- Registre de ressources et preuves.
- Collecteur de mesures avec provenance et horodatage.
- Moteur de filtres et classement déterministe.
- Journal d'audit.
- Générateur de rapports.

Les interfaces fournisseurs et l'exécution de workloads sont hors périmètre initial. Chaque composant doit être relié à des fichiers réellement présents avant d'être décrit comme développé.

## 11. Plan de validation

### Étape A — découverte utilisateur
Mener des entretiens consentis avec des profils des segments candidats. Documenter le problème actuel, la méthode de choix, les coûts de décision, les contraintes de sécurité et la volonté de tester. Ne pas recueillir de données confidentielles.

### Étape B — prototype hors ligne
Utiliser des données fictives clairement marquées comme démonstration. Vérifier le filtrage, le classement, les explications et les cas d'échec. Ces résultats ne sont pas des performances réelles.

### Étape C — laboratoire autorisé
Seulement après approbation distincte : enregistrer des ressources de test dont l'usage est autorisé, exécuter des charges synthétiques non sensibles, mesurer et conserver les résultats.

### Étape D — comparaison
Comparer la recommandation à une méthode de référence sur les mêmes profils et ressources. Mesurer qualité de sélection, latence du processus décisionnel, coût observé lorsque calculable, et erreurs.

### Étape E — pilote restreint
Uniquement avec un partenaire volontaire, un périmètre écrit, une revue sécurité/juridique, un budget approuvé et un mécanisme d'arrêt. Aucun passage en production n'est implicite.

## 12. Questions produit qui restent ouvertes

- Quel segment présente le problème le plus fréquent et le plus coûteux ?
- Quelle charge de travail unique servira de premier cas de test ?
- Quelles ressources de laboratoire sont réellement disponibles et autorisées ?
- Quelles mesures peuvent être obtenues de manière fiable ?
- Quel rôle exact EDGE FINDS doit-il remplir à moyen terme ?
- Quel est le responsable de chaque volet et quelles compétences sont disponibles ?
- Quel seuil mesurable justifierait de poursuivre, pivoter ou arrêter ?

Ces questions seront résolues par preuves et décisions consignées, pas par hypothèses présentées comme des faits.

## 13. Séparation SOWIA / FINAL TEC

SOWIA peut héberger des travaux préparatoires et aider à structurer le projet. Cela ne transfère pas automatiquement à FINAL TEC le code, les données, les comptes, les contrats, la propriété intellectuelle ou les revenus de SOWIA. Toute licence, cession, prestation ou refacturation doit être formalisée et revue avant exploitation ou financement.

## 14. Conditions de passage

Ce cadrage n'autorise aucun déploiement, connexion fournisseur, achat, paiement, benchmark externe, migration, ouverture d'accès investisseur ou sollicitation financière. Chaque passage vers une étape opérationnelle nécessitera une approbation distincte définissant le périmètre, le budget maximal, les ressources, les données, les responsables, les contrôles et l'arrêt.
