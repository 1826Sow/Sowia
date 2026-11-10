# SOW IA — Paiements en crypto-actifs

## Statut

Spécification produit et sécurité — **pas encore intégrée au parcours de paiement en production**.

Le paiement PayPal existant reste inchangé. Aucun paiement crypto ne doit accorder Premium avant validation serveur d'un événement de paiement confirmé auprès du prestataire.

## Objectif

Permettre aux clients éligibles de régler un abonnement ou un service SOW IA en crypto-actifs, tout en conservant un prix de référence en EUR, une comptabilité fiable et une expérience de paiement internationale.

## Première version recommandée

- Priorité aux jetons de monnaie électronique dont l'émetteur et le jeton sont autorisés pour le marché ciblé au titre de MiCA.
- Évaluer en premier lieu EURC (référence euro) et USDC (référence dollar), sous réserve de la disponibilité effective auprès du prestataire retenu, des réseaux activés pour SOW IA et de la conformité au moment du lancement.
- Ne pas accepter automatiquement un jeton ou un réseau parce qu'il est techniquement disponible.
- BTC, ETH et autres actifs volatils pourront faire l'objet d'une phase ultérieure, avec devis à durée limitée et conversion/risque de change explicitement présentés.
- Ne pas créer de jeton SOW IA ni de portefeuille custodial propriétaire dans cette première version.

## Architecture technique

Créer un adaptateur de paiement indépendant du fournisseur, sans modifier le flux PayPal :

1. Le serveur SOW IA crée une commande interne avec identifiant unique, utilisateur, produit, montant EUR, devise, date d'expiration et état `pending`.
2. Le prestataire retourne une session ou un lien de paiement hébergé. Les clés API restent exclusivement dans les secrets serveur.
3. Le client paie directement dans l'interface du prestataire ou son portefeuille ; SOW IA ne demande jamais la phrase de récupération ni la clé privée.
4. Un webhook signé est reçu côté serveur. Vérifier la signature cryptographique, l'identifiant d'événement, le marchand destinataire, la commande, l'actif, le réseau, le montant et le statut final.
5. Les webhooks doivent être idempotents : un même événement ne peut être traité deux fois.
6. Une confirmation du navigateur ou une capture d'écran de transaction ne suffit jamais à accorder Premium.
7. Après vérification serveur et confirmation définitive du prestataire, enregistrer la transaction et accorder l'accès selon la durée et le produit achetés.
8. Les remboursements, annulations, paiements partiels, paiements en trop, expirations et litiges doivent avoir des états dédiés et une procédure traçable.

## Données et comptabilité

Prévoir des enregistrements séparés pour les commandes, événements de paiement et écritures comptables. Chaque enregistrement doit contenir au minimum :

- utilisateur et espace SOW IA concernés ;
- référence interne de commande ;
- fournisseur et identifiant de paiement externe ;
- actif, réseau, montant attendu et montant reçu ;
- devise de référence et taux de conversion/horodatage si applicable ;
- statut, horodatages, frais et montant net reçu ;
- identifiant d'événement webhook et état de traitement ;
- référence de remboursement éventuelle.

Ne jamais stocker de clé privée, phrase de récupération ou secret de portefeuille. Ne jamais considérer une commande créée ou un paiement simplement détecté comme un revenu encaissé. Les tableaux de bord distinguent montant brut, frais, remboursements, taxes, montant net et valeur EUR réellement rapprochée.

## Sécurité et conformité — conditions bloquantes avant lancement

- Vérifier le statut réglementaire exact du prestataire, de ses entités contractantes et de ses services dans les pays ciblés.
- Vérifier si le parcours précis implique des services de paiement, des services sur crypto-actifs, ou les deux ; ne pas supposer qu'un prestataire possède toutes les autorisations nécessaires.
- Faire valider le modèle par un conseil compétent en réglementation financière, fiscalité, comptabilité et protection des consommateurs.
- Prévoir les obligations KYC/AML, sanctions, Travel Rule lorsqu'applicable, conservation des justificatifs, RGPD et traitement des réclamations.
- Restreindre les actifs et réseaux à une liste blanche explicitement activée.
- Ne pas activer de paiements Live avant validation du contrat, des frais, des pays desservis, des conditions de remboursement et des webhooks en environnement de test.
- Aucun transfert sortant automatique, conversion, investissement ou conservation de fonds clients dans la première version.

