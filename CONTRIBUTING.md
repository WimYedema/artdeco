# Contributing

Thanks for your interest in contributing.

## Development Setup

1. Install `uv`.
2. Sync the development environment:

```bash
uv sync --group dev
```

## Checks

Run lint and type checks:

```bash
uv run ruff check .
uv run pyright src
```

Run unit tests:

```bash
uv run pytest
```

Run typing tests:

```bash
uv run pyright src tests/typing
```

Build and validate package metadata:

```bash
uv build
uv run twine check dist/*
```

## Pull Requests

- Keep changes focused and small.
- Add or update documentation for behavior changes.
- Ensure CI passes before requesting review.
