.PHONY: install-api install-web api web test lint compose-up compose-down

install-api:
	uv sync --project apps/api --extra dev

install-web:
	npm --prefix apps/web ci

api:
	uv run --project apps/api uvicorn geodashboard_api.main:app --reload

web:
	npm --prefix apps/web run dev

test:
	uv run --project apps/api pytest -c apps/api/pyproject.toml apps/api/tests
	npm --prefix apps/web run test

lint:
	uv run --project apps/api ruff check apps/api
	uv run --project apps/api ruff format --check apps/api
	uv run --project apps/api mypy --config-file apps/api/pyproject.toml apps/api/src
	npm --prefix apps/web run lint

compose-up:
	docker compose up --build

compose-down:
	docker compose down
