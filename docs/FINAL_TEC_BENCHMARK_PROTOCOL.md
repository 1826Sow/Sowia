# FINAL TEC — protocole et registre de benchmarks IA / Edge

**Statut : prototype de validation locale, non fusionné et non déployé.** Le module ne lance pas de benchmarks et ne contacte aucun fournisseur. Il valide des observations fournies par un opérateur et calcule des statistiques descriptives.

## Objectif

Créer une base de comparaison reproductible des ressources autorisées, avant toute affirmation de performance ou décision de placement de charge.

## Fiche de benchmark minimale

Chaque essai doit identifier :
- un identifiant de benchmark et un identifiant de charge ;
- le type de charge : inference, embedding, batch, edge inference ou charge synthétique ;
- la ressource testée et sa catégorie : GPU cloud, appareil Edge, serveur privé ou CPU ;
- l'opérateur/fournisseur déclaré et la région ;
- les heures de début et de fin, avec fuseau explicite ;
- les observations de latence en millisecondes ;
- le nombre de tentatives et de succès ;
- le coût observé, la devise et la base de calcul ;
- les versions logicielles, profil matériel, référence de configuration et référence d'artefact.

Les informations doivent permettre de reproduire l'essai. Les identifiants d'artefacts doivent pointer vers des journaux ou résultats conservés dans un dépôt de preuves contrôlé. Ne pas placer de secrets, clés API, données personnelles ou données clients dans les références ou notes.

## Statistiques calculées

Le module calcule :
- latence minimale, médiane nearest-rank, p95 nearest-rank et maximale ;
- nombre d'échantillons ;
- tentatives, succès, échecs et taux de succès ;
- durée exacte de la fenêtre de test ;
- coût déclaré avec devise et base de calcul.

La médiane et le p95 sont des statistiques descriptives sur les observations reçues. Elles ne prouvent pas à elles seules la représentativité d'un test. La disponibilité calculée sur une courte fenêtre de test n'est pas un SLA.

## Règles de comparabilité

Ne comparer que des essais ayant un profil comparable :
- même charge et même version de modèle ;
- mêmes paramètres de requête, taille d'entrée/sortie et niveau de concurrence ;
- même protocole de mesure et même période de chauffe ;
- matériel et versions logicielles documentés ;
- région, réseau et conditions d'exécution explicités ;
- coût ramené à une unité commune clairement définie.

Si une dimension diffère ou manque, présenter les essais séparément et signaler la limite. Ne pas établir de classement global à partir de tests hétérogènes.

## Circuit de preuve

1. L'opérateur prépare un relevé d'essai et ses artefacts.
2. Le module contrôle le format et calcule les statistiques.
3. La soumission reste `evidence_status=pending` et `publication_state=draft`.
4. Un réviseur indépendant vérifie les journaux, la configuration, l'intégrité de l'artefact et la reproductibilité.
5. Une validation serveur distincte pourra ensuite autoriser une publication explicite.

Une saisie valide n'est pas une preuve vérifiée. Les tests unitaires du module ne prouvent pas que les mesures ont réellement été exécutées.

## Limites du prototype

- Aucun agent d'exécution ni runner distant.
- Aucun appel API vers AWS, Azure, Google Cloud ou fournisseurs Edge.
- Aucune collecte automatique de factures ou coûts.
- Aucune écriture Supabase.
- Aucun tableau de classement public.
- Aucun accès investisseur supplémentaire.
- Aucun SLA, rendement ou économie garantis.

La prochaine étape technique, après revue, sera un runner isolé et autorisé, avec quotas, budget maximal, arrêt d'urgence, journalisation et artefacts signés. Les tests sur ressources tierces nécessiteront une autorisation explicite et une configuration contrôlée.
