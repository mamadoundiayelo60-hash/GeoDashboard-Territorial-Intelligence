import { useEffect, useRef } from "react";
import maplibregl, { type GeoJSONSource, type Map as MapLibreMap } from "maplibre-gl";
import type { Feature, FeatureCollection } from "geojson";
import type { LayerSummary } from "../api/layers";
import type { CoverageResult, ScenarioLocation } from "../api/diagnostics";
import type { TerritoryProfile } from "../api/territories";
import { layerColor } from "../utils/layerColors";

const territorySource = "active-territory";

type Props = { territory: TerritoryProfile | null; layers: LayerSummary[]; visibleIds: Set<string>; diagnostic: CoverageResult | null; scenarioLocations: ScenarioLocation[]; placingScenario: boolean; onScenarioMapClick: (location: ScenarioLocation) => void };

export function MapCanvas({ territory, layers, visibleIds, diagnostic, scenarioLocations, placingScenario, onScenarioMapClick }: Props) {
  const container = useRef<HTMLDivElement | null>(null);
  const map = useRef<MapLibreMap | null>(null);
  const renderedLayerIds = useRef<Set<string>>(new Set());
  const placingScenarioRef = useRef(placingScenario);
  const scenarioClickRef = useRef(onScenarioMapClick);
  useEffect(() => {
    if (!container.current || map.current) return;
    const instance = new maplibregl.Map({ container: container.current, center: [2.3, 46.6], zoom: 4.7, attributionControl: false, style: { version: 8, sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, attribution: "© OpenStreetMap contributors" } }, layers: [{ id: "osm", type: "raster", source: "osm" }] } });
    map.current = instance;
    instance.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    instance.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    instance.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: "GeoDashboard" }), "bottom-right");
    const handleScenarioClick = (event: maplibregl.MapMouseEvent) => {
      if (!placingScenarioRef.current) return;
      scenarioClickRef.current({ longitude: event.lngLat.lng, latitude: event.lngLat.lat });
    };
    instance.on("click", handleScenarioClick);
    return () => { instance.off("click", handleScenarioClick); instance.remove(); map.current = null; };
  }, []);
  useEffect(() => {
    placingScenarioRef.current = placingScenario;
    scenarioClickRef.current = onScenarioMapClick;
    if (map.current) map.current.getCanvas().style.cursor = placingScenario ? "crosshair" : "";
  }, [placingScenario, onScenarioMapClick]);
  useEffect(() => {
    const currentMap = map.current;
    if (!currentMap || !territory) return;
    const feature: Feature = { type: "Feature", properties: { code: territory.code, name: territory.name }, geometry: territory.geometry };
    const update = () => {
      const source = currentMap.getSource(territorySource) as GeoJSONSource | undefined;
      if (source) source.setData(feature);
      else {
        currentMap.addSource(territorySource, { type: "geojson", data: feature });
        currentMap.addLayer({ id: "territory-fill", type: "fill", source: territorySource, paint: { "fill-color": "#6d49c9", "fill-opacity": 0.2 } });
        currentMap.addLayer({ id: "territory-outline", type: "line", source: territorySource, paint: { "line-color": "#f6b73c", "line-width": 3 } });
      }
      const [west, south, east, north] = territory.bbox;
      currentMap.fitBounds([[west, south], [east, north]], { padding: 70, duration: 1200 });
    };
    if (currentMap.loaded()) update(); else currentMap.once("load", update);
  }, [territory]);
  useEffect(() => {
    const currentMap = map.current;
    if (!currentMap) return;
    const updateLayers = () => {
      const activeIds = new Set(layers.map((layer) => layer.id));
      renderedLayerIds.current.forEach((id) => {
        if (activeIds.has(id)) return;
        const sourceId = `user-${id}`;
        for (const suffix of ["fill", "line", "point"]) {
          const mapLayerId = `${sourceId}-${suffix}`;
          if (currentMap.getLayer(mapLayerId)) currentMap.removeLayer(mapLayerId);
        }
        if (currentMap.getSource(sourceId)) currentMap.removeSource(sourceId);
        renderedLayerIds.current.delete(id);
      });
      layers.forEach((layer, index) => {
      const sourceId = `user-${layer.id}`;
      const color = layerColor(index);
      const source = currentMap.getSource(sourceId) as GeoJSONSource | undefined;
      if (!source && layer.preview) {
        renderedLayerIds.current.add(layer.id);
        currentMap.addSource(sourceId, { type: "geojson", data: layer.preview });
        currentMap.addLayer({ id: `${sourceId}-fill`, type: "fill", source: sourceId, filter: ["==", ["geometry-type"], "Polygon"], paint: { "fill-color": color, "fill-opacity": 0.32 } });
        currentMap.addLayer({ id: `${sourceId}-line`, type: "line", source: sourceId, filter: ["in", ["geometry-type"], ["literal", ["LineString", "Polygon"]]], paint: { "line-color": color, "line-width": 2.5 } });
        currentMap.addLayer({ id: `${sourceId}-point`, type: "circle", source: sourceId, filter: ["==", ["geometry-type"], "Point"], paint: { "circle-color": color, "circle-radius": 6, "circle-stroke-color": "#ffffff", "circle-stroke-width": 1.5 } });
      }
      for (const suffix of ["fill", "line", "point"]) {
        const id = `${sourceId}-${suffix}`;
        if (currentMap.getLayer(id)) currentMap.setLayoutProperty(id, "visibility", visibleIds.has(layer.id) ? "visible" : "none");
      }
      });
    };
    if (currentMap.loaded()) updateLayers(); else currentMap.once("load", updateLayers);
  }, [layers, visibleIds]);
  useEffect(() => {
    const currentMap = map.current;
    if (!currentMap) return;
    const update = () => {
      const collection: FeatureCollection = { type: "FeatureCollection", features: scenarioLocations.map((location, index) => ({ type: "Feature", properties: { index }, geometry: { type: "Point", coordinates: [location.longitude, location.latitude] } })) };
      const scenarioSource = currentMap.getSource("scenario-sites") as GeoJSONSource | undefined;
      if (scenarioSource) scenarioSource.setData(collection); else {
        currentMap.addSource("scenario-sites", { type: "geojson", data: collection });
        currentMap.addLayer({ id: "scenario-sites", type: "circle", source: "scenario-sites", paint: { "circle-color": "#f6b73c", "circle-radius": 9, "circle-stroke-color": "#111827", "circle-stroke-width": 3 } });
      }
      if (!diagnostic) return;
      const diagnosticCollection: FeatureCollection = { type: "FeatureCollection", features: [
        { type: "Feature", properties: { state: "current" }, geometry: diagnostic.covered_geometry },
        { type: "Feature", properties: { state: "scenario" }, geometry: diagnostic.scenario_covered_geometry },
      ] };
      const diagnosticSource = currentMap.getSource("coverage-result") as GeoJSONSource | undefined;
      if (diagnosticSource) diagnosticSource.setData(diagnosticCollection); else {
        currentMap.addSource("coverage-result", { type: "geojson", data: diagnosticCollection });
        currentMap.addLayer({ id: "coverage-current", type: "fill", source: "coverage-result", filter: ["==", ["get", "state"], "current"], paint: { "fill-color": "#7452c8", "fill-opacity": .25 } });
        currentMap.addLayer({ id: "coverage-scenario", type: "fill", source: "coverage-result", filter: ["==", ["get", "state"], "scenario"], paint: { "fill-color": "#14b8a6", "fill-opacity": .38, "fill-outline-color": "#087d73" } });
      }
      if (currentMap.getLayer("scenario-sites")) currentMap.moveLayer("scenario-sites");
    };
    if (currentMap.loaded()) update(); else currentMap.once("load", update);
  }, [diagnostic, scenarioLocations]);
  return <div ref={container} className="map-canvas" />;
}
