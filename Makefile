.PHONY: up down init build-index run test lint format tag extract-integrations

up:
	docker-compose up -d

down:
	docker-compose down

init:
	uv run python -m scripts.init_db

build-index:
	uv run python -m pipeline.build_index

run:
	uv run python -m app.gradio_app

test:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

tag:
	uv run python -m pipeline.tag_mods

extract-integrations:
	uv run python -m pipeline.extract_integrations
