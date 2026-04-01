"""Static typing tests validated by pyright.

These are NOT executed — they only need to type-check cleanly.
"""

from artdeco import decorator

# --- Sync decorator factory ------------------------------------------------


@decorator()
def logged(call, prefix: str):
    return call()


@logged("hello")
def add(a: int, b: int) -> int:
    return a + b


result: int = add(1, 2)


# --- Async decorator factory ------------------------------------------------


@decorator()
async def alogged(call, prefix: str):
    return await call()


@alogged("hello")
async def mul(a: int, b: int) -> int:
    return a * b


# --- Decorator with extra keyword arguments ---------------------------------


@decorator()
def with_default(call, tag: str, *, retries: int = 3):
    for _ in range(retries):
        val = call()
        if val is not None:
            return val
    return None


@with_default("cache", retries=5)
def fetch(url: str) -> str | None:
    return url


fetch_result: str | None = fetch("https://example.com")
