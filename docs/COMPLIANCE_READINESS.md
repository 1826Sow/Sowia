# SOW IA — registre de préparation à la conformité

**État au 25 novembre 2026 — audit technique initial, non-certification.**

Ce document distingue les contrôles vérifiés dans le dépôt et la base de production des éléments qui nécessitent des informations du responsable de SOW IA ou une validation par un professionnel habilité. Il ne constitue ni un avis juridique, ni une certification RGPD, AMF, MiCA, DSA ou de sécurité.

## 1. NIGHT EXCHANGE — périmètre actuellement autorisé par le code

- Le moteur est une simulation fermée en crédits NXC non convertibles et non remboursables.
- Aucun dépôt, retrait, paiement, remboursement ou règlement en euros n'est implémenté dans cette version.
- Les « actions » sont des positions virtuelles de simulation : elles ne donnent pas de droit réel au capital, aux bénéfices, à un dividende ou à la propriété intellectuelle d'une application.
- Les cotations et capitalisations sont simulées.
- Les opérations passent par des fonctions PostgreSQL contrôlées ; les RPC de marché vérifiées refusent l'exécution au rôle anon et sont accessibles aux utilisateurs authentifiés.
- Les politiques RLS limitent les lectures aux données publiques approuvées et aux données propres à l'utilisateur ou aux participants.
- Les journaux de transactions et d'allocations sont protégés contre la modification et la suppression.

**Règle de lancement :** ne pas activer d'argent réel, de conversion, de titres transférables, de dividendes monétaires, de droits de vote ou de droits économiques sans analyse juridique préalable dans chaque territoire ciblé et autorisations réglementaires nécessaires.

## 2. Contrôles techniques observés en production

### Vérifié le 25 novembre 2026
- Authentification obligatoire sur l'application de production (connexion utilisateur précédemment confirmée).
- Tables NIGHT EXCHANGE protégées par RLS.
- Les privilèges SQL clients sur les tables financières ont été réduits : les rôles anon/authenticated n'ont plus d'écriture directe sur les tables de marché ; les lectures authentifiées prévues restent soumises à RLS.
- Les RPC de marché auditées refusent l'exécution au rôle anon et contrôlent l'utilisateur authentifié et les droits requis.
- Les tables internes de revenus, d'activité et de quotas sont inaccessibles directement aux rôles anon et authenticated ; les sept tables signalées « RLS enabled, no policy » ont RLS activé et aucun privilège client direct de lecture/écriture.
- La fonction interne `sowia_consume_agent_credits(uuid,text)` n'est plus exécutable par PUBLIC, anon ou authenticated. Le point d'entrée authentifié `sowia_consume_agent_action_for_agent` reste disponible.
- Les huit fonctions SECURITY DEFINER encore exécutables par authenticated ont été inspectées individuellement : leurs définitions vérifiées contiennent des contrôles d'identité, de propriétaire, de rôle administrateur ou d'accès Premium selon leur fonction.
- `sowia_action_transition(uuid,text,text)` utilise désormais `search_path=pg_catalog`.

### Alertes encore ouvertes
- Supabase signale huit fonctions SECURITY DEFINER exécutables par authenticated. Cette alerte ne prouve pas à elle seule une faille : ces RPC sont des points d'entrée utilisés par l'application. Elles doivent rester couvertes par des tests d'autorisation négatifs et une revue régulière ; ne pas révoquer leurs droits en bloc sans remplacer les parcours applicatifs.
- Protection contre les mots de passe compromis désactivée. Ne pas prétendre qu'elle est active ; vérifier les possibilités de configuration du projet et les contraintes de forfait avant toute décision.
- Supabase signale sept tables RLS sans politique. L'inspection des privilèges confirme qu'elles ne sont pas directement accessibles aux rôles anon/authenticated ; elles sont conçues comme tables internes. Conserver cette absence d'accès client tant qu'aucun besoin applicatif explicite et validé ne justifie une politique.
- Les tests RLS utilisant les comptes de test Supabase ont précédemment échoué avec `invalid_credentials`. Cela empêche de considérer la validation multi-comptes de bout en bout comme terminée ; les secrets GitHub ne doivent pas être modifiés dans le cadre de cet audit.

## 3. Informations juridiques et RGPD manquantes avant ouverture publique

Le site vitrine public ne présente actuellement aucun lien visible vers des mentions légales, une politique de confidentialité ou des conditions d'utilisation. Ne pas publier de mentions légales fictives ni inventer l'identité de l'exploitant.

