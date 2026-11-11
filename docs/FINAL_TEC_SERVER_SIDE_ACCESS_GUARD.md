# FINAL TEC — contrôle d'autorisation côté serveur

**Statut : code préparé dans une branche de proposition, non fusionné et non déployé.**

## Contrôle implémenté

Le routage Streamlit de « FINAL TEC LIVE — investisseurs » appelle désormais un helper dédié. L'accès n'est accordé que si :
- le mode Supabase cloud est actif ;
- une identité Supabase authentifiée est présente ;
- un client Supabase de session est disponible ;
- l'appel RPC `final_tec_can_view_published_metrics` retourne strictement le booléen `true`.

Le RPC s'appuie sur le JWT de la session et sur `auth.uid()`, puis vérifie une attribution active au projet FINAL TEC, le rôle `final_tec_investor_viewer`, la date de début et l'expiration.

## Refus par défaut

Toute absence d'identité/client, RPC absent, erreur réseau/SQL, réponse mal formée ou réponse autre que le booléen `true` bloque la page. L'application n'affiche alors aucun tableau de bord et n'expose pas le détail technique de l'erreur.

L'authentification GitHub/SOWIA seule, un nom d'utilisateur, une adresse e-mail, un paramètre d'URL ou une variable locale ne constitue jamais une autorisation FINAL TEC.

## Tests unitaires ajoutés

- RPC confirme explicitement l'accès ;
- attribution refusée ;
- identité/client absent ;
- RPC absent ;
- erreur RPC ;
- réponse mal formée.

Ces tests utilisent un faux client Supabase : ils valident le comportement du helper, **pas** les politiques RLS réelles.

## Dépendance et blocage volontaire

La fonction SQL `final_tec_can_view_published_metrics()` appartient à la proposition SQL PR #222. Tant que cette proposition n'est pas revue puis appliquée dans un environnement de test, le RPC peut être absent ; dans ce cas la page reste bloquée. C'est le comportement attendu.

Le dashboard lui-même utilise encore des données synthétiques locales. Cette modification ne branche pas de données réelles, ne crée aucun investisseur et n'active aucun accès externe.

## Limites

- Le helper protège la route Streamlit, mais la future lecture des métriques doit aussi passer par RLS.
- Aucun journal d'audit des refus n'est encore branché ; ne pas prétendre qu'il est opérationnel.
- Les rôles admin/analyste nécessiteront des autorisations distinctes ; cette version ne donne accès qu'au rôle viewer.
- Les tests réels à deux comptes Supabase, l'inspection du projet Supabase et une revue de sécurité restent obligatoires.
