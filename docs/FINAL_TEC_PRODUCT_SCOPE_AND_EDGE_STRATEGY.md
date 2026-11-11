# FINAL TEC PLATFORM — cadrage du premier produit et choix du segment d'entrée

> Version 0.1 — proposition stratégique à valider par les porteurs du projet. Les pistes ci-dessous ne décrivent pas des produits déjà construits.

## 1. Décision structurante

FINAL TEC ne doit pas commencer par promettre de « concurrencer NVIDIA » sur l'ensemble des puces, accélérateurs, systèmes et logiciels. Cette ambition à long terme couvre des marchés différents, très capitalistiques et techniquement exigeants.

La première étape doit être un produit étroit, mesurable, démontrable et vendable à un client clairement identifié. L'objectif est d'obtenir une preuve technique et commerciale avant d'élargir le périmètre.

## 2. Pistes de premier produit à évaluer

### Option A — Orchestration de ressources de calcul IA et edge

Hypothèse : une couche logicielle qui découvre, qualifie et orchestre des ressources de calcul hétérogènes (cloud, serveurs privés et nœuds edge) pour un cas d'usage défini.

Valeur à tester :
- sélectionner une ressource selon coût, latence, disponibilité, localisation des données et capacité ;
- répartir ou déplacer des charges de travail selon des règles explicites ;
- fournir visibilité sur consommation, coûts, disponibilité et performance ;
- permettre à une organisation de gérer plusieurs fournisseurs ou sites depuis une interface cohérente.

Avantages potentiels : démarrage logiciel plus progressif qu'une fabrication de puces ; possibilité de tester sur infrastructures existantes ; cohérence avec une exploration du edge computing.

Risques à traiter : dépendance aux fournisseurs, sécurité des charges et données, compatibilité matérielle, observabilité, fiabilité et différenciation face aux outils existants.

### Option B — Plateforme de services IA pour un secteur vertical

Hypothèse : une offre logicielle IA spécialisée pour un secteur et un processus précis, avec un résultat métier mesurable.

Avantages potentiels : problème client plus facile à délimiter ; possibilité de valider la volonté de payer sur un périmètre restreint.

Risques : concurrence logicielle forte, accès aux données, conformité sectorielle, coût de service et dépendance à des modèles tiers.

### Option C — Infrastructure matérielle ou accélérateur spécialisé

Hypothèse : concevoir un équipement, une carte, un accélérateur ou une architecture matérielle différenciée.

Avantages potentiels : différenciation profonde et potentiel stratégique à long terme si une innovation démontrable existe.

Risques : besoin important de capital, expertise spécialisée, propriété intellectuelle, prototypage, fabrication, chaîne d'approvisionnement, certification et cycles de développement longs. Ne pas retenir cette option comme premier jalon sans équipe, invention documentée, faisabilité et financement adaptés.

## 3. Orientation provisoire recommandée

**Piste prioritaire à instruire : Option A, orchestration logicielle de ressources IA et edge.**

Cette orientation est une hypothèse de travail, pas une décision définitive ni une preuve de faisabilité. Elle paraît constituer un point d'entrée plus progressif que la fabrication immédiate de matériel, tout en permettant d'explorer les infrastructures de calcul et l'edge.

Le premier MVP devrait se limiter à un cas d'usage unique, par exemple la sélection et le suivi d'une ressource d'exécution selon des critères mesurables. Il ne doit pas prétendre orchestrer tous les matériels, clouds ou modèles dès la première version.

## 4. Place de EDGE FINDS

Le nom « EDGE FINDS » est conservé comme initiative stratégique à clarifier. Avant de lui attribuer une fonction technique, documenter ce que le projet doit désigner :
- découverte et inventaire de nœuds edge ;
- recherche de capacités disponibles ;
- comparaison de ressources selon latence, coût et localisation ;
- mise en relation entre demandeurs et opérateurs ;
- autre fonction, à préciser.

Si EDGE FINDS concerne bien la découverte de ressources edge, il pourrait devenir un sous-ensemble ou un service complémentaire de l'option A. Ne pas annoncer cette intégration comme existante avant une spécification et un prototype.

## 5. Critères de sélection du premier segment

Noter chaque option de 1 à 5, avec preuve ou justification écrite. Une note inconnue reste « à évaluer ».

| Critère | Question de validation |
|---|---|
| Intensité du problème | Le problème est-il fréquent, coûteux et prioritaire pour un acheteur identifié ? |
| Accès au client | Peut-on rencontrer des utilisateurs et décideurs du segment ? |
| Faisabilité | L'équipe et les ressources disponibles peuvent-elles construire une démonstration ? |
| Différenciation | Existe-t-il un avantage mesurable par rapport aux alternatives ? |
| Coût de démarrage | Le prototype est-il réalisable sans infrastructure hors de portée ? |
| Délai de preuve | Peut-on mesurer un résultat en quelques cycles de développement ? |
| Modèle économique | Un acheteur comprend-il comment et pourquoi payer ? |
| Risque réglementaire/sécurité | Les obligations sont-elles identifiables et maîtrisables ? |
| Évolutivité | Le premier produit peut-il ouvrir une trajectoire plus large sans refonte totale ? |

Ne pas calculer de score final tant que les critères et les preuves ne sont pas renseignés. Une forte ambition stratégique ne compense pas une absence de client ou de faisabilité.

## 6. Définition du premier MVP si l'option A est confirmée

Périmètre initial possible :
1. enregistrer quelques ressources de calcul de test avec leurs caractéristiques vérifiées ;
2. collecter disponibilité, latence et coût selon une méthode documentée ;
3. appliquer une règle de sélection explicable ;
4. lancer une charge de test non sensible dans un environnement autorisé ;
5. comparer le résultat à une méthode de référence ;
6. produire un rapport de coût, performance et disponibilité.

Exclusions de la première version :
- fabrication ou conception de puces ;
- promesse de performance supérieure aux grands fournisseurs ;
- gestion de fonds ou achat automatique de capacités ;
- accès à des ressources tierces sans contrat et autorisation ;
- données sensibles ou charges de production avant audit sécurité ;
- compatibilité universelle annoncée sans tests.

## 7. Preuves exigées avant de parler aux investisseurs

- un segment client et un acheteur définis ;
- entretiens clients réels, consentis et synthétisés ;
- alternatives concurrentes documentées ;
- architecture et dépendances techniques ;
- prototype reproductible ;
- mesures de latence, disponibilité, coût et consommation pertinentes ;
- devis et budget par jalon ;
- équipe, responsabilités et propriété intellectuelle clarifiées ;
- intérêt commercial qualifié, séparé des contrats signés et revenus encaissés.

## 8. Décisions à consigner par les porteurs

- Option retenue et justification ;
- premier segment client ;
- problème prioritaire ;
- définition et exclusions du MVP ;
- rôle exact de EDGE FINDS ;
- ressources techniques réellement disponibles ;
- responsables et calendrier réaliste.

Tant que ces décisions ne sont pas validées, la recommandation Option A demeure une hypothèse de cadrage. Le dossier investisseurs doit conserver cette distinction.
