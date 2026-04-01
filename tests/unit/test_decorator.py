# pyright: reportMissingImports=false, reportArgumentType=false, reportCallIssue=false

from __future__ import annotations

import asyncio

import pytest

from artdeco import DecorationError, decorator


def test_sync_decorator_calls_wrapped() -> None:
    calls: list[str] = []

    @decorator()
    def traced(call, prefix: str):
        calls.append(prefix)
        return call()

    @traced("sync")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5
    assert calls == ["sync"]


def test_sync_decorator_preserves_method_binding() -> None:
    @decorator()
    def plus(call, offset: int):
        return call() + offset

    class Counter:
        def __init__(self, base: int) -> None:
            self.base = base

        @plus(3)
        def value(self) -> int:
            return self.base

    assert Counter(7).value() == 10


def test_sync_decorator_rejects_async_target() -> None:
    @decorator()
    def wrapped(call):
        return call()

    async def async_target() -> int:
        return 1

    with pytest.raises(DecorationError):
        wrapped()(async_target)


def test_async_decorator_rejects_sync_target() -> None:
    @decorator()
    async def wrapped(call):
        return await call()

    def sync_target() -> int:
        return 1

    with pytest.raises(DecorationError):
        wrapped()(sync_target)


def test_async_decorator_calls_wrapped() -> None:
    @decorator()
    async def traced(call, prefix: str):
        return f"{prefix}:{await call()}"

    @traced("async")
    async def compute() -> str:
        return "ok"

    assert asyncio.run(compute()) == "async:ok"


def test_async_decorator_preserves_method_binding() -> None:
    @decorator()
    async def scaled(call, multiplier: int):
        return (await call()) * multiplier

    class Data:
        def __init__(self, value: int) -> None:
            self.value = value

        @scaled(2)
        async def read(self) -> int:
            return self.value

    assert asyncio.run(Data(9).read()) == 18
