# FINAL TEC — transaction atomique des deux nonces et du journal d'audit

## Ajout
`final_tec_atomic_approval_store.py` fournit un stockage local SQLite qui
regroupe dans une seule transaction :
1. la vérification de l'existence des deux nonces attendus ;
2. le contrôle de leur association à la même autorisation ;
3. le contrôle de leur expiration, révocation et consommation antérieure ;
4. la consommation des deux nonces ;
5. l'ajout d'un événement au journal d'audit chaîné par SHA-256.

Si l'une des deux consommations ou l'écriture d'audit échoue, la transaction
est annulée : aucun nonce n'est consommé et aucun événement partiel n'est écrit.

Le moteur double approbation accepte désormais
`atomic_pair_audit_commit`. Cette interface est la voie à utiliser pour le
stockage transactionnel. Les anciens callbacks séparés restent uniquement
pour compatibilité avec les tests et prototypes antérieurs ; cette voie n'est
pas atomique entre consommation et audit.

## Contrôles ajoutés aux tests
- concurrence entre plusieurs consommateurs du même couple ;
- une seule transaction gagnante et un seul événement d'audit ;
- révocation d'un des deux nonces ;
- couple incomplet ou mal associé ;
- échec simulé de l'insertion d'audit et rollback des deux nonces ;
- reprise après réouverture de la base ;
- interdiction applicative UPDATE/DELETE sur les lignes d'audit ;
- détection d'une modification directe du journal par vérification de chaîne ;
- intégration du callback transactionnel au moteur.

## Limites
- SQLite est ici un stockage local mono-hôte, pas un registre distribué ni
  une base adaptée au partage entre plusieurs serveurs.
- Les triggers protègent contre les modifications ordinaires via l'application,
  mais un administrateur privilégié capable de modifier le fichier ou le schéma
  peut contourner ces protections. La chaîne SHA-256 est détectable, pas
  immuable face à un administrateur hostile.
- Aucun service de sauvegarde, réplication, KMS/HSM, OIDC, MFA, annuaire
  d'identité ou contrôle d'accès serveur réel n'est configuré.
- Aucun déploiement, workload ou autorisation d'exécution n'est inclus.

## Statut
Prototype local isolé, PR en brouillon. Les tests CI doivent être confirmés
sur la tête finale de la branche. G2-B reste **NO-GO / NOT_RUN**.
