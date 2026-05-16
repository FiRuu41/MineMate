.PHONY: up down init crawl-demo build-index run test lint format

up:
	docker-compose up -d

down:
	docker-compose down

init:
	uv run python -m scripts.init_db

crawl-demo:
	uv run python -m pipeline.crawl --mods create jei botania

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
