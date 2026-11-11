# FINAL TEC — collecte contrôlée des preuves

**Statut : module de préparation en brouillon, non fusionné et non déployé.** Cette étape prépare les éléments avant revue ; elle ne connecte pas encore un formulaire utilisateur ni une base Supabase.

## Objectif

Éviter qu'une déclaration, un fichier ou une valeur saisie par un membre de l'équipe soit automatiquement considérée comme un résultat FINAL TEC vérifié.

## Pipeline proposé

1. Un contributeur prépare une fiche avec identifiant, titre, catégorie, valeur éventuelle, unité, source, date, référence de preuve et responsable.
2. Le module `prepare_evidence_submission()` contrôle les champs, les formats, la catégorie, l'URL HTTPS, le fuseau horaire et les valeurs numériques.
3. Le module produit toujours un enregistrement `evidence_status = pending` et `publication_state = draft`.
4. Une revue humaine distincte devra vérifier la preuve, l'identité du responsable et la reproductibilité.
5. Seul un processus serveur autorisé pourra ensuite qualifier la donnée, attribuer l'approbateur et la publier.

## Protections

- Les champs inconnus sont rejetés.
- Un contributeur ne peut pas soumettre `verified`, `published`, `approved_by` ou une date de publication.
- Les catégories sont limitées aux jalons techniques, tests IA/Edge, performances, coûts, feuille de route, pilotes/partenariats.
- Les sources doivent être HTTPS valides, sans identifiants intégrés.
- Les dates doivent inclure un fuseau horaire.
- Les valeurs numériques NaN et infinies sont refusées.
- La fonction ne réalise aucune écriture réseau ni base de données.

## Hors périmètre actuel

- Pas de téléversement de pièces jointes.
- Pas de connexion à un stockage Supabase.
- Pas de processus de validation multi-personnes.
- Pas de publication d'indicateurs.
- Pas d'accès investisseur supplémentaire.
- Pas de collecte automatique de benchmarks depuis des ressources tierces.

Ces fonctions ne seront ajoutées qu'avec contrôle des permissions, conservation des preuves, journal d'audit et tests de sécurité adaptés.
