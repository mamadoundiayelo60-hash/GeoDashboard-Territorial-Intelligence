# Modèle de sécurité

## Frontières de confiance

Sont non fiables : fichiers importés, archives, KML/XML, CSV, expressions calculées,
requêtes SQL, paramètres d'API, noms de fichiers, métadonnées et services distants.

## Import de fichiers

- extensions et signatures autorisées ;
- taille, nombre de fichiers, entités, champs et sommets limités ;
- extraction ZIP sans chemins absolus ni `..` ;
- refus des liens symboliques ;
- analyse KML/XML sans entités externes ;
- répertoire isolé par opération ;
- noms de fichiers générés côté serveur ;
- nettoyage à expiration ;
- aucune désérialisation Python non sûre.

## PostgreSQL/PostGIS

- compte en lecture seule par défaut ;
- secrets exclusivement côté serveur ;
- chiffrement TLS configurable ;
- schémas et tables autorisés ;
- analyse syntaxique SQL ;
- une instruction `SELECT` ou `WITH ... SELECT` ;
- refus des fonctions et commandes dangereuses ;
- timeout, limite de lignes et mémoire contrôlée ;
- annulation et journalisation ;
- aucune valeur utilisateur concaténée au SQL.

## Champs calculés

- grammaire dédiée ;
- arbre syntaxique validé ;
- fonctions autorisées explicitement ;
- types d'entrée et de sortie contrôlés ;
- prévisualisation limitée ;
- absence de `eval`, import ou accès au système.

## Services externes

- liste d'hôtes autorisés ;
- délais et taille de réponse limités ;
- redirections contrôlées ;
- validation du contenu ;
- cache borné ;
- circuit breaker et messages fonctionnels.

## API applicative

- validation stricte des schémas ;
- CORS limité ;
- en-têtes de sécurité ;
- quotas par opération ;
- identifiants non prédictibles ;
- séparation des projets ;
- absence de traces sensibles dans les réponses ;
- journal d'audit sans secrets.

## Tests obligatoires

- ZIP Slip et bombes d'archives ;
- XML External Entity ;
- fichier déguisé ;
- géométrie pathologique ;
- injection SQL ;
- expression hostile ;
- dépassement de quotas ;
- accès croisé entre projets ;
- expiration des ressources temporaires.