## Fournisseur à évaluer

**Fipto** est un candidat de présélection technique, pas un fournisseur choisi ni un partenariat conclu. Sa documentation publique décrit une API B2B, des Payment Links hébergés, des webhooks, un environnement de démonstration, ainsi que USDC et EURC sur plusieurs réseaux. Elle indique également des statuts français d'établissement de paiement et de PSCA MiCA. La documentation précise que l'offre vise les PSP, courtiers crypto et grandes entreprises ; l'éligibilité de SOW IA, les conditions commerciales et les services effectivement accessibles doivent donc être confirmés directement avant toute intégration.

Site et documentation à examiner :
- https://www.fipto.com/fr
- https://docs.fipto.com/reference/getting-started
- https://docs.fipto.com/docs/what-is-fipto-api

Comparer au moins deux prestataires supplémentaires sur les mêmes critères : autorisations pertinentes, pays acceptés, stablecoins/réseaux autorisés, checkout hébergé, webhooks signés, sandbox, conversion EUR, frais, remboursements, délais de règlement, support et exigences KYC/AML.

## Plan de réalisation

1. Vérification de l'entité juridique SOW IA et de son éligibilité marchand auprès des fournisseurs.
2. Comparatif fournisseurs et revue réglementaire.
3. Modèle de données Supabase avec RLS et accès d'administration serveur strictement limité.
4. Adaptateur et tests unitaires de validation des commandes/webhooks, sans clés de production.
5. Parcours sandbox de bout en bout et tests de rejeu, doublons, mauvais réseau, mauvais montant, webhook falsifié et paiement expiré.
6. Revue sécurité et comptable.
7. Activation Live uniquement après accord explicite du responsable et validation des conditions.

## Règle produit

Le client voit le prix en EUR, le montant crypto, le réseau exact, les frais éventuels et le délai d'expiration avant de confirmer. Le statut du paiement est explicite : en attente, détecté, confirmé, expiré, remboursé ou rejeté. Le droit Premium n'est accordé qu'après confirmation serveur définitive.


## Migration Supabase préparée

Le fichier `supabase_crypto_payments.sql` ajoute :
- une table de commandes crypto, lisible uniquement par le propriétaire authentifié ;
- une table d'événements webhook non accessible aux clients ;
- des identifiants externes uniques pour empêcher les doublons ;
- le champ `crypto_payment_id` et l'extension du fournisseur d'abonnement à `crypto`.

**Cette migration est seulement enregistrée dans GitHub. Elle n'a pas été exécutée dans Supabase.** Les écritures doivent être faites par le serveur avec une clé de service conservée dans les secrets, jamais depuis le navigateur. Le parcours ne doit pas être activé avant revue SQL/RLS, tests et connexion réelle au prestataire.

La table d'événements ne stocke volontairement pas le corps brut complet du webhook. Les journaux applicatifs doivent éviter les secrets, données personnelles superflues et données de portefeuille sensibles.


### Traitement atomique — préparation technique

La migration SQL inclut maintenant la fonction serveur `sowia_confirm_crypto_payment` :
- accès d'exécution réservé au rôle Supabase `service_role` ;
- insertion unique des événements fournisseur ;
- verrouillage de la commande pendant le rapprochement ;
- vérification du fournisseur, utilisateur, commande, expiration, statut final, actif, réseau et montant exact ;
- mise en attente de contrôle manuel en cas d'écart ;
- absence d'écrasement d'un droit PayPal Premium actif ;
- activation du droit crypto dans la même transaction que la confirmation de commande.

