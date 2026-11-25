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

### Constat complémentaire — accès, export et effacement des données

Revue ciblée des droits d'accès, d'export et d'effacement effectuée le 25 novembre 2026 :

- L'export JSON de l'espace sélectionné couvre les données structurées explicitement listées par le service d'export : conversations standard, messages, notes mémoire, projets, agents, données de suivi et préférences.
- Depuis les PR #476 et #477, l'export inclut également les PDF privés du propriétaire dans l'espace sélectionné, sous forme Base64, après contrôle d'accès et vérification de signature PDF. Limites : 10 Mo par fichier et 50 Mo cumulés ; au-delà, l'export échoue plutôt que de produire un export incomplet.
- L'export reste limité au périmètre applicatif explicitement listé. Il n'inclut pas les données conservées directement par les sous-traitants, les secrets d'authentification/API, les identifiants de paiement ni certaines données techniques ou journaux.
- La suppression d'une conversation SOW IA standard par son propriétaire a été ajoutée par la PR #475, avec confirmation explicite et contrôle du propriétaire, de l'espace et des droits Premium lorsque requis.
- Depuis la PR #479, le propriétaire peut également supprimer une note de mémoire privée d'un de ses agents et supprimer une conversation d'agent. La suppression de la conversation entraîne celle de ses messages associés. Les contrôles sont limités au propriétaire, à l'agent, à la conversation et à l'espace concernés ; la RPC de suppression refuse les appels non authentifiés.
- L'accès du propriétaire à ses propres notes mémoire reste possible lorsque son agent est en pause ou archivé, afin qu'il puisse les consulter et les supprimer. Cela ne donne pas accès aux données d'un autre compte.
- Aucune procédure autonome et complète de suppression du compte Auth n'a été confirmée. La suppression d'un compte dans Supabase, la propagation aux sauvegardes, journaux et sous-traitants, ainsi que les délais de conservation doivent être définis et testés séparément.
- Aucune durée de conservation fonctionnelle générale n'a été identifiée pour l'ensemble des conversations agents et des notes mémoire persistantes.

**État après les PR #475 à #479 :** l'export JSON applicatif (y compris les PDF privés dans les limites ci-dessus), la suppression d'une conversation standard, la suppression d'une note mémoire privée d'agent et la suppression d'une conversation d'agent avec ses messages sont implémentés. Ces fonctionnalités ne démontrent pas à elles seules que l'ensemble des données détenues par les sous-traitants, les sauvegardes et les journaux est effacé, ni qu'une suppression autonome complète du compte est disponible.

**Conséquence :** ne pas considérer le droit à l'effacement ni la limitation de conservation comme entièrement opérationnels pour l'ensemble du compte. Avant ouverture publique, définir puis tester la suppression complète du compte, les délais de propagation, les sauvegardes, les journaux et les exceptions légales. Maintenir les suppressions sélectives strictement limitées aux données du compte demandeur et auditer leur exécution.

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
