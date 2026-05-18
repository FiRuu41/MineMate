.PHONY: init build-index build-tags run test lint format tag extract-integrations

init:
	uv run python -m scripts.init_db

build-index:
	uv run python -m pipeline.build_index

build-tags:
	uv run python -m pipeline.tag_mods --workers 10

run:
	uv run minemate start

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
