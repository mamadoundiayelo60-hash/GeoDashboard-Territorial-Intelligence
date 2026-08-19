# ADR 001 — React, FastAPI et PostGIS

## Statut

Accepté pour la construction de GeoDashboard v2.

## Contexte

Le produit exige une carte fluide, des panneaux synchronisés, un comparateur de
scénarios et un studio de restitution. Une interface Streamlit classique limiterait
la maîtrise de l'état, de la carte et de l'identité visuelle.

## Décision

- React et TypeScript pour l'interface ;
- MapLibre GL pour la carte ;
- FastAPI pour les contrats HTTP ;
- Python géospatial pour les traitements ;
- PostgreSQL/PostGIS pour la persistance et les requêtes spatiales ;
- travaux asynchrones pour rapports et analyses longues.

## Conséquences

Le développement initial est plus exigeant, mais l'interface, la testabilité et la
séparation des responsabilités sont nettement supérieures. Cette architecture permet
également de présenter un projet full-stack géospatial crédible en entretien.
