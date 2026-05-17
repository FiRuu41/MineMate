# Contributing to MineMate

## Contributors

- **FuRui** ([@FiRuu41](https://github.com/FiRuu41)) — 项目主理人
- **Claude Code** (Anthropic) — AI 辅助开发
- **DeepSeek** — LLM 推理

## Setup
```bash
git clone https://github.com/FiRuu41/MineMate.git
cd minemate
cp .env.example .env
uv sync
docker-compose up -d
uv run python -m scripts.init_db
```

## Code Style
- Python 3.11+, type hints
- ruff lint (E, F, I, UP, B)
- Tests with pytest

## Adding a New Tool
1. Create `tools/your_tool.py` with a function that returns dict/list
2. Add the intent to `config/prompts/router.txt`
3. Add to `VALID_INTENTS` in `agents/router.py`
4. Add a branch in `agents/workflow.py`

## Pull Request
1. Write tests for new functionality
2. Run `uv run pytest` - all tests must pass
3. Run `uv run ruff check .` - no lint errors
