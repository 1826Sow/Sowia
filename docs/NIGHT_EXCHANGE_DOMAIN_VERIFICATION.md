# NIGHT EXCHANGE — contrôle de propriété du domaine partenaire

## Objectif
Empêcher qu'une application tierce s'inscrive en se faisant passer pour une marque, un éditeur ou un service qu'elle ne contrôle pas. L'approbation d'une fiche ne doit jamais reposer uniquement sur le nom, le logo ou une adresse e-mail déclarés.

## Barrière de vérification proposée
1. Le compte authentifié soumet le domaine officiel de l'application.
2. SOW IA crée un défi aléatoire à durée limitée, lié au compte et au domaine.
3. Le demandeur publie une valeur TXT sous `_sowia-verification.<domaine>`.
4. Un service de confiance côté serveur interroge le DNS public et compare la valeur exacte.
5. Le serveur consomme le défi une seule fois dans une transaction atomique et conserve une preuve horodatée.
6. La fiche reste en attente d'une revue humaine de l'identité de l'éditeur, des permissions, de la sécurité et de la conformité. Le contrôle DNS prouve le contrôle technique du domaine au moment du test ; il ne prouve pas à lui seul l'identité juridique ni l'autorisation d'utiliser une marque.

## Règles anti-contournement
- Aucun statut `approved` ni `verified` ne peut être écrit par le navigateur ou un compte partenaire.
- Toute modification du domaine ou du propriétaire invalide la preuve et renvoie la fiche en modération.
- Les défis expirent, sont liés au compte et au domaine, et ne sont consommables qu'une fois.
- Les réponses DNS doivent provenir d'un résolveur serveur de confiance, jamais du formulaire ou du navigateur.
- Les domaines ressemblants, homographes, domaines jetables et preuves de marque font l'objet d'une revue humaine complémentaire.
- Un signalement entraîne une enquête confidentielle et une décision humaine motivée ; aucun score automatique ne doit déclarer une fraude.

## État de cette livraison
Le module `sowia_partner_verification.py` fournit des règles Python testables pour normaliser un domaine, émettre un défi TXT, interroger un résolveur DNS-over-HTTPS fixe côté serveur (Cloudflare, délai borné, redirections désactivées) et vérifier la réponse DNS. Les tests couvrent les domaines invalides, l'usurpation de compte, les preuves incorrectes, l'expiration et le rejeu.

**Ce n'est pas encore une vérification en production.** Le module ne contacte pas le DNS et n'est pas relié à l'interface, à Supabase ou à la modération.

Une migration préparatoire est maintenant proposée dans `supabase/migrations/20261121190000_night_exchange_domain_challenges.sql`. Elle prévoit :
- un schéma non exposé `sowia_private`, inaccessible aux rôles clients ;
- le stockage du seul condensat SHA-256 du jeton, jamais du jeton TXT en clair ;
- des défis liés à un compte et un domaine, avec expiration ;
- une consommation atomique par mise à jour conditionnelle, empêchant le rejeu concurrent ;
- une piste d'audit pour l'émission et la consommation réussie ;
- des fonctions internes dans `sowia_private` et de simples points d'entrée RPC `SECURITY INVOKER` dans `public`, exécutables uniquement par `service_role` ; cette clé doit rester exclusivement côté serveur.

**Cette migration est un fichier de proposition dans GitHub : elle n'a pas été appliquée à Supabase.** L'intégration reste bloquée jusqu'à la mise en place du résolveur DNS de confiance, aux tests SQL/RLS sur un environnement isolé, à la revue humaine et à la validation du déploiement. Ne jamais faire confiance à des enregistrements DNS transmis par le client.
