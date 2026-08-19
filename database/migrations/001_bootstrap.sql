CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS geodashboard;

CREATE TABLE IF NOT EXISTS geodashboard.project (
    id uuid PRIMARY KEY,
    name text NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    territory_code text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS geodashboard.audit_event (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id uuid REFERENCES geodashboard.project(id) ON DELETE CASCADE,
    event_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_event_project_idx
    ON geodashboard.audit_event(project_id, created_at DESC);
