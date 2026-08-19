CREATE TABLE IF NOT EXISTS geodashboard.dataset (
    id uuid PRIMARY KEY,
    project_id uuid REFERENCES geodashboard.project(id) ON DELETE CASCADE,
    name text NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    source_format text NOT NULL,
    feature_count integer NOT NULL DEFAULT 0 CHECK (feature_count >= 0),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS geodashboard.feature (
    dataset_id uuid NOT NULL REFERENCES geodashboard.dataset(id) ON DELETE CASCADE,
    feature_id bigint GENERATED ALWAYS AS IDENTITY,
    properties jsonb NOT NULL DEFAULT '{}'::jsonb,
    geometry geometry(Geometry, 4326) NOT NULL,
    PRIMARY KEY (dataset_id, feature_id)
);

CREATE INDEX IF NOT EXISTS feature_geometry_gix ON geodashboard.feature USING gist(geometry);
CREATE INDEX IF NOT EXISTS feature_properties_gin ON geodashboard.feature USING gin(properties);

CREATE OR REPLACE VIEW geodashboard.v_projects AS
SELECT id, name, territory_code, created_at, updated_at FROM geodashboard.project;

CREATE OR REPLACE VIEW geodashboard.v_datasets AS
SELECT id, project_id, name, source_format, feature_count, metadata, created_at
FROM geodashboard.dataset;

CREATE OR REPLACE VIEW geodashboard.v_features AS
SELECT dataset_id, feature_id, properties, geometry FROM geodashboard.feature;
