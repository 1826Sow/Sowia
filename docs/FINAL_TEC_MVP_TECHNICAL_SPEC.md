# FINAL TEC — spécification technique préliminaire du MVP IA / Edge

> Version 0.1 — document de conception uniquement. Le prototype décrit ci-dessous n'est ni développé ni testé. Cette spécification ne constitue pas une architecture de production ni une promesse de compatibilité ou de performance.

## 1. Objectif

Démontrer en laboratoire qu'un logiciel peut :
1. enregistrer un petit ensemble de ressources de calcul explicitement autorisées ;
2. collecter et horodater leurs caractéristiques et mesures ;
3. appliquer une sélection explicable selon un profil de besoin ;
4. exécuter une charge synthétique non sensible, uniquement sur une ressource autorisée ;
5. comparer les résultats et produire un rapport traçable.

Question à valider : la sélection guidée par des mesures apporte-t-elle un bénéfice mesurable face à une sélection fixe ou manuelle pour un cas d'usage client précis ?

## 2. Périmètre et rôles

Prototype mono-organisation, environnement de laboratoire, sans comptes clients externes ni multi-tenant.

| Rôle | Autorisations |
|---|---|
| Administrateur laboratoire | Enregistrer/désactiver les ressources de test, régler les seuils |
| Opérateur | Lancer un benchmark autorisé, consulter/exporter les rapports |
| Lecteur | Consulter les résultats sans modifier |
| Collecteur | Écrire des mesures horodatées, sans modifier politiques ou autorisations |

## 3. Architecture logique

1. **Console opérateur** : inventaire, lancement de tests, lecture des rapports.
2. **API de contrôle** : authentification, validation, autorisations et orchestration.
3. **Registre des ressources** : métadonnées, capacité, état, localisation et autorisation.
4. **Collecteur de mesures** : latence, disponibilité, durée d'exécution, coût vérifié ou inconnu.
5. **Moteur de politique** : filtres obligatoires puis classement explicable.
6. **Adaptateur de test** : charges synthétiques dans des environnements explicitement autorisés.
7. **Journal d'audit** : qui a demandé quoi, sur quelle ressource, selon quelle politique et avec quel résultat.
8. **Générateur de rapports** : comparaison à une référence, limites et erreurs.

Les adaptateurs fournisseurs doivent rester séparés du moteur de décision pour limiter le couplage. Aucune découverte de réseau ou connexion à un fournisseur tiers n'est implicite.

## 4. Modèle de données minimal

### Resource
- `resource_id`, propriétaire/opérateur, environnement, région ;
- type (CPU/GPU/autre explicitement pris en charge), profil de capacité et source ;
- disponibilité (disponible/indisponible/inconnue) ;
- autorisation (active/suspendue/expirée/inconnue) ;
- coût et devise si vérifiés, sinon `unknown` ;
- date de dernière vérification.

### Measurement
- identifiant, ressource, métrique, valeur, unité ;
- horodatage, version de méthode, profil de test, nombre d'échantillons ;
- source, statut de confiance, erreurs et limites.

### WorkloadProfile
- identifiant/version, type de charge synthétique, durée maximale ;
- capacité minimale, latence, région et disponibilité requises ;
- sensibilité : le MVP accepte uniquement des données et charges synthétiques non sensibles.

### SelectionDecision / BenchmarkRun
- profil, candidates, filtres et règles appliqués ;
- mesures utilisées avec âge et provenance ;
- décision ou motif d'absence de sélection ;
- version de politique, demandeur, autorisation, paramètres, durée, statut ;
- résultats bruts, erreurs, coût calculé ou marqué inconnu, rapport associé.

Ne jamais stocker de clés fournisseur, secrets ou jetons dans ces enregistrements ni dans les journaux.

## 5. Pipeline fonctionnel

1. L'administrateur enregistre une ressource et précise propriétaire, portée d'autorisation et expiration.
2. Le contrôle refuse toute autorisation absente, inconnue, expirée ou suspendue.
3. Le collecteur mesure, horodate et conserve la méthode.
4. Le moteur élimine les ressources incompatibles ou dont les mesures sont trop anciennes.
5. Les ressources admissibles sont classées selon une politique versionnée et explicable.
6. L'opérateur confirme explicitement la ressource avant exécution.
7. Le benchmark synthétique est exécuté dans les limites prévues.
8. Un rapport compare les résultats à une référence.

Si aucune ressource n'est admissible, le système répond « aucune ressource admissible » : il ne choisit pas une option non conforme.

## 6. Sélection explicable

