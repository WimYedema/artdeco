# artdeco

**artdeco** is a tiny, zero-dependency Python library that makes writing
decorator factories effortless: works with plain functions and instance methods,
for both synchronous and asynchronous code, and for stacking multiple decorators
in any combination.

You write one function.  `artdeco` turns it into a fully-featured, stackable
decorator factory.

## Why artdeco?

Writing a production-quality decorator factory from scratch is surprisingly
tedious:

- You need a descriptor (`__get__`) to keep `self` working on methods.
- You need `functools.wraps` to preserve `__name__`, `__doc__`, etc.
- Handling `async def` requires extra work, since `iscoroutinefunction` stops
  working once you wrap an async function without explicitly marking the wrapper.
- You need to guard against accidentally mixing sync/async.
- You want to stack multiple decorators on the same function.

**artdeco handles all of that for you.**

## Features

- **Works on methods**: decorators preserve descriptor binding so `self` is
  always correct.
- **Sync and async**: one API covers both; write `async def` to get an async
  decorator factory.
- **Stackable**: apply as many decorators as you like; ordering is preserved.
- **Inspect call internals**: `call` is a plain `functools.partial`, giving you
  access to `call.func`, `call.args`, and `call.keywords` at decoration time.
- **Misuse detection**: applying a sync decorator to an `async def` (or vice
  versa) raises a clear `DecorationError`.
- **Fully typed**: ships with `py.typed`; works with Pyright and mypy.
- **Zero dependencies**: pure Python 3.12+, uses only the standard library.

## Installation

```bash
pip install py-artdeco
```

## Quick Start

### Synchronous decorator factory

```python
from artdeco import decorator


@decorator()
def log(call, prefix: str):
    print(prefix, "calling")
    return call()


@log("DEBUG:")
def add(a: int, b: int) -> int:
    return a + b


assert add(1, 2) == 3  # prints "DEBUG: calling"
```

### Async decorator factory

```python
from artdeco import decorator


@decorator()
async def traced(call, prefix: str):
    print(prefix, "before")
    result = await call()
    print(prefix, "after")
    return result


@traced("ASYNC")
async def work(x: int) -> int:
    return x * 2
```

### Works seamlessly on instance methods

```python
from artdeco import decorator


@decorator()
def retry(call, times: int):
    for _ in range(times):
        try:
            return call()
        except Exception:
            pass
    raise RuntimeError("all retries failed")


class Client:
    @retry(times=3)
    def fetch(self) -> str:        # self is bound correctly
        ...
```

### Stack multiple decorators

```python
from artdeco import decorator


@decorator()
def log(call, label: str):
    print(f"[{label}] calling {call.func.__name__}")
    return call()


@decorator()
def validate(call):
    result = call()
    assert result is not None
    return result


@log("INFO")
@validate()
def compute(x: int) -> int:
    return x * 2
```

### Inspect the current invocation via `call`

`call` is a `functools.partial`, so the current call's arguments are always
available without any extra machinery:

```python
from artdeco import decorator


@decorator()
def audit(call, label: str):
    print(
        f"{label} | {call.func.__name__}"
        f"  args={call.args}  kwargs={call.keywords}"
    )
    return call()


@audit("AUDIT")
def transfer(amount: float, *, currency: str = "USD") -> bool:
    return True


transfer(100.0, currency="EUR")
# AUDIT | transfer  args=(100.0,)  kwargs={'currency': 'EUR'}
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
