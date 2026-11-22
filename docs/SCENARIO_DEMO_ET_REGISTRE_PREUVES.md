# SOW IA — Scénario de démonstration et registre de preuves

Statut : guide de démonstration préparé à partir des rubriques repérées dans le code de la branche de développement. Ce document ne certifie pas que chaque parcours a été testé en production ou sur un appareil Android.

Démo web connue : https://fm5aczcvvj5jgkhpxwqtcr.streamlit.app/  
Dépôt : https://github.com/1826Sow/Sowia  
Pitch deck : [PITCH_DECK_SOW_IA_FR_EN.md](PITCH_DECK_SOW_IA_FR_EN.md)

---

## 1. Objectif de la démonstration

En 5 à 7 minutes, montrer un flux cohérent :
**un objectif international → une recherche documentée → un acteur à qualifier → une relation suivie → une prochaine action préparée.**

Publics visés : incubateurs, accélérateurs, fondateurs, PME, partenaires commerciaux et investisseurs.

Ne pas chercher à parcourir tout le produit. Un scénario court, reproductible et honnête est plus convaincant qu'une visite exhaustive.

## 2. Scénario conseillé

### Cas d'usage fictif, explicitement présenté comme tel
Une jeune entreprise souhaite étudier le marché singapourien pour trouver des partenaires de distribution dans les technologies professionnelles.

Ce cas sert uniquement à illustrer le parcours. Il ne représente ni un client réel, ni un prospect existant, ni un résultat obtenu par SOW IA.

### Séquence chronométrée

| Temps | Action | Ce que le public doit comprendre |
|---|---|---|
| 0:00–0:30 | Présenter l'objectif et le marché fictif | Le besoin est défini avant la recherche |
| 0:30–2:00 | Ouvrir **SOWIA GLOBAL INTELLIGENCE** puis **Recherche assistée** | La recherche est ciblée et les sources restent consultables |
| 2:00–3:00 | Ouvrir **Développement mondial** puis **Visibilité mondiale** | Les événements et écosystèmes peuvent être explorés par région, pays, public et année |
| 3:00–4:00 | Montrer la qualification d'un résultat et, si le compte le permet, l'enregistrement CRM | Une piste devient un dossier à examiner, pas un partenariat acquis |
| 4:00–5:30 | Ouvrir **Négociation & accords** | Les besoins, objections, étapes et brouillons peuvent être structurés |
| 5:30–6:30 | Montrer la mémoire du dossier et la prochaine action | Le contexte peut être conservé pour le suivi |
| 6:30–7:00 | Conclure avec le pilote proposé | Inviter à tester un cas concret et mesurable |

Les libellés visibles peuvent évoluer. Si une rubrique n'est pas accessible dans la version effectivement ouverte, ne pas improviser : passer à la séquence suivante et consigner l'écart.

## 3. Texte oral suggéré

### Ouverture
« SOW IA est conçu pour aider les entrepreneurs et les organisations à structurer leur développement commercial au-delà de leur marché d'origine. Nous allons suivre un exemple fictif, depuis la recherche jusqu'à la préparation d'une relation commerciale. »

### Recherche
« Nous définissons d'abord le marché, le secteur et l'objectif. SOW IA aide à organiser une recherche et à consulter les sources. Les résultats sont des pistes : ils doivent être vérifiés avant toute décision. »

### Visibilité
« Nous pouvons ensuite explorer les écosystèmes, événements et publics pertinents selon la région et l'année. L'objectif est d'identifier les bons endroits où approfondir une démarche, pas de prétendre qu'une candidature ou une participation est déjà acquise. »

### Suivi et négociation
« Lorsqu'une piste mérite d'être approfondie, nous pouvons structurer les informations, suivre les étapes et préparer un brouillon de réponse ou une proposition indicative. Les messages ne sont pas envoyés automatiquement et aucun accord contractuel n'est accepté ou signé par l'outil. »

### Conclusion
« Nous souhaitons maintenant confronter ce parcours à des cas réels avec des startups, des incubateurs et des partenaires. Le pilote permettra de mesurer la pertinence des recherches, la facilité d'utilisation et le temps réellement gagné. »

## 4. Préparation avant chaque démonstration

