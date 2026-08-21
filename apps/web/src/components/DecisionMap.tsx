import { useEffect, useRef } from "react";
import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { Feature, FeatureCollection } from "geojson";
import type { DecisionResult } from "../api/decisions";
import type { TerritoryProfile } from "../api/territories";

export type DecisionLayerId = "grid" | "currentArea" | "scenarioArea" | "facilities" | "candidates";
export type DecisionLayerVisibility = Record<DecisionLayerId, boolean>;

type Props = {
  territory: TerritoryProfile;
  result: DecisionResult | null;
  comparison: number;
  visibility: DecisionLayerVisibility;
};

function popupContent(title: string, rows: Array<[string, unknown]>, source?: string) {
  const root = document.createElement("article");
  root.className = "feature-popup";
  const heading = document.createElement("strong");
  heading.textContent = title;
  root.appendChild(heading);
  rows.forEach(([label, value]) => {
    const row = document.createElement("p");
    const key = document.createElement("span");
    const content = document.createElement("b");
    key.textContent = label;
    content.textContent = String(value ?? "Non renseigné");
    row.append(key, content);
    root.appendChild(row);
  });
  if (source) {
    const attribution = document.createElement("small");
    attribution.textContent = `Source : ${source}`;
    root.appendChild(attribution);
  }
  return root;
}

