# SOW IA — plan de secours SMTP Amazon SES

## État
- Fournisseur actuellement configuré : Brevo (ne pas modifier sans décision explicite).
- Le journal Brevo a déjà confirmé un rejet de l'expéditeur non validé.
- Le compte de connexion SOW IA `sowla@live.fr` reste inchangé.
- Cette procédure est préparatoire : aucun identifiant AWS/Supabase n'est stocké dans le dépôt.

## Compatibilité
Supabase Auth accepte tout fournisseur SMTP compatible. Le remplacement de Brevo par SES se fait dans les paramètres SMTP Auth de Supabase ; il ne nécessite pas de modification du code de connexion SOW IA.

## Paramètres régionaux envisagés
- Région AWS : Europe (Paris), `eu-west-3`.
- Hôte SMTP : `email-smtp.eu-west-3.amazonaws.com`.
- Port recommandé : `587` avec STARTTLS.
- Nom d'utilisateur / mot de passe : identifiants SMTP SES générés spécifiquement pour la région `eu-west-3` (ils ne sont pas les clés d'accès AWS ordinaires).
- Nom d'expéditeur : `SOW IA`.
- Adresse expéditeur : uniquement une identité SES vérifiée et autorisée.

## Conditions avant tout basculement
1. Créer/accéder au compte AWS et activer Amazon SES dans `eu-west-3`.
2. Vérifier une identité d'expéditeur dans SES. Une adresse individuelle peut être vérifiée pour les essais ; pour une délivrabilité durable, privilégier un domaine contrôlé par SOW IA avec DKIM/SPF/DMARC.
3. Générer les identifiants SMTP SES dans la même région.
4. Demander à AWS la sortie du mode sandbox avant tout envoi à des destinataires non vérifiés. En sandbox, les destinataires doivent eux aussi être vérifiés.
5. Conserver les identifiants uniquement dans le tableau de bord Supabase (jamais dans GitHub, le code ou les messages ChatGPT).

## Basculement contrôlé (à exécuter uniquement après accord)
Dans le projet Supabase TEST, remplacer temporairement les seuls champs SMTP par les valeurs SES :
- Host : `email-smtp.eu-west-3.amazonaws.com`
- Port : `587`
- Username / Password : identifiants SMTP SES de la région Paris
- Sender email : adresse vérifiée dans SES
- Sender name : `SOW IA`

Faire un seul test vers une boîte de test vérifiée, puis contrôler les journaux SES et Supabase Auth. En cas d'échec, restaurer les paramètres Brevo conservés séparément. Ne jamais modifier le projet Supabase de production pendant cette validation.

## Garde-fous
- Ne pas modifier l'adresse de connexion des utilisateurs.
- Ne pas modifier les modèles Magic Link ni les flux OAuth.
- Ne pas désactiver la confirmation e-mail.
- Ne pas fusionner la branche de fonctionnalité ni modifier l'application principale pour ce chantier SMTP.
- Ne jamais demander ni enregistrer ici les clés AWS, mots de passe SMTP, clés Supabase ou jetons.

## Références officielles
- Supabase — SMTP personnalisé : https://supabase.com/docs/guides/auth/auth-smtp
- AWS — points de terminaison SES : https://docs.aws.amazon.com/fr_fr/general/latest/gr/ses.html
- AWS — identifiants SMTP SES : https://docs.aws.amazon.com/ses/latest/dg/smtp-credentials.html
- AWS — envoi SMTP et exigences d'identité : https://docs.aws.amazon.com/fr_fr/ses/latest/dg/send-using-smtp-programmatically.html
