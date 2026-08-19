# Spécification produit

## 1. Promesse

GeoDashboard transforme un territoire communal et des données géographiques en
diagnostic, scénarios d'aménagement et livrables décisionnels.

Le produit répond à quatre verbes :

- **Explorer** un territoire et ses données ;
- **Diagnostiquer** les écarts spatiaux ;
- **Simuler** une intervention ;
- **Décider** à l'aide de comparaisons documentées.

## 2. Utilisateurs

### Chargé d'étude territorial

Souhaite évaluer la couverture d'équipements sans reconstruire une chaîne SIG à
chaque étude.

### Géomaticien

Souhaite contrôler les données, exécuter des requêtes PostGIS, créer des champs et
conserver la traçabilité des traitements.

### Décideur

Souhaite comprendre les écarts, comparer des scénarios et obtenir une synthèse
lisible sans manipuler un logiciel SIG.

## 3. Démonstration phare

1. Rechercher « Calais » et sélectionner la commune identifiée par son code INSEE.
2. Afficher automatiquement son contour et son profil territorial.
3. Choisir le thème « accès aux équipements de santé ».
4. Calculer la couverture actuelle et localiser les secteurs déficitaires.
5. Ajouter un équipement hypothétique sur la carte.
6. Recalculer instantanément les indicateurs.
7. Comparer situation initiale et scénario avec un curseur cartographique.
8. Générer un brief PDF et un GeoPackage documenté.

## 4. Modules

### Territoire

- recherche par nom, code postal ou code INSEE ;
- sélection non ambiguë avec département et région ;
- contour, emprise, superficie, population et densité ;
- conservation du code INSEE comme identifiant métier ;
- cache et reprise contrôlée en cas d'indisponibilité du service.

### Catalogue de données

- API nationales et services IGN ;
- PostgreSQL/PostGIS ;
- GeoJSON, GeoPackage, Shapefile ZIP, KML et CSV géographique ;
- métadonnées, source, millésime, licence et attribution ;
- diagnostic automatique de qualité.

### Carte

- rendu MapLibre GL ;
- styles catégoriels, gradués, proportionnels et heatmap ;
- sélection clic, rectangle et polygone ;
- légende, mesure, géocodage et info-bulles ;
- comparaison avant/après ;
- synchronisation avec tables et graphiques.

### Diagnostics guidés

- couverture d'équipements ;
- proximité et zones déficitaires ;
- comparaison de territoires ;
- comparaison de scénarios ;
- implantation multicritère expliquée.

### Atelier expert

- requêtes PostGIS en lecture seule ;
- constructeur visuel de requêtes ;
- champs calculés avec langage d'expression contrôlé ;
- buffer, intersection, différence, dissolution, jointure et sélection spatiales ;
- historique et manifeste reproductible.

### Restitution

- modèles A4/A3 portrait et paysage ;
- studio de composition par blocs ;
- carte, légende, graphiques, tableaux, sources et limites ;
- PDF, PNG, GeoJSON, GeoPackage, CSV et manifeste JSON.

## 5. Indicateurs du diagnostic de couverture

- nombre d'équipements ;
- équipements pour 10 000 habitants ;
- surface et population potentiellement couvertes ;
- surface et population hors couverture ;
- taux de couverture ;
- score par secteur ;
- gain absolu et relatif d'un scénario ;
- secteurs prioritaires avec justification.

Le produit distingue explicitement couverture géométrique, distance réseau et temps
d'accès. Il n'assimile jamais un buffer à un temps réel de déplacement.

## 6. Critères d'effet démonstration

- territoire visible moins de deux secondes après une réponse mise en cache ;
- changement de scénario perçu comme instantané sur un cas préparé ;
- carte, indicateurs et graphiques mis à jour ensemble ;
- comparaison avant/après compréhensible sans explication orale ;
- premier rapport généré en moins de quinze secondes sur le scénario de référence ;
- aucune erreur technique brute affichée à l'utilisateur.

Ces objectifs seront mesurés dans l'environnement de démonstration et documentés ;
ils ne seront pas annoncés avant validation.

## 7. Hors périmètre initial

- édition topologique complète ;
- géoréférencement raster ;
- moteur de géotraitement généraliste ;
- rendu cartographique d'impression équivalent à QGIS ;
- écriture SQL libre sur une base de production ;
- recommandations opaques ou présentées comme prescriptions.

## 8. Définition de terminé

Une fonctionnalité est terminée lorsqu'elle possède : contrat typé, contrôle de
sécurité, tests unitaires, cas d'erreur utilisateur, journal de traitement,
documentation et validation visuelle.
