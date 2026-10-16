# Aqil research worker

Python 3.13 analytics and source-integration worker managed with [uv](https://docs.astral.sh/uv/).

## Setup

```powershell
uv sync
```

## Commands

```powershell
uv run pytest
uv run ruff check .
uv run ruff format .
uv run aqil-research
```

External financial APIs and LLM providers are not connected during initial scaffolding.
