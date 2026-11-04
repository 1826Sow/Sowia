# Authentification et isolation des données — SOW IA

## Décision d'architecture

SOW IA utilise actuellement Streamlit et SQLite. La mémoire et les messages existants ne sont pas encore cloisonnés par compte. Il ne faut pas publier cette version pour plusieurs utilisateurs.

La connexion choisie est **« Continuer avec GitHub »** : GitHub sert de fournisseur d'identité. Chaque compte sera identifié par l'identifiant numérique GitHub (et non par le nom d'utilisateur, qui peut changer).

## Pourquoi l'authentification n'est pas encore activée

Une connexion OAuth réelle exige une URL publique HTTPS stable pour l'application et une URL de rappel (callback) enregistrée auprès de GitHub. Les secrets OAuth doivent être configurés dans l'hébergeur, jamais dans GitHub ni dans le code.

Le dépôt seul ne fournit ni l'URL publique de SOW IA ni les secrets d'une application OAuth. Ajouter un simple écran « Connexion » sans vérifier réellement l'identité donnerait une fausse sécurité : cette approche est exclue.

## Étapes techniques obligatoires

1. Définir l'hébergeur et l'URL HTTPS publique de SOW IA.
2. Créer une application OAuth GitHub avec une URL de rappel exacte.
3. Stocker le Client ID, le Client Secret et une clé de session forte dans les secrets de l'hébergeur.
4. Implémenter le flux OAuth avec contrôle de `state`, échange du code côté serveur, validation de l'identité via l'API GitHub et session sécurisée.
5. Ajouter un identifiant propriétaire obligatoire aux conversations et aux notes mémoire.
6. Faire évoluer la base sans supprimer les anciennes données. Les anciennes données devront rester privées et non accessibles aux nouveaux comptes tant qu'une attribution explicite n'aura pas été faite.
7. Ajouter des tests prouvant qu'un compte ne peut ni lire, ni modifier, ni supprimer les données d'un autre compte.
8. Exécuter les tests automatiques et effectuer une revue de sécurité avant toute ouverture publique.

## Règles de sécurité

- Ne jamais demander ni enregistrer le mot de passe GitHub de l'utilisateur.
- Ne jamais committer de Client Secret, jeton OAuth, clé API ou secret de session.
- Ne jamais accepter un identifiant utilisateur fourni librement par le navigateur comme preuve d'identité.
- Toutes les lectures, écritures et suppressions doivent être filtrées côté serveur par l'identifiant authentifié.
- Les anciennes données SQLite ne doivent pas être automatiquement attribuées à un compte arbitraire.
- Ne pas activer les fonctions multi-utilisateurs tant que l'authentification et les tests d'isolation ne sont pas terminés.

## Information nécessaire pour finaliser le branchement OAuth

Il faut connaître l'adresse publique HTTPS de déploiement de SOW IA. Si le site n'est pas encore hébergé, cette étape viendra après le choix et la configuration de l'hébergement.