# Politique de sécurité

## Signaler une vulnérabilité

Merci de ne pas ouvrir d'issue publique contenant une preuve de concept sensible.
Contactez l'auteur via son profil GitHub en décrivant la version, l'impact et les
étapes minimales de reproduction. Un accusé de réception sera fourni sous 72 heures.

## Garanties de la version actuelle

- fichiers bornés, signatures contrôlées et extraction ZIP défensive ;
- sessions isolées par UUID ;
- expressions calculées interprétées par une grammaire sans `eval` ;
- SQL limité à un `SELECT` sur les vues `geodashboard.v_*` ;
- transaction SQL read-only, timeout de 3 secondes et 200 lignes maximum ;
- CORS explicite, en-têtes de sécurité et erreurs techniques masquées ;
- secrets fournis exclusivement par variables d'environnement.

Voir [le modèle de sécurité détaillé](docs/security-model.md).
