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

## 2. Contrôles techniques observés

### Vérifié
- Authentification obligatoire sur l'application de production.
- Tables NIGHT EXCHANGE protégées par RLS.
- Pas de privilège d'exécution anon sur les RPC de marché auditées.
- Les RPC financières vérifient l'utilisateur authentifié et les droits Premium.
- Les tables de revenus internes n'ont pas de politique de lecture client.
- Les fonctions privilégiées d'agents et de modération auditées contiennent des contrôles d'identité, de propriétaire ou de rôle administrateur.
- La fonction de transition des plans d'action utilisait un search_path non vide ; migration de durcissement préparée dans cette branche.

### En cours
- Réduction des privilèges SQL clients par défaut sur les tables financières NIGHT EXCHANGE : retrait des écritures directes anon/authenticated et rétablissement des seules lectures authentifiées prévues par RLS.
- Vérification CI et revue de la migration de durcissement avant toute application en production.

### Alertes Supabase à traiter
- Protection contre les mots de passe compromis désactivée. La documentation du projet indique que l'option Supabase correspondante dépend d'un forfait supérieur ; ne pas prétendre qu'elle est active.
- Linter signale des tables RLS sans politique. Certaines sont volontairement privées et sans accès client direct (dont le registre interne des revenus NIGHT EXCHANGE et des événements/quota d'agents). Chaque table doit être classée explicitement comme « lecture client interdite » ou recevoir une politique propriétaire appropriée.
- Linter signale des fonctions SECURITY DEFINER accessibles aux utilisateurs authentifiés. Les fonctions examinées appliquent des contrôles d'identité, de propriétaire ou d'administrateur ; elles doivent rester couvertes par des tests d'autorisation négatifs et une revue régulière.

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
