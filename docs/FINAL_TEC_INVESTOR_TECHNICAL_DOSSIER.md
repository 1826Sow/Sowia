# FINAL TEC — cadre du dossier technique investisseur

**Statut : document de cadrage préparatoire.** Ce document ne certifie aucune performance, ne décrit pas une infrastructure déjà déployée et ne constitue ni une offre d'investissement ni une prévision financière validée.

## 1. Objet et périmètre

Ce dossier doit permettre à un lecteur technique ou financier de distinguer :
- ce qui existe effectivement dans le dépôt ;
- ce qui est conçu mais pas encore intégré ;
- ce qui a été testé dans un environnement contrôlé ;
- ce qui a été mesuré sur du matériel réel ;
- ce qui reste une hypothèse, une simulation ou une projection.

FINAL TEC est envisagé comme une plateforme technologique autonome à terme. Tant que cette séparation n'est pas juridiquement et opérationnellement réalisée, SOWIA et FINAL TEC doivent conserver des périmètres, responsabilités, actifs, coûts, données et accès clairement distingués. Aucun actif de SOWIA ne doit être présenté comme appartenant à FINAL TEC sans décision documentée.

## 2. Architecture cible à documenter

L'architecture devra être décrite par composants, flux de données, frontières de confiance et responsabilités. Les blocs ci-dessous sont des domaines de conception, pas une affirmation qu'ils sont tous opérationnels.

1. **Plan de contrôle** : identité, autorisations, politiques de placement, quotas, plafonds de dépenses et arrêt d'urgence.
2. **Registre des ressources** : inventaire explicite des ressources autorisées, capacités déclarées, région, disponibilité observée et conditions d'utilisation.
3. **Registre des preuves** : benchmarks, journaux, configurations, artefacts, provenance, validation indépendante et historique d'audit.
4. **Moteur de sélection EDGE** : évaluation déterministe des candidats admissibles, explication des exclusions et réponse sans sélection si aucun candidat ne satisfait les contraintes.
5. **Couche d'exécution** : à concevoir séparément ; aucun lancement de charge distante ne doit être activé par simple présence d'un candidat dans l'inventaire.
6. **Observabilité** : mesures techniques, incidents, coûts, consommation énergétique et qualité de service avec horodatage et provenance.
7. **Vue investisseur** : affichage en lecture seule des seuls indicateurs validés et publiés, avec période, unité, source et statut.

Pour chaque composant, le dossier final devra fournir un schéma, les interfaces, les données traitées, les dépendances, les privilèges requis, les modes de panne et les contrôles de sécurité.

## 3. Familles de charges à évaluer

Les familles doivent être évaluées séparément. Un résultat obtenu sur une famille ne doit pas être extrapolé à une autre.

| Famille | Exemples de mesures à relever |
|---|---|
| Inférence LLM | TTFT, tokens/s, latence totale, longueur entrée/sortie, concurrence |
| Embeddings | éléments/s, latence par lot, dimension, taille du lot |
| Traitement batch | jobs/h, durée par tâche, taux d'échec, reprise |
| Inférence EDGE | latence bout-en-bout, réseau, mémoire, consommation énergétique |
| Charge synthétique | comportement sous charge artificielle, clairement étiqueté comme synthétique |

Les comparaisons doivent conserver le même modèle et sa version, le même jeu d'entrées, les mêmes paramètres, la même concurrence, le même protocole de chauffe et des conditions réseau documentées. À défaut, les résultats sont présentés séparément.

## 4. Fiche matérielle obligatoire

Chaque essai sur matériel réel doit documenter, lorsque disponible :

- fabricant, modèle exact et nombre d'accélérateurs ;
- mémoire accélérateur/VRAM et mémoire système ;
- CPU, nombre de cœurs, RAM et stockage ;
- interconnexion et réseau (débit, latence, région, type de liaison) ;
- puissance électrique mesurée, méthode et instrument ;
- système d'exploitation, pilote, runtime, bibliothèques et versions ;
- modèle IA, quantification, précision et paramètres d'exécution ;
- limites de puissance, température et éventuel throttling ;
- environnement : dédié, partagé, virtualisé ou périphérique.

Toute caractéristique inconnue doit être marquée « non renseignée », jamais estimée silencieusement.

## 5. Protocole de mesure reproductible

Pour chaque expérience :

1. Définir l'objectif, la charge, les critères d'acceptation et les seuils avant l'essai.
2. Identifier la ressource et confirmer l'autorisation d'utilisation.
3. Figer les versions, paramètres, données de test et configuration.
4. Distinguer démarrage à froid, période de chauffe et régime stabilisé.
5. Réaliser plusieurs répétitions indépendantes ; conserver les valeurs brutes.
6. Rapporter médiane, p95 et p99 lorsque la taille d'échantillon le permet, ainsi que minimum, maximum, nombre d'échantillons et taux d'échec.
7. Mesurer la durée réelle et la consommation ; préciser les outils et limites instrumentales.
8. Conserver les journaux et artefacts avec empreinte cryptographique, horodatage et identifiant de l'opérateur.
9. Faire vérifier les éléments par une personne distincte de l'opérateur.
10. Publier uniquement après validation explicite par le circuit de gouvernance.

Un échantillon court ne démontre pas une disponibilité de long terme ni un SLA. Une valeur calculée à partir de données manquantes ou simulées ne doit jamais être présentée comme une mesure réelle.