Cette fonction **ne vérifie pas elle-même la signature cryptographique du fournisseur**. L'adaptateur serveur devra impérativement vérifier la signature avant de l'appeler et lui transmettre `signature_verified=true` uniquement après validation. Le nom du fournisseur reste configurable dans le schéma ; Fipto n'est toujours pas choisi.

La migration n'a pas été exécutée sur Supabase et la fonction SQL n'a pas encore été testée sur une base de test. Elle doit être relue et testée avant exécution.


### Protection contre le double droit Premium

La fonction atomique refuse maintenant de remplacer **tout droit Premium déjà actif**, qu'il provienne de PayPal ou d'un paiement crypto antérieur. La commande est placée en contrôle manuel. Cela évite qu'un deuxième paiement écrase la référence du premier et simplifie le rapprochement comptable. Le parcours de création de commande devra aussi vérifier l'absence d'un abonnement actif avant d'envoyer le client vers le prestataire.

### Cas de tests SQL obligatoires avant activation

- événement valide et paiement exact : une seule commande confirmée et un seul droit Premium ;
- rejeu du même identifiant d'événement : résultat `duplicate`, aucune seconde activation ;
- deuxième événement pour une commande déjà confirmée : `already_confirmed` ;
- signature invalide : rejet sans activation ;
- utilisateur, commande ou fournisseur incorrect : rejet ;
- actif, réseau, montant, statut ou expiration incorrect : contrôle manuel, aucun droit ;
- droit PayPal ou crypto déjà actif : contrôle manuel, aucune écriture d'écrasement ;
- deux webhooks simultanés pour une même commande : une seule transaction peut confirmer la commande grâce au verrouillage `FOR UPDATE`.

Ces tests SQL restent à exécuter dans un projet Supabase de test. La migration n'est pas une preuve d'exécution ni de conformité réglementaire.


## Préparation du parcours de commande

Deux modules neutres vis-à-vis du prestataire sont maintenant ajoutés :

- `crypto_checkout.py` valide côté serveur l'utilisateur, l'espace, le produit, le prix EUR, l'actif, le réseau, le montant crypto et l'expiration (5 à 60 minutes), puis prépare un objet de commande `pending`.
- `validate_hosted_checkout_url` n'accepte que les liens HTTPS dont l'hôte exact figure dans une liste blanche explicite.

Tests écrits dans `tests/test_crypto_checkout.py` pour les commandes valides, les valeurs hors limites, les dates sans fuseau, les actifs/réseaux non autorisés et les liens de paiement non fiables.

Ces fonctions ne créent pas encore de commande dans Supabase et ne contactent aucun prestataire. Le taux de conversion EUR/crypto doit venir du prestataire au moment de créer le checkout, avec horodatage et durée de validité ; il ne doit jamais être inventé par SOW IA. Le module ne doit pas être branché à l'interface client tant qu'un prestataire n'est pas retenu et que son domaine officiel n'est pas vérifié.


## Registre financier et reporting

La migration `supabase_crypto_payments.sql` ajoute maintenant `sowia_financial_transactions` :
- une ligne est créée dans la même transaction SQL qu'une confirmation crypto acceptée ;
- les lignes sont uniques par fournisseur, identifiant de paiement et type d'écriture ;
- les utilisateurs authentifiés peuvent uniquement lire leurs propres lignes ; aucune écriture client n'est autorisée ;
- les montants bruts sont conservés dans la devise réellement reçue (EURC, USDC, etc.) ;
- la valeur de référence en EUR est conservée séparément et n'est jamais présentée comme un règlement EUR ;
- frais et net restent NULL tant que le prestataire ne les a pas fournis et rapprochés.

Le module `financial_reporting.py` agrège uniquement les transactions confirmées/remboursées, séparées par fournisseur et devise. Il exclut les paiements en attente et ne transforme pas un montant crypto en revenu EUR encaissé.

