# Post LinkedIn

J'ai repensé GeoDashboard comme un véritable studio d'intelligence territoriale.

Le constat de départ était simple : un logiciel SIG sait produire un buffer ou une
intersection, mais un décideur cherche surtout à comprendre quels secteurs sont mal
desservis, quel serait l'impact d'une nouvelle implantation et comment restituer le
résultat de manière transparente.

GeoDashboard permet désormais de sélectionner automatiquement une commune française,
d'importer des données SIG, d'en contrôler la qualité, de mesurer une couverture
territoriale et de comparer un scénario d'aménagement ajouté directement sur la carte.
L'application génère ensuite un rapport PDF décisionnel ainsi que des exports GeoJSON,
GeoPackage et un manifeste reproductible.

La stack associe React, TypeScript et MapLibre GL côté interface, FastAPI, GeoPandas,
Shapely et ReportLab côté moteur, ainsi que PostgreSQL/PostGIS pour l'atelier expert.
Les imports, expressions calculées et requêtes SQL sont traités comme des entrées non
fiables et soumis à des contrôles dédiés.

Le mode démo utilise 103 équipements ouverts de Calais issus d'OpenStreetMap.

GitHub : https://github.com/mamadoundiayelo60-hash/GeoDashboard-Territorial-Intelligence

Démo : à ajouter après le premier déploiement Render.

#geomatique #SIG #GIS #Python #PostGIS #React #DataEngineering #OpenData
