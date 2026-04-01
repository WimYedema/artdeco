# artdeco

Method-aware decorator factories for Python functions and methods, with support for both synchronous and asynchronous decorator implementations.

## Features

- Create decorators that work for plain functions and bound instance methods.
- Use the same high-level API for sync and async decorator implementations.
- Prevent mismatched usage (sync decorator applied to async function, and vice versa).
- Typed package with `py.typed` included.

## Installation

```bash
pip install artdeco
```

## Quick Start

```python
from artdeco import decorator


@decorator()
def log(call, prefix: str):
	print(prefix, "calling")
	return call()


@log("DEBUG:")
def add(a: int, b: int) -> int:
	return a + b


assert add(1, 2) == 3
```

Async example:

```python
from artdeco import decorator


@decorator()
async def traced(call, prefix: str):
	print(prefix, "before")
	return await call()


@traced("ASYNC")
async def work(x: int) -> int:
	return x * 2
```

## Development

This project uses `uv` for environment and dependency management.

Install tools and dependencies:

```bash
uv sync --group dev
```

Run checks:

```bash
uv run ruff check .
uv run pytest
uv run pyright src
```

Run typing tests:

```bash
uv run pyright src tests/typing
```

Build and validate distribution metadata:

```bash
uv build
uv run twine check dist/*
```

## License

MIT, see [LICENSE](LICENSE).
