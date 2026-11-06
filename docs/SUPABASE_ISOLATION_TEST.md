# SOW IA — validation d’isolation Supabase (environnement de test uniquement)

## Objectif

Vérifier avec deux comptes authentifiés distincts que les fichiers du bucket privé
`sowia-private-documents` restent strictement séparés. Cette procédure complète
les tests unitaires et statiques ; elle ne les remplace pas.

## Règles de sécurité

- Créer un projet Supabase **jetable et isolé**, sans données de production.
- Ne jamais exécuter le script `supabase_optional_features.sql` dans le projet de production
  pendant cette validation.
- Utiliser deux comptes de test distincts, A et B, chacun avec son propre identifiant
  Supabase Auth.
- Ne jamais placer une clé `service_role` dans le navigateur, dans un dépôt Git,
  dans un journal ou dans les variables accessibles au client.
- Les opérations de lecture, liste, téléchargement et suppression doivent être
  effectuées avec le client authentifié de chaque utilisateur, pas avec le client admin.
- Supprimer le projet de test et les comptes de test après validation.

## Préparation

1. Créer un nouveau projet Supabase de test.
2. Créer deux utilisateurs Auth distincts (A et B) et confirmer leurs identifiants.
3. Exécuter le script SQL optionnel de SOW IA **uniquement dans ce projet isolé**.
4. Vérifier que le bucket `sowia-private-documents` est privé et que les règles RLS
   sont actives sur `storage.objects`.
5. Obtenir deux sessions utilisateur indépendantes, une pour A et une pour B.
6. Préparer deux PDF valides sans données personnelles : `A-test.pdf` et `B-test.pdf`.

## Scénario positif

- Avec la session A, téléverser `A-test.pdf` sous le préfixe de l’identifiant A.
- Avec la session B, téléverser `B-test.pdf` sous le préfixe de l’identifiant B.
- Vérifier que A peut lister et télécharger son propre PDF.
- Vérifier que B peut lister et télécharger son propre PDF.
- Vérifier que chaque téléchargement restitue exactement le contenu du PDF attendu.

## Scénario négatif obligatoire

Avec la session A, tenter séparément de :

- lister le dossier de B ;
- télécharger le chemin exact du PDF de B ;
- supprimer le chemin exact du PDF de B.

Répéter les trois tentatives depuis la session B vers le fichier de A.

**Résultat attendu :** chaque opération inter-utilisateur est refusée par Supabase
(RLS/policies) ou ne révèle aucun fichier de l’autre compte. Une réponse vide à une
liste n’est pas, à elle seule, suffisante : les tentatives de téléchargement et de
suppression doivent aussi être vérifiées. Après les tentatives, le propriétaire doit
toujours pouvoir télécharger son propre fichier.

## Vérification complémentaire des règles existantes

Le script comprend une politique restrictive qui limite le bucket privé au dossier
correspondant à `auth.uid()`, même si une autre politique permissive existe.
Vérifier dans le projet de test qu’une politique permissive préexistante n’autorise
pas A à accéder aux objets de B. Ne pas modifier les politiques d’autres buckets.

## Critères de validation

La validation est réussie uniquement si :

- A accède à son propre fichier ;
- B accède à son propre fichier ;
- A ne peut ni lister, ni télécharger, ni supprimer le fichier de B ;
- B ne peut ni lister, ni télécharger, ni supprimer le fichier de A ;
- les fichiers des deux comptes restent intacts après les tentatives interdites.

Consigner la date, le projet de test (sans secret), les identifiants de test anonymisés,
les résultats de chaque opération et les éventuelles erreurs. Ne jamais consigner de
jeton, mot de passe ou clé API.

## État actuel

Cette procédure est une préparation. Aucun projet Supabase de test n’est confirmé,
aucune requête SQL n’a été exécutée et aucune isolation réelle n’est encore certifiée.