- [ ] Ouvrir la version exacte qui sera présentée et noter la date / l'heure.
- [ ] Vérifier la connexion et l'accès au compte de démonstration.
- [ ] Vérifier que les rubriques Recherche assistée, Visibilité mondiale et Négociation & accords sont accessibles.
- [ ] Lancer une recherche courte et ouvrir au moins une source.
- [ ] Vérifier qu'une source est bien étiquetée comme piste à vérifier.
- [ ] Si l'archivage CRM est montré, vérifier le compte et le résultat de l'enregistrement.
- [ ] Si la mémoire est montrée, vérifier que le dossier est réellement archivé.
- [ ] Préparer un plan B sans connexion : captures récentes datées, clairement identifiées comme captures et non comme démonstration en direct.
- [ ] Fermer ou masquer les données personnelles, secrets, clés API et dossiers confidentiels.
- [ ] Ne pas utiliser de vraies coordonnées ou données de tiers sans autorisation.

## 5. Registre de preuves — à remplir uniquement après observation

| Élément | Preuve attendue | État actuel |
|---|---|---|
| Recherche assistée | Recherche exécutée, sources ouvertes et résultat daté | Présence dans le code repérée ; test en direct à consigner |
| Visibilité mondiale | Résultats affichés, filtres utilisés, sources consultables | Présence dans le code repérée ; test en direct à consigner |
| Enregistrement CRM | Confirmation de sauvegarde dans le bon espace utilisateur | Non vérifié ici |
| Négociation | Brouillon et étapes visibles sans envoi externe | Présence dans le code repérée ; test en direct à consigner |
| Mémoire de dossier | Entrée retrouvée dans « Ma mémoire » | Présence dans le code repérée ; test en direct à consigner |
| PDF | Import d'un fichier de test et retour à la navigation | Test Android réel à consigner |
| Android | Installation de l'APK correspondant au commit attendu | Signature, version et appareil réel à vérifier |
| Sécurité | Aucune clé serveur/service_role dans le client ou l'APK | Audit dédié requis ; ne pas conclure sans preuve |

Pour chaque test, enregistrer : date, version/commit, environnement (web/Android), appareil/navigateur, étapes, résultat attendu, résultat observé, capture ou journal expurgé, anomalie et statut (réussi/échoué/non testé).

## 6. Indicateurs à mesurer lors d'un pilote

Ne pas annoncer de résultats avant collecte. Pour chaque organisation pilote, mesurer :
- temps nécessaire pour produire une première liste de pistes pertinentes ;
- part des sources jugées pertinentes après revue humaine ;
- nombre de pistes qualifiées et de dossiers réellement suivis ;
- temps de préparation d'une prise de contact ;
- taux de complétion du parcours ;
- retours qualitatifs sur clarté, confiance et facilité d'utilisation.

Établir une mesure de référence avant le pilote et comparer des tâches équivalentes. Ne pas confondre nombre de résultats affichés et opportunités commerciales qualifiées.

## 7. Limites et garde-fous de présentation

- Une source web ou un résultat de recherche n'est pas automatiquement exact, actuel ou vérifié.
- Une piste CRM n'est pas un client, un partenaire ou une vente.
- Un brouillon n'est pas un message envoyé.
- Une proposition indicative n'est pas un contrat.
- Un accord de principe n'est pas une signature ni une autorisation de paiement.
- Une fonctionnalité visible dans le code n'est pas une preuve de fonctionnement sur tous les comptes ou appareils.
- Ne jamais exposer de secrets, tokens, clés privées, données personnelles ou informations confidentielles.

## 8. Fiche de retour pilote

À dupliquer pour chaque test :

- Organisation / profil (avec autorisation) :
- Pays / secteur :
- Date et version testée :
- Tâche réalisée :
- Résultat obtenu :
- Temps mesuré :
- Sources jugées utiles / inutiles :
- Étape la plus facile :
- Blocage principal :
- Fonction manquante ou à améliorer :
- Autorisation de citer le retour publiquement : oui / non / à confirmer.

---

## Prochaine étape de validation

Avant une présentation à un investisseur, compléter le registre avec au moins un parcours web observé de bout en bout et, séparément, un test Android réel. Les deux environnements ne doivent pas être confondus. Les résultats non testés doivent rester explicitement marqués « non testés ».