export function DecisionMap({ territory, result, comparison, visibility }: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);

  useEffect(() => {
    if (!container.current || map.current) return;
    const instance = new maplibregl.Map({
      container: container.current,
      center: [1.86, 50.95],
      zoom: 11.2,
      attributionControl: false,
      style: {
        version: 8,
        sources: {
          carto: {
            type: "raster",
            tiles: ["https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png"],
            tileSize: 256,
          },
        },
        layers: [{ id: "basemap", type: "raster", source: "carto", paint: { "raster-opacity": 0.82 } }],
      },
    });
    map.current = instance;
    instance.addControl(new maplibregl.NavigationControl(), "bottom-right");
    instance.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    return () => { instance.remove(); map.current = null; };
  }, []);

  useEffect(() => {
    const current = map.current;
    if (!current) return;
    const draw = () => {
      const feature: Feature = { type: "Feature", properties: {}, geometry: territory.geometry };
      const source = current.getSource("territory") as GeoJSONSource | undefined;
      if (source) source.setData(feature);
      else {
        current.addSource("territory", { type: "geojson", data: feature });
        current.addLayer({ id: "territory", type: "line", source: "territory", paint: { "line-color": "#8ca7ff", "line-width": 2 } });
      }
      current.fitBounds([[territory.bbox[0], territory.bbox[1]], [territory.bbox[2], territory.bbox[3]]], { padding: 46, duration: 900 });
    };
    if (current.isStyleLoaded()) draw(); else current.once("style.load", draw);
  }, [territory]);

  useEffect(() => {
    const current = map.current;
    if (!current || !result) return;
    const draw = () => {
      const sources: Record<string, FeatureCollection | Feature> = {
        grid: result.demand_grid,
        facilities: result.facilities,
        candidates: result.candidates,
        currentArea: { type: "Feature", properties: {}, geometry: result.current_service_area },
        scenarioArea: { type: "Feature", properties: {}, geometry: result.scenario_service_area },
      };
      Object.entries(sources).forEach(([id, data]) => {
        const source = current.getSource(id) as GeoJSONSource | undefined;
        if (source) source.setData(data); else current.addSource(id, { type: "geojson", data });
      });
      if (!current.getLayer("grid")) current.addLayer({ id: "grid", type: "fill", source: "grid", paint: { "fill-color": ["case", ["==", ["get", "served"], false], ["interpolate", ["linear"], ["get", "vulnerability"], 35, "#29335c", 90, "#ff5c7a"], "#193d45"], "fill-opacity": 0.64, "fill-outline-color": "rgba(255,255,255,.06)" } });
      if (!current.getLayer("currentArea")) current.addLayer({ id: "currentArea", type: "line", source: "currentArea", paint: { "line-color": "#55d7cf", "line-width": 2, "line-opacity": 0.8 } });
      if (!current.getLayer("scenarioArea")) current.addLayer({ id: "scenarioArea", type: "fill", source: "scenarioArea", paint: { "fill-color": "#6cf3c5", "fill-opacity": comparison / 100 * 0.18, "fill-outline-color": "#6cf3c5" } });
      if (!current.getLayer("facilities")) current.addLayer({ id: "facilities", type: "circle", source: "facilities", paint: { "circle-color": "#f8fafc", "circle-radius": 5, "circle-stroke-color": "#17213e", "circle-stroke-width": 2 } });
      if (!current.getLayer("candidates")) current.addLayer({ id: "candidates", type: "circle", source: "candidates", paint: { "circle-color": ["case", ["==", ["get", "rank"], 1], "#ffd166", "#8ca7ff"], "circle-radius": ["case", ["==", ["get", "rank"], 1], 11, 7], "circle-stroke-color": "#091126", "circle-stroke-width": 3 } });
      current.moveLayer("facilities");
      current.moveLayer("candidates");
    };
    if (current.isStyleLoaded()) draw(); else current.once("style.load", draw);
  }, [result]);

  useEffect(() => {
    const current = map.current;
    if (!current) return;
    (Object.entries(visibility) as Array<[DecisionLayerId, boolean]>).forEach(([id, visible]) => {
      if (current.getLayer(id)) current.setLayoutProperty(id, "visibility", visible ? "visible" : "none");
    });
  }, [visibility, result]);

  useEffect(() => {
    const current = map.current;
    if (!current || !result || !current.getLayer("grid")) return;

    const interactiveLayers = ["candidates", "facilities", "grid"].filter((id) => current.getLayer(id));

    const onMapClick = (event: maplibregl.MapMouseEvent) => {
      const feature = current.queryRenderedFeatures(event.point, { layers: interactiveLayers })[0];
      if (!feature) return;

      const properties = feature.properties ?? {};
      let content: HTMLElement;
      if (feature.layer.id === "candidates") {
        content = popupContent(
          `Parcelle candidate ${String.fromCharCode(64 + Number(properties.rank))}`,
          [
            ["Rang", properties.rank],
            ["Score relatif", `${properties.score}/100`],
            ["Habitants supplémentaires", Number(properties.gained_people).toLocaleString("fr-FR")],
            ["Population vulnérable", Number(properties.vulnerable_people).toLocaleString("fr-FR")],
            ["Identifiant cadastral", properties.parcel_id],
            ["Superficie", `${Number(properties.parcel_area_m2).toLocaleString("fr-FR")} m²`],
            ["Zonage GPU", `${properties.zone_type} · ${properties.zone_label}`],
          ],
          "Moteur TerriScope · Cadastre Etalab · GPU",
        );
      } else if (feature.layer.id === "facilities") {
        content = popupContent(
          properties.name || "Équipement de santé",
          [["Catégorie", properties.amenity], ["Identifiant OSM", properties.osm_id]],
          properties.source || "OpenStreetMap",
        );
      } else {
        content = popupContent(
          "Maille de demande",
          [
            ["Population Filosofi", Number(properties.population).toLocaleString("fr-FR")],
            ["Vulnérabilité", `${properties.vulnerability}/100`],
            ["Accessibilité actuelle", properties.served ? "Desservie" : "Non desservie"],
            ["Valeur imputée", properties.imputed ? "Oui — valeur approchée" : "Non"],
          ],
          "INSEE — Filosofi 2021, carreau de 200 m",
        );
      }

      new maplibregl.Popup({ closeButton: true, maxWidth: "300px" })
        .setLngLat(event.lngLat)
        .setDOMContent(content)
        .addTo(current);
    };

    const onMouseMove = (event: maplibregl.MapMouseEvent) => {
      const hovered = current.queryRenderedFeatures(event.point, { layers: interactiveLayers }).length > 0;
      current.getCanvas().style.cursor = hovered ? "pointer" : "";
    };

    current.on("click", onMapClick);
    current.on("mousemove", onMouseMove);
    return () => {
      current.off("click", onMapClick);
      current.off("mousemove", onMouseMove);
      current.getCanvas().style.cursor = "";
    };
  }, [result]);

  useEffect(() => { if (map.current?.getLayer("scenarioArea")) map.current.setPaintProperty("scenarioArea", "fill-opacity", comparison / 100 * 0.22); }, [comparison]);
  return <div className="decision-map" ref={container} />;
}
