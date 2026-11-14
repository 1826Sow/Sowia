# SOW IA — financement et partenariats

## Objectif

Centraliser les pistes de financement de SOW IA sans remplacer Streamlit,
Supabase, les comptes existants, les droits Premium ou les parcours PayPal déjà
présents.

## Canaux déjà représentés dans l'application

1. **Abonnements Premium** — parcours existant « Abonnement ».
2. **Offres et prestations professionnelles** — pipeline « Opportunités et revenus ».
   Les prévisions restent des estimations, jamais des encaissements.
3. **Partenariats, affiliation et sponsoring** — « Développement mondial »,
   CRM partenaires et Business Club.
4. **Aides, appels à projets et marchés** — radar de recherche dans
   « Développement mondial ». Les résultats sont des pistes à vérifier, pas
   des financements obtenus.
5. **Paiements confirmés** — « Revenus & paiements », alimenté uniquement par
   les transactions validées et enregistrées.

## Liens externes facultatifs

La page « Financement & partenariats » peut afficher des liens externes configurés
dans les secrets du déploiement :

- `SOWIA_SUPPORT_URL` : page externe de soutien volontaire.
- `SOWIA_CROWDFUNDING_URL` : campagne de financement participatif.
- `SOWIA_SPONSOR_URL` : page externe de contact ou de présentation sponsor.

Seules les URL HTTPS valides sont affichées. Si une valeur est absente ou invalide,
le bouton correspondant reste désactivé/absent et l'interface indique que le
parcours n'est pas configuré.

## Limites et sécurité

- Cette page ne crée aucun paiement, abonnement, don ou remboursement.
- Aucun lien de paiement n'est inventé et aucun identifiant PayPal/Stripe n'est
  exposé dans le navigateur.
- Aucun nouveau schéma ni aucune nouvelle table Supabase n'est introduit.
- Les liens externes doivent être créés et contrôlés par le propriétaire de SOW IA.
- Les montants prévisionnels, partenariats en discussion, demandes de subvention
  et dons attendus ne sont pas des revenus encaissés.
- La mise en place d'une campagne ou d'un sponsor reste conditionnée à
  l'acceptation de leurs conditions, à la vérification juridique/fiscale et à
  la configuration du compte de paiement externe.

## Activation

Ne renseigner les variables de lien qu'après création et vérification des pages
correspondantes chez le fournisseur choisi. Ne jamais ajouter de mot de passe,
clé API ou secret de paiement dans le code ou dans ce document.
