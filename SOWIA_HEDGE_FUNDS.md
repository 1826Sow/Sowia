# SOWIA Hedge Funds — première fondation analytique

## Périmètre
Le module `hedge_fund_intelligence.py` fournit une validation de profils de fonds et des statistiques descriptives sur une série mensuelle de rendements nets explicitement fournie.

- Profils : identité, gestionnaire, stratégie, domicile, devise, encours sous gestion et date de référence.
- Provenance : URL HTTPS et indicateur explicite de vérification de la source.
- Rendements : rendement composé, rendement annualisé, volatilité annualisée, drawdown maximal et ratio de Sharpe indicatif.
- Contrôles : données manquantes, mois dupliqués, mois manquants, devises et valeurs numériques invalides.

## Limites
- Aucun flux de marché n'est téléchargé et aucun chiffre n'est inventé.
- Les rendements doivent être des rendements mensuels nets, exprimés en décimal (0,02 = +2 %), sans mois manquant.
- Le ratio de Sharpe utilise le taux sans risque annuel fourni, converti en équivalent mensuel. Il reste un indicateur descriptif, pas une prévision.
- Les encours sous gestion ne doivent jamais être additionnés entre devises.
- Aucun classement, conseil d'investissement, ordre, transfert ou souscription n'est produit.
- Les performances historiques ne garantissent pas les performances futures.

## Étapes suivantes
1. Définir des adaptateurs de sources documentées et leurs licences/conditions d'accès.
2. Ajouter des comparaisons de stratégie et d'indices de référence avec devises explicites.
3. Ajouter les contrôles de liquidité, levier, concentration et contrepartie lorsque les données sont disponibles.
4. Intégrer une vue dédiée dans l'application après validation indépendante des tests et des droits d'accès.