**Filtres obligatoires :** autorisation active, disponibilité récente, type/capacité compatibles, région conforme, mesures suffisamment récentes. Un plafond de coût ne peut être appliqué que si le tarif est fiable, daté et vérifié.

**Classement :** dimensions possibles : latence observée, coût unitaire vérifié, disponibilité observée, adéquation de capacité. Les poids doivent être configurés pour un cas d'usage, justifiés et versionnés. Une donnée inconnue n'est jamais assimilée à zéro ou à une valeur favorable. Le rapport explique les éliminations et le classement.

Le MVP ne réalise aucun achat, réservation payante ou déplacement automatique de charge.

## 7. Interfaces conceptuelles

Les routes ci-dessous sont des contrats de conception, pas des API existantes :
- `POST /lab/resources` — enregistrer une ressource ;
- `GET /lab/resources` — consulter l'inventaire selon les droits ;
- `POST /lab/resources/{id}/measurements` — soumettre une mesure ;
- `POST /lab/selections` — calculer une sélection ;
- `POST /lab/benchmarks` — demander un test après contrôle d'autorisation ;
- `GET /lab/benchmarks/{id}` — consulter statut et résultats ;
- `GET /lab/reports/{id}` — consulter un rapport.

Chaque requête doit être authentifiée, autorisée, validée et journalisée. Les erreurs ne doivent révéler aucun secret ou détail de ressources non accessibles.

## 8. Sécurité et confidentialité minimales

- Liste d'autorisation explicite ; aucun scan réseau ni découverte non sollicitée.
- Authentification et contrôle d'accès par rôle ; moindre privilège.
- Isolation du plan de contrôle et des environnements d'exécution.
- Données et charges synthétiques uniquement.
- Quotas de durée, CPU/GPU, mémoire et nombre de tests.
- Arrêt d'urgence et désactivation immédiate d'une ressource.
- Journal d'audit protégé contre les modifications ordinaires.
- Communications chiffrées et coffre à secrets si des connexions authentifiées sont ajoutées.
- Règles de conservation/suppression définies avant toute donnée personnelle.
- Revue des licences, contrats, dépendances et propriété intellectuelle.
- Aucun partage externe sans approbation explicite.

## 9. Protocole de benchmark

Pour chaque profil : documenter matériel, logiciel, version, région et configuration ; fixer une charge synthétique ; effectuer des répétitions selon une méthode constante ; mesurer latence (médiane et percentiles), durée, disponibilité et consommation pertinente ; calculer le coût seulement avec un tarif vérifié et daté ; exécuter une référence fixe dans des conditions comparables ; conserver les échecs et valeurs aberrantes.

Le nombre de répétitions, les seuils et métriques finales seront arrêtés dans un protocole séparé adapté au segment client. Aucune performance n'est présumée ici.

## 10. Critères d'acceptation

- Une ressource non autorisée est systématiquement refusée.
- Une ressource dont les mesures sont périmées est exclue ou signalée.
- Le moteur explique les critères d'élimination et le classement.
- Une décision est reproductible avec la même politique et les mêmes mesures.
- Un benchmark synthétique ne s'exécute que sur une ressource autorisée.
- Résultats, erreurs et provenance sont traçables.
- Le rapport distingue mesures observées, données déclarées, estimations et inconnues.
- L'arrêt d'urgence empêche tout nouveau test.
- Aucun achat ni paiement ne peut être déclenché.

## 11. Étapes de réalisation

| Étape | Livrable | Condition de passage |
|---|---|---|
| 0 — cadrage | Segment, problème, profil de charge, ressources autorisées | Problème et périmètre approuvés |
| 1 — simulation | Registre fictif, règles, résultats simulés | Règles et explications vérifiables |
| 2 — laboratoire | Collecteur et benchmarks synthétiques contrôlés | Mesures reproductibles, autorisations démontrées |
| 3 — comparaison | Référence fixe, rapports coût/performance | Bénéfice mesuré ou décision de pivot |
| 4 — pilote restreint | Pilote non sensible avec partenaire autorisé | Revue juridique/sécurité et accord explicite |

Aucun calendrier ou budget n'est fixé sans connaître l'équipe et les ressources disponibles.

## 12. Décisions à prendre

- Segment client et acheteur.
- Premier cas d'usage et profil de charge.
- Ressources de laboratoire réellement disponibles et autorisées.
- Technologies et hébergement adaptés aux compétences de l'équipe.
- Fonction exacte de EDGE FINDS.
- Métriques et seuils de réussite.
- Responsables technique, sécurité et propriété intellectuelle.

**Conclusion :** ce document décrit un prototype possible et ses garde-fous. Il ne prouve ni l'existence d'un prototype, ni une performance, ni une demande client, ni un avantage concurrentiel.