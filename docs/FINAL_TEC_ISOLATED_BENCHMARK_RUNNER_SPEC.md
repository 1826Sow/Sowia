# FINAL TEC — conception du runner de benchmark isolé

**Statut : spécification de conception uniquement.** Ce document ne crée pas de runner exécutable, ne lance aucun benchmark et n'autorise aucun accès à une infrastructure tierce.

## 1. Objectif et périmètre

Définir un futur composant d'exécution contrôlée pour produire des mesures IA / Edge reproductibles, traçables et vérifiables avant toute comparaison ou publication.

Le runner devra rester distinct de SOWIA sur les plans technique, opérationnel, financier et juridique. Il ne devra pas être intégré à un flux de production SOWIA sans décision d'architecture et validation séparées.

### Hors périmètre explicite à ce stade

- Aucun workload réel ou payant.
- Aucun appel à AWS, Azure, Google Cloud, fournisseur GPU ou opérateur Edge.
- Aucun provisioning, achat, réservation ou paiement.
- Aucune collecte automatique de factures, clés ou données client.
- Aucune écriture Supabase, publication ou exposition aux investisseurs.
- Aucun accès réseau sortant par défaut.

## 2. Architecture cible en couches

1. **Orchestrateur de demande** : reçoit une demande signée/identifiée, contrôle son statut d'autorisation et vérifie les limites avant toute préparation.
2. **Policy gate fail-closed** : refuse si une autorisation, une limite, un profil de charge ou une ressource manque, est expiré ou incohérent.
3. **Pré-validateur** : valide le manifeste, les paramètres, les unités, les versions et la compatibilité du profil.
4. **Environnement isolé** : exécution dans un conteneur ou bac à sable éphémère, utilisateur non privilégié, système de fichiers temporaire et limites OS.
5. **Collecteur local** : recueille uniquement les métriques prévues dans le manifeste et les journaux techniques autorisés.
6. **Normaliseur** : produit une fiche compatible avec `final_tec_benchmark.py`, toujours `pending/draft`.
7. **Coffre de preuves** : destination privée, accès minimal, empreintes et historique append-only ; aucune publication automatique.

Le runner ne décide jamais seul qu'une preuve est vérifiée. La revue indépendante et le mécanisme serveur de publication restent séparés.

## 3. Manifeste d'exécution obligatoire

Chaque exécution future devra référencer un manifeste immuable comprenant au minimum :

- `run_id`, `benchmark_id`, version du manifeste et empreinte SHA-256 ;
- identité de l'opérateur et référence de l'approbation ;
- workload, modèle, version, paramètres, tailles d'entrée/sortie et concurrence ;
- ressource autorisée, matériel, région et fournisseur déclaré ;
- durée maximale, nombre maximal de requêtes et volume maximal de données ;
- budget plafond, devise, base de coût et source du tarif ;
- fenêtre de chauffe, répétitions et protocole statistique ;
- métriques autorisées et seuils d'arrêt ;
- références des artefacts attendus et politique de conservation.

Les secrets ne doivent jamais être inscrits dans le manifeste, les logs ou les artefacts. Les références de secrets, si un besoin futur est approuvé, doivent être résolues côté serveur depuis un coffre dédié, avec portée minimale et durée de vie courte.

## 4. Contrôles de sécurité obligatoires

### Isolation

- Processus non privilégié ; aucune capacité d'administration.
- Conteneur ou bac à sable éphémère, image épinglée par digest.
- Système de fichiers en lecture seule hors répertoire temporaire dédié.
- Limites CPU, mémoire, processus, stockage et bande passante.
- Aucun montage de socket Docker, répertoire hôte sensible ou fichier d'identité cloud.
- Nettoyage contrôlé à la fin, avec conservation séparée des seuls artefacts autorisés.

### Réseau

- Réseau désactivé par défaut.
- Aucune résolution DNS ni sortie Internet implicite.
- Toute exception future devra définir une allowlist de destinations, ports, protocoles, durée et volume, approuvée avant exécution.
- Refus des destinations arbitraires, adresses locales/métadonnées cloud et redirections hors allowlist.

