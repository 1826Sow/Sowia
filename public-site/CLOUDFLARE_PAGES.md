# Publication SOW IA — Cloudflare Pages

Ce guide prépare l'hébergement de la page publique sans toucher au déploiement Streamlit de l'application privée.

## État

- Page statique : `public-site/index.html`.
- Projet Cloudflare Pages : **à créer**.
- Domaine public : **à choisir / rattacher**.
- Web Analytics : direction approuvée, **pas encore activée**.
- Aucun secret Cloudflare ni script de suivi n'est stocké dans le dépôt.

## Configuration recommandée

Créer un projet Cloudflare Pages connecté au dépôt GitHub `1826Sow/Sowia`.

| Paramètre | Valeur |
|---|---|
| Branche de production | `main` (uniquement après fusion approuvée) |
| Répertoire racine | `public-site` |
| Commande de build | aucune |
| Répertoire de sortie | `.` |
| Framework preset | None |

Pour le premier aperçu, utiliser un déploiement de prévisualisation depuis la branche de la PR, si le projet Pages est configuré pour les previews. Ne pas publier la branche de travail comme production.

## Contrôles avant mise en production

1. Vérifier le rendu mobile et desktop.
2. Tester les trois langues (FR, EN, ES), les liens et la navigation clavier.
3. Vérifier que le bouton principal ouvre bien l'application SOW IA et que l'authentification reste obligatoire.
4. Ajouter le domaine public et vérifier HTTPS.
5. Ajouter la notice de confidentialité et vérifier les exigences CNIL applicables avant d'activer la mesure d'audience.
6. Activer Cloudflare Web Analytics dans **Workers & Pages → projet → Metrics → Web Analytics**, puis vérifier l'arrivée des données.

## Limites de mesure

Cloudflare Web Analytics fournit des mesures d'audience et de performance, mais ne mesure pas les clics sur les boutons via des événements personnalisés. Ne pas présenter les clics CTA comme une statistique disponible avec ce seul outil.

## Sécurité et séparation

- Ne pas modifier les secrets, l'authentification Streamlit, Supabase ou les politiques RLS.
- Ne jamais ajouter de clé API ou de jeton Cloudflare au code source.
- Si un déploiement par GitHub Actions est choisi ultérieurement, stocker les identifiants requis uniquement dans les secrets du dépôt et limiter leurs permissions.
- La page publique reste un site statique indépendant ; elle ne donne pas accès aux données privées de l'application.

## Ressources officielles

- [Cloudflare Pages — Git integration](https://developers.cloudflare.com/pages/get-started/git-integration/)
- [Cloudflare Pages — configuration](https://developers.cloudflare.com/pages/configuration/build-configuration/)
- [Cloudflare Web Analytics — installation](https://developers.cloudflare.com/web-analytics/get-started/)
- [CNIL — solutions de mesure d'audience](https://www.cnil.fr/fr/cookies-solutions-pour-les-outils-de-mesure-daudience)
