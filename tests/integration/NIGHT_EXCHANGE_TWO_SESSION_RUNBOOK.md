# NIGHT EXCHANGE — parcours de validation avec deux sessions réelles

## Objet et périmètre

Ce protocole complète les tests SQL transactionnels exécutés sur le projet isolé **SOWIA - TEST**. Il valide le parcours applicatif avec deux sessions Supabase réellement authentifiées. Il ne remplace pas les tests de concurrence multi-connexion.

**Ne jamais utiliser la production pour ce protocole.** Ne pas copier de mots de passe, jetons JWT, clés API ou cookies dans GitHub, les journaux, les captures d'écran ou une conversation.

## Préconditions bloquantes

- L'application et les quatre migrations NIGHT EXCHANGE sont déployées uniquement sur le projet TEST dédié.
- Deux comptes de test distincts A et B existent dans Supabase Auth.
- Les deux comptes possèdent chacun une application professionnelle approuvée et un accès Premium actif dans le projet TEST.
- Un troisième compte C, sans participation au contrat, est disponible pour le contrôle d'accès négatif.
- Les URL et clés publiques utilisées par le client pointent vers le projet TEST. Aucune clé `service_role` ou clé secrète ne doit être présente dans le client.
- Les comptes et données de test sont jetables et ne contiennent aucune donnée commerciale réelle.

Si une précondition n'est pas démontrée, arrêter le test. Ne pas contourner un contrôle ni modifier les secrets existants.

## Préparation des sessions

- Session A : navigateur normal, compte A.
- Session B : autre navigateur ou fenêtre privée isolée, compte B.
- Session C : troisième session isolée, compte C.
- Vérifier dans chaque session que l'utilisateur connecté est bien celui attendu, sans afficher ni exporter de jeton.

## Parcours nominal

1. Depuis A, ouvrir « Registre commercial » et créer une proposition vers l'application approuvée de B, avec un titre de test et une clé d'idempotence unique.
2. Vérifier que A voit le contrat au statut initial et son événement de proposition.
3. Depuis B, ouvrir le registre et vérifier que le même contrat est visible.
4. Depuis B, accepter la proposition. Vérifier que le statut et l'historique se mettent à jour.
5. Depuis A, vérifier que le nouvel état est visible sans possibilité d'effectuer une action réservée à B.
6. Poursuivre les transitions prévues par le cycle de vie jusqu'à la clôture, en respectant le rôle du participant autorisé.
7. Vérifier que chaque transition produit un événement d'audit cohérent et qu'aucun événement antérieur n'a été modifié.

## Contrôles négatifs obligatoires

- C ne voit pas le contrat et ne peut ni le lire ni le faire évoluer.
- A ne peut pas effectuer une transition réservée à B, et inversement.
- Une transition interdite est refusée sans changement d'état ni événement parasite.
- Une répétition identique avec la même clé d'idempotence ne crée pas de doublon.
- La réutilisation d'une clé avec un contenu différent est rejetée.
- Aucun utilisateur authentifié ne peut modifier ou supprimer directement un contrat ou un événement d'audit via l'API.

## Concurrence — test distinct

Ce test doit être exécuté depuis deux connexions HTTP indépendantes, pas depuis une seule transaction SQL simulée.

- Préparer une proposition en attente.
- Envoyer presque simultanément deux transitions incompatibles depuis les sessions A et B.
- Vérifier qu'une seule transition valide gagne, que l'autre reçoit un refus cohérent, et qu'il existe exactement un événement d'audit pour la transition gagnante.
- Recommencer avec deux requêtes identiques portant la même clé d'idempotence : le résultat doit rester idempotent.

Ne pas lancer ce test tant que les deux sessions réelles et les comptes TEST ne sont pas confirmés.

## Preuves à consigner

Consigner uniquement : date/heure, identifiants de test non sensibles, action, résultat attendu, résultat observé, statut HTTP et identifiant du contrat/événement de test. Masquer les adresses e-mail si le rapport est partagé.

Ne jamais consigner : mot de passe, JWT, cookie, clé anon/publishable complète, clé secrète ou en-tête Authorization.

## Critères de sortie

Le parcours est validé uniquement si tous les contrôles nominaux et négatifs passent dans les sessions réelles, puis si le test de concurrence passe sur deux connexions indépendantes. Un échec bloque la fusion et doit être reproduit sur TEST avant toute correction.

## État au moment de la rédaction

Les tests SQL avec claims JWT simulés ont réussi et ont été annulés par ROLLBACK. Ils ne constituent pas une validation HTTP avec deux comptes réellement connectés. Les sessions réelles, le test de concurrence HTTP et la validation visuelle de l'interface restent à effectuer.