## 6. Méthode de calcul des coûts

Chaque coût doit indiquer sa devise, sa période et son unité fonctionnelle. Le dossier devra séparer :

- coût de location ou d'amortissement du matériel ;
- énergie et refroidissement ;
- réseau et transfert de données ;
- stockage ;
- licences et logiciels ;
- exploitation, supervision et maintenance ;
- coûts de disponibilité redondante et de reprise ;
- frais variables ou minimums facturés par un fournisseur.

Formules indicatives, à renseigner avec des données sourcées :

- **Coût total observé** = somme des coûts attribuables à la fenêtre de mesure.
- **Coût unitaire** = coût total observé / nombre d'unités de travail réussies.
- **Énergie par unité** = énergie mesurée en kWh / nombre d'unités réussies.
- **Marge brute indicative** = (revenu attribuable − coûts directs attribuables) / revenu attribuable.

Toute extrapolation mensuelle ou annuelle doit être identifiée comme projection, exposer ses hypothèses, son taux d'utilisation, les coûts exclus et une analyse de sensibilité. Ne pas comparer des tarifs fournisseurs sans date, région, engagement, devise et conditions contractuelles.

## 7. Indicateurs admissibles dans la vue investisseur

Un indicateur public ou investisseur doit comporter au minimum : nom, définition, unité, période, source, date de collecte, méthode, statut de validation, responsable et référence d'artefact.

Statuts à distinguer :
- `measured_pending` : observation soumise, pas encore validée ;
- `verified_not_published` : vérifiée, mais pas autorisée à l'affichage ;
- `verified_published` : vérifiée et publication explicitement autorisée ;
- `simulation` : résultat de simulation, non assimilable à une mesure ;
- `projection` : estimation prospective avec hypothèses ;
- `unavailable` : donnée absente ou insuffisante.

La vue doit afficher « données insuffisantes » plutôt que fabriquer une valeur. Elle ne doit pas mélanger mesures, simulations et projections dans une même série sans séparation visuelle et méthodologique nette.

## 8. Sécurité, gouvernance et séparation

Avant toute exécution réelle :
- autorisation écrite et périmètre précis des ressources ;
- identités distinctes et privilèges minimaux ;
- secrets conservés côté serveur, jamais dans le navigateur ni dans les journaux ;
- plafonds de dépense et de durée, quotas et coupe-circuit testés ;
- journal d'audit append-only avec contrôle d'intégrité ;
- isolation des charges et protection des données ;
- procédure d'incident, arrêt d'urgence et retour arrière ;
- revue indépendante des risques et des contrôles.

SOWIA ne doit pas pouvoir engager automatiquement des dépenses, lancer des workloads ou publier des résultats FINAL TEC sans autorisation explicite et traçable. Les données, comptes, contrats et finances doivent être séparés selon le périmètre réellement établi.

## 9. Jalons de maturité et preuves attendues

| Jalon | Preuve minimale | Ce que le jalon ne permet pas d'affirmer |
|---|---|---|
| Prototype logiciel | code revu, tests automatisés, limites documentées | performance matérielle |
| Test contrôlé | protocole, configuration, journaux et résultats reproductibles | disponibilité de production |
| Pilote autorisé | périmètre contractuel, mesures réelles, incidents et coûts | capacité à grande échelle |
| Exploitation limitée | suivi continu, sécurité revue, support et procédures | SLA général sans engagement |
| Publication investisseur | validation indépendante, provenance et autorisation de publication | rentabilité future garantie |

Chaque jalon doit avoir un propriétaire, des critères d'entrée/sortie, des risques ouverts et une décision datée. Les jalons non atteints restent explicitement « non démontrés ».

## 10. Structure du dossier final

Le dossier investisseur complet pourra être assemblé lorsque les preuves existent, dans cet ordre :

1. Résumé exécutif et statut réel du projet.
2. Architecture et frontières SOWIA / FINAL TEC.
3. Cas d'usage et familles de charges ciblées.
4. Inventaire matériel et partenaires autorisés.
5. Protocole et résultats de benchmarks reproductibles.
6. Sécurité, gouvernance, conformité et gestion des risques.
7. Modèle de coûts, hypothèses et scénarios financiers.
8. Feuille de route, dépendances et besoins de financement.
9. Registre des preuves et annexes techniques.
10. Limites, inconnues et éléments non encore démontrés.

## 11. État de préparation au moment de la rédaction

Les PR #226 et #227 proposent respectivement un registre de benchmarks et un moteur de sélection EDGE hors ligne. Elles sont des travaux en brouillon : elles ne prouvent pas qu'une infrastructure de calcul est déployée, qu'un benchmark réel a été exécuté, qu'une ressource fournisseur est connectée ou qu'un service est disponible pour des investisseurs.

Ce document est une structure de travail. Les sections de résultats, coûts, capacités, clients, revenus, partenaires et financement doivent rester vides ou porter la mention « à établir » jusqu'à réception de preuves vérifiables.

## 12. Conditions de passage à l'exécution

Le présent document n'autorise aucune action opérationnelle. Toute étape ultérieure impliquant des ressources externes devra faire l'objet d'une approbation séparée précisant le fournisseur, le compte, le budget maximal, la durée, les workloads, les données utilisées, les responsables et le mécanisme d'arrêt. Aucun test payant, déploiement, migration, publication ou accès investisseur n'est autorisé par ce document.
