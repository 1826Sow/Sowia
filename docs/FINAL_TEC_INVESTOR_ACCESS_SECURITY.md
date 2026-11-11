# FINAL TEC — architecture de sécurité de l'espace investisseurs

**Statut : spécification de conception uniquement — non déployée, non activée et non auditée.**

Ce document prépare un accès externe en lecture seule au tableau de bord FINAL TEC. Il ne crée aucun compte, n'envoie aucune invitation et n'autorise aucun investisseur à consulter des données.

## 1. État technique constaté

- SOW IA utilise déjà une connexion Supabase Auth avec flux OAuth GitHub/PKCE.
- L'identité authentifiée est disponible dans la session Streamlit.
- Cette authentification prouve l'identité de la session ; elle ne prouve pas à elle seule qu'un utilisateur est autorisé à voir FINAL TEC.
- Aucun rôle investisseur dédié ni politique d'autorisation FINAL TEC n'est considéré comme vérifié à ce stade.
- Le tableau de bord actuel est une maquette locale alimentée par des données synthétiques/en attente de preuve.

**Conséquence :** ne jamais assimiler « connecté à SOWIA » à « autorisé à consulter FINAL TEC ».

## 2. Rôles proposés

| Rôle | Périmètre | Autorisations |
|---|---|---|
| `sowia_owner` | Administration SOWIA | Gérer les accès et paramètres, avec journalisation |
| `final_tec_admin` | FINAL TEC | Gérer le contenu publié et les preuves validées |
| `final_tec_analyst` | FINAL TEC | Préparer les indicateurs et soumettre des preuves ; aucune publication sans validation |
| `final_tec_investor_viewer` | Un dossier investisseur explicitement attribué | Lecture seule des seules données publiées et autorisées |

Le rôle investisseur ne doit jamais hériter des droits d'administration, de modification, de paiement ou d'accès aux données privées SOWIA.

## 3. Modèle d'autorisation

Une autorisation doit être accordée à un utilisateur Supabase précis, pour un dossier FINAL TEC précis, avec un état et une échéance.

Champs minimaux proposés pour une table dédiée :
- identifiant UUID ;
- `user_id` lié à l'identifiant Supabase Auth ;
- `project_id` fixe ou identifiant du dossier FINAL TEC ;
- rôle autorisé ;
- état `pending`, `active`, `revoked` ou `expired` ;
- date de début, date d'expiration ;
- créateur de l'autorisation et motif ;
- date de révocation et auteur de la révocation.

Ne pas utiliser une adresse e-mail, un nom GitHub ou un paramètre d'URL comme preuve d'autorisation. Les invitations doivent être nominatives, approuvées par un responsable habilité et limitées dans le temps.

## 4. Règles d'accès obligatoires

1. Refuser par défaut : absence de session, rôle inconnu, autorisation absente, expirée ou révoquée = aucun accès.
2. Vérifier le rôle côté serveur à chaque chargement de données, pas seulement masquer une page dans la navigation Streamlit.
3. Appliquer les politiques RLS Supabase aux tables de données ; la clé `service_role` ne doit jamais être utilisée dans le navigateur ni dans le chemin de lecture investisseur.
4. Isoler les données FINAL TEC des historiques, documents, mémoires, paiements et données personnelles SOWIA.
5. N'exposer que les indicateurs explicitement publiés et leurs preuves autorisées ; ne jamais exposer les brouillons, secrets, données personnelles ou pièces confidentielles internes.
6. Les investisseurs ont un accès strictement en lecture seule : aucune écriture, suppression, invitation, export massif ou modification.
7. La révocation doit être immédiate côté serveur ; une session déjà ouverte ne doit pas conserver un accès après révocation.
8. Enregistrer les connexions, consultations sensibles, téléchargements autorisés, refus d'accès, changements de rôle et révocations.
9. Limiter les exports, ajouter une identification du dossier destinataire et éviter les URL publiques permanentes.
10. Prévoir une durée de conservation définie pour les journaux et les données d'accès, conformément au RGPD.

## 5. Journal d'audit minimal

Chaque événement doit enregistrer : identifiant d'événement, horodatage UTC, identifiant utilisateur, dossier, action, ressource, résultat (autorisé/refusé), motif technique non sensible et identifiant de session pseudonymisé.

Ne jamais enregistrer de jeton OAuth, mot de passe, clé API, contenu de document confidentiel ou secret dans les journaux.

## 6. Tests de sécurité avant ouverture

- utilisateur non connecté : refus ;
- utilisateur connecté sans rôle : refus ;
- rôle investisseur sans attribution au dossier : refus ;
- accès expiré ou révoqué : refus immédiat ;
- investisseur A tentant de lire le dossier de B : refus ;
- tentative d'écriture/suppression par investisseur : refus ;
- tentative d'accès aux données privées SOWIA : refus ;
- rôle analyste tentant de publier directement : refus ;
- accès administrateur autorisé uniquement dans le périmètre prévu ;
- journaux présents pour autorisations et refus, sans secrets ;
- tests RLS exécutés avec des comptes de test distincts, pas uniquement avec le propriétaire ou le rôle service.

## 7. Séquence de mise en œuvre

1. Inventorier les tables Supabase, les politiques RLS, les migrations et les flux d'authentification existants.
2. Concevoir une migration réversible pour les rôles, attributions et journaux.
3. Écrire les politiques RLS et tests négatifs/positifs dans un environnement de test.
4. Ajouter un contrôle d'autorisation centralisé côté serveur dans SOW IA.
5. Brancher le tableau de bord sur un jeu de données publié et versionné, chaque indicateur conservant sa provenance.
6. Faire réaliser une revue de sécurité indépendante.
7. Ouvrir un accès pilote uniquement après validation humaine explicite, avec un seul compte de test et une révocation testée.

## 8. Critères de non-ouverture

L'accès externe reste désactivé tant qu'un seul des points suivants manque : inventaire RLS, tests d'isolation entre utilisateurs, révocation démontrée, journalisation, validation des données publiées, revue de sécurité et autorisation humaine explicite.

**Aucune promesse de performance, de partenariat, de chiffre financier ou de financement ne doit être affichée sans preuve vérifiable, datée et approuvée. FINAL TEC reste juridiquement et opérationnellement distinct de SOWIA.**