**Limite actuelle :** la fonction SQL écrit les paiements crypto confirmés. Le flux PayPal existant n'alimente pas encore ce registre ; il faudra l'intégrer séparément sans modifier son traitement d'accès Premium. Aucun tableau de bord financier n'est encore branché dans l'application. Les tests Python sont écrits mais leur exécution n'est pas confirmée.


## Intégration PayPal et première vue financière

Le retour PayPal après capture serveur validée appelle maintenant `financial_ledger.record_paypal_capture` après l'attribution Premium. L'écriture utilise l'identifiant de capture PayPal, pas seulement l'identifiant de commande, et une clé d'unicité rend la répétition idempotente. Si l'écriture comptable échoue, l'accès Premium déjà validé reste actif et l'application signale que le rapprochement est à effectuer ; elle ne prétend pas que le paiement a échoué.

La page privée **Revenus & paiements** lit les écritures via le client Supabase authentifié et RLS, puis affiche une synthèse séparée par fournisseur et devise. Elle distingue le brut, les remboursements, les frais/net connus et la référence EUR non encaissée.

Limites de cette première version :
- La migration `supabase_crypto_payments.sql` doit être exécutée pour créer la table de registre avant d'utiliser la page.
- Les paiements PayPal ponctuels futurs alimentent le registre ; les paiements historiques ne sont pas rétro-importés.
- Les abonnements PayPal récurrents, les remboursements PayPal et les frais de règlement ne sont pas encore rapprochés.
- Les paiements crypto ne peuvent alimenter le registre qu'après activation réelle d'un prestataire, vérification de ses webhooks et application de la migration.
- Le tableau de bord ne calcule pas un bénéfice net global ni un chiffre d'affaires consolidé multi-devises.

Les tests unitaires sont ajoutés pour le writer PayPal et la lecture/agrégation ; ils doivent encore être exécutés en CI.


## Rapprochement des abonnements PayPal récurrents

Le module `paypal_subscriptions.py` expose désormais `sync_completed_subscription_transactions` :
- la synchronisation est volontaire et déclenchée par le titulaire depuis « Revenus & paiements » ;
- elle couvre une fenêtre bornée de 90 jours, puis peut être relancée si PayPal signale d'autres pages ;
- elle retrouve le propriétaire et le forfait depuis la ligne serveur `sowia_subscriptions`, puis recoupe le propriétaire et le plan avec la fiche PayPal ;
- elle récupère l'historique PayPal authentifié et ne comptabilise que les transactions dont le statut est `COMPLETED` ;
- chaque transaction est enregistrée sous son identifiant PayPal réel, avec clé d'idempotence ; frais et net restent inconnus si PayPal ne les retourne pas ;
- les liens de pagination sont limités au domaine HTTPS de l'API PayPal configurée.

Les tests `tests/test_paypal_recurring_sync.py` et `tests/test_paypal_recurring_ledger.py` couvrent l'identification du propriétaire, les statuts non terminés, la pagination et l'idempotence.

Les statuts `PARTIALLY_REFUNDED` et `REFUNDED` sont désormais détectés pendant la synchronisation. Comme la liste des transactions d'abonnement expose le statut et l'identifiant de la capture, mais pas l'identifiant ni le montant de chaque remboursement individuel, SOW IA place la capture en `manual_review` au lieu d'inventer un montant de remboursement. Une capture ainsi signalée est exclue des totaux de revenus reconnus jusqu'au rapprochement exact. Le nombre de captures à contrôler est retourné par la synchronisation.

**Limite restante :** les remboursements ne sont pas encore inscrits comme écritures `refund` individuelles. Il faudra récupérer les ressources de remboursement PayPal avec leurs identifiants et montants propres (ou traiter les événements webhook signés) avant de les comptabiliser. Cette synchronisation est limitée à Sandbox tant que le parcours d'abonnement n'a pas été validé en environnement de test.

Référence technique officielle : [PayPal Subscriptions API — liste des transactions](https://developer.paypal.com/docs/api/subscriptions/v1/#subscriptions_transactions).
