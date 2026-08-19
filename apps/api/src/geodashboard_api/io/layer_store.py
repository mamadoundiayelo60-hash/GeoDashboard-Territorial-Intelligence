"""Stockage temporaire isolé par identifiant de session."""

import builtins
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import geopandas as gpd

from geodashboard_api.models import HistoryEvent, LayerSummary


class LayerStore:
    """Persiste uniquement dans un chemin dérivé d'UUID validés."""

    def __init__(self, root: Path, session_id: UUID) -> None:
        self.directory = root.resolve() / str(session_id)
        self.directory.mkdir(parents=True, exist_ok=True)

    def save(self, layer: LayerSummary, frame: gpd.GeoDataFrame) -> None:
        """Enregistre une version GeoJSON normalisée et ses métadonnées."""
        frame.to_crs(4326).to_file(self.directory / f"{layer.id}.geojson", driver="GeoJSON")
        (self.directory / f"{layer.id}.json").write_text(layer.model_dump_json(), encoding="utf-8")

    def list(self) -> list[LayerSummary]:
        """Charge le catalogue sans suivre de chemins fournis par l'utilisateur."""
        layers: list[LayerSummary] = []
        for path in sorted(self.directory.glob("*.json")):
            layers.append(LayerSummary.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return layers

    def load_frame(self, layer_id: UUID) -> gpd.GeoDataFrame:
        """Charge une couche canonique à partir d'un UUID déjà validé."""
        path = self.directory / f"{layer_id}.geojson"
        if not path.exists():
            raise FileNotFoundError(layer_id)
        return gpd.read_file(path, engine="pyogrio")

    def delete(self, layer_id: UUID) -> bool:
        """Supprime les deux fichiers canoniques d'une couche."""
        removed = False
        for suffix in (".json", ".geojson"):
            path = self.directory / f"{layer_id}{suffix}"
            if path.exists():
                path.unlink()
                removed = True
        return removed

    def record_event(
        self, event_type: str, summary: str, parameters: dict[str, object]
    ) -> HistoryEvent:
        """Ajoute une ligne JSONL dans le journal isolé de la session."""
        event = HistoryEvent(
            id=str(uuid4()),
            event_type=event_type,
            summary=summary,
            parameters=parameters,
            created_at=datetime.now(UTC).isoformat(),
        )
        with (self.directory / "history.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(event.model_dump_json() + "\n")
        return event

    def history(self) -> builtins.list[HistoryEvent]:
        """Retourne les événements les plus récents en premier."""
        path = self.directory / "history.jsonl"
        if not path.exists():
            return []
        events = [HistoryEvent.model_validate_json(line) for line in path.read_text().splitlines()]
        return list(reversed(events[-100:]))
