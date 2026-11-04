# SOW IA

Application web d'intelligence artificielle construite avec Streamlit.

## Modules présents

- Interface d'accueil SOW IA
- Assistant conversationnel via API compatible OpenAI
- Historique local des conversations avec SQLite
- Extraction de texte depuis les PDF
- Recherche web optionnelle via Tavily
- Pages préparées pour documents, export PDF et abonnement Premium

## Installation locale

1. Installer Python 3.10 ou supérieur.
2. Installer les dépendances : `pip install -r requirements.txt`.
3. Copier `.env.example` vers `.env` et renseigner les clés nécessaires.
4. Démarrer : `streamlit run app.py`.

Ne jamais déposer le fichier `.env` ni une clé API dans GitHub.

## Vérification du projet

Lancer les vérifications depuis la racine du dépôt :

```bash
python -m compileall -q .
pytest -q
```

Une action GitHub exécute également ces contrôles automatiquement à chaque pull request vers `main`.

## État des fonctionnalités

Le socle comprend l'assistant, l'historique local, l'extraction de texte PDF et la recherche web optionnelle. Les modules Stripe, gestion de comptes, création PDF avancée et stockage documentaire sécurisé restent à intégrer et tester avant mise en production. L'application n'est pas encore déclarée prête pour une utilisation publique.