### Budget et arrêt

- Budget maximal strict, calculé avant démarrage et contrôlé pendant l'exécution.
- Arrêt immédiat si le plafond est atteint, si le tarif est inconnu ou si le coût ne peut plus être estimé.
- Timeout global, limite de requêtes, limite de répétitions et coupe-circuit.
- Arrêt d'urgence indépendant de l'interface utilisateur.
- Aucune relance automatique après un arrêt de sécurité.

### Données et journaux

- Pas de données personnelles, secrets, données clients ou prompts confidentiels dans les tests par défaut.
- Redaction des journaux et validation des formats de sortie.
- Artefacts limités à une taille et un type autorisés.
- Les logs distinguent les événements observés, les valeurs déclarées et les erreurs du runner.

## 5. Machine à états

Les transitions doivent être explicites et auditées :

`draft → submitted → authorized → prepared → running → completed → pending_review`

États terminaux ou de blocage :

- `rejected` : politique ou autorisation non satisfaite ;
- `aborted` : arrêt manuel ou d'urgence ;
- `timed_out` : durée maximale dépassée ;
- `budget_exceeded` : plafond atteint ;
- `failed` : erreur technique.

Aucun état d'exécution ne peut directement produire `verified` ou `published`. Une revue indépendante est nécessaire.

## 6. Résultat et intégrité

Le résultat devra contenir :

- manifeste et version du runner ;
- dates UTC de début et fin ;
- statut final et raison d'arrêt le cas échéant ;
- métriques brutes et statistiques calculées ;
- ressources et versions réellement observées ;
- coût observé avec devise, unité et source ;
- empreintes SHA-256 des fichiers et du relevé normalisé ;
- journaux d'événements et références d'artefacts.

Une empreinte SHA-256 détecte une différence de contenu lorsqu'elle est recalculée et comparée ; elle ne prouve ni l'identité de l'opérateur, ni l'exécution réelle, ni l'absence de falsification. Une signature numérique future devra utiliser une identité de service contrôlée et une clé protégée côté serveur.

## 7. Plan de réalisation par portes de validation

| Porte | Livrable | Autorisation requise |
|---|---|---|
| G0 | Tests unitaires du manifeste, policy gate et machine à états avec fixtures locales | Travail hors ligne |
| G1 | Bac à sable local sans réseau, charges synthétiques non coûteuses | Validation technique |
| G2 | Tests de limites CPU/mémoire/temps et arrêt d'urgence | Validation sécurité |
| G3 | Signature et dépôt privé des artefacts, accès restreint | Approbation sécurité et architecture |
| G4 | Essai sur ressource réelle explicitement autorisée | Approbation écrite, budget plafonné et fournisseur choisi |
| G5 | Revue indépendante et publication contrôlée | Approbation reviewer distincte |

Chaque porte doit produire des résultats reproductibles, des journaux et une décision documentée. L'échec d'une porte bloque la suivante.

## 8. Critères d'acceptation avant toute exécution réelle

- Refus vérifié par défaut si le réseau, la ressource ou le budget ne sont pas explicitement autorisés.
- Tests démontrant l'impossibilité de dépasser les plafonds configurés.
- Arrêt d'urgence testé et journalisé.
- Absence de secrets dans les journaux et artefacts.
- Reproductibilité documentée sur fixtures locales.
- Séparation effective entre opérateur, réviseur et publication.
- Aucun indicateur investisseur alimenté par des simulations ou des données non vérifiées.

## 9. Décisions encore ouvertes

Ne pas choisir ou activer de fournisseur, d'instance, de matériel, de tarif, de région, de runner hébergé ou de service de stockage sans décision explicite. Les besoins de conformité, de propriété intellectuelle, de conservation et d'assurance devront être examinés avant G4.

**État actuel : spécification proposée. Aucun runner n'est construit, aucune exécution n'est autorisée et aucun coût n'a été engagé.**