À obtenir et valider :
- identité légale de l'exploitant (personne ou société), forme juridique, adresse, immatriculation et numéro de TVA le cas échéant ;
- adresse de contact juridique et support ;
- pays d'établissement et territoires où le service sera proposé ;
- inventaire des données traitées, finalités, bases légales, durées de conservation et destinataires ;
- liste exacte des sous-traitants et transferts hors EEE (hébergement, authentification, IA, recherche web, paiement, analytique) ;
- procédure d'accès, rectification, export, opposition et effacement, avec les exceptions de conservation légale ;
- politique de cookies/traceurs si des traceurs non essentiels sont utilisés ;
- procédure de violation de données, gestion des demandes et contact de l'autorité compétente si nécessaire.

## 3 bis. Sous-traitants et flux techniques repérés dans le code

Cette liste est une cartographie de départ fondée sur le dépôt ; elle ne prouve pas qu'un fournisseur est activé dans l'environnement de production ni ne remplace la vérification des contrats et paramètres de compte.

- **Hébergement de l'application :** Render, service déclaré en région Frankfurt dans `render.yaml`.
- **Authentification, base de données et stockage documentaire :** Supabase.
- **Inférence IA :** intégrations OpenAI et Groq présentes ; le fournisseur effectivement utilisé dépend de la configuration runtime.
- **Recherche web :** intégrations Tavily et DuckDuckGo présentes ; l'utilisation de Tavily dépend de la configuration.
- **Abonnements :** intégration PayPal présente avec configuration Sandbox/Live ; le mode effectif doit être vérifié dans l'environnement sans consulter ni modifier les secrets.
- **Voix :** la transcription utilise la reconnaissance vocale du navigateur ; le navigateur peut transmettre l'audio à son propre service de reconnaissance, comme l'interface l'indique déjà à l'utilisateur.
- **Connexion GitHub :** le code prévoit le fournisseur OAuth GitHub via Supabase ; son activation réelle doit être vérifiée dans la configuration du fournisseur.

Pour chaque fournisseur réellement activé, consigner l'entité contractante, le rôle RGPD, le lieu de traitement, les sous-traitants ultérieurs, les transferts hors EEE, les garanties contractuelles, les durées et les catégories de données transmises. La CNIL rappelle qu'un contrat de sous-traitance conforme à l'article 28 et une maîtrise de la chaîne de sous-traitance sont nécessaires lorsque le fournisseur agit comme sous-traitant.

## 4. Plateforme et marketplace — analyse réglementaire à faire

- Déterminer si NIGHT EXCHANGE reste un outil de démonstration/jeu fermé ou permet ultérieurement des contrats entre professionnels et consommateurs.
- Si des contrats à distance entre consommateurs et professionnels sont conclus via la plateforme, analyser les obligations applicables du Digital Services Act, notamment la traçabilité des professionnels, les mécanismes de notification et les voies de recours.
- Toute offre de titres financiers, droits équivalents à des actions, financement participatif ou négociation pour compte de tiers doit faire l'objet d'une qualification par un avocat spécialisé et, si nécessaire, d'un échange avec l'AMF/autorité compétente. Une mention « simulation » ou « jeton » ne neutralise pas une activité réelle.
- Définir les règles de modération, suspension, contestation, signalement d'une application illicite et traitement des réclamations.

## 5. Conditions de mise en production à lever

- [ ] Identité de l'exploitant et coordonnées juridiques confirmées.
- [ ] Mentions légales, politique de confidentialité et conditions d'utilisation rédigées et publiées.
- [ ] Registre des traitements et contrats de sous-traitance revus.
- [ ] Durées de conservation et parcours d'exercice des droits testés.
- [ ] Cartographie des transferts de données et mesures de sécurité documentées.
- [ ] Revue juridique du modèle NIGHT EXCHANGE dans les pays de lancement.
- [ ] Tests de sécurité et d'autorisation multi-comptes réussis.
- [ ] Plan de réponse aux incidents et de continuité testé.
- [ ] Vérification d'accessibilité et des langues proposées.

## Références officielles de départ

- RGPD : Règlement (UE) 2016/679.
- DSA : Règlement (UE) 2022/2065.
- MiCA : Règlement (UE) 2023/1114.
- ESMA : orientations sur la qualification des crypto-actifs comme instruments financiers.
- AMF : régime PSFP et services d'investissement en cas d'offres de titres.

Ce registre doit être mis à jour à chaque évolution fonctionnelle, commerciale ou géographique.
