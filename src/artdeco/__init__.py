"""Utilities for creating method-aware synchronous and asynchronous decorator factories.

This module provides a single high-level helper, the `decorator` class, plus a small set
of internal helpers used to make decorators that:
- Work for both free functions and bound instance methods (preserve descriptor behavior).
- Support both synchronous and asynchronous decorator implementations.
- Validate that a sync decorator is not applied to an async function and vice versa.
- Pass the original function invocation to the decorator implementation as the
    first positional argument "call" (a functools.partial calling the wrapped function
    with the current call's arguments).  Because ``call`` is a plain
    ``functools.partial``, its attributes are accessible inside the decorator:
    ``call.func`` is the underlying wrapped function, ``call.args`` contains the
    positional arguments of the current invocation, and ``call.keywords`` contains
    the keyword arguments of the current invocation.

Key components
----------------
_SyncMethodAwareWrapper
        Small descriptor-compatible wrapper returned for synchronous decorated functions.
        It implements __get__ so that decorating instance methods preserves binding to the
        instance. Its __call__ simply invokes the wrapped function.
_AsyncMethodAwareWrapper
        Analogous to _SyncMethodAwareWrapper but for async functions. Its __call__ returns
        an awaitable.
DecorationError
        Exception raised when a decorator of one "kind" (sync/async) is applied to a function
        of the opposite kind. The error message includes the decorator name and the target
        function name.
decorator
        A factory class used as a decorator factory generator. Usage pattern:
                @decorator()
                def my_decorator(call, ...):
                        # for synchronous decorator implementations:
                        # - call() to invoke the original function and return its result,
                        #   or return some transformed value.
                        return call()
                @my_decorator(...)
                def wrapped(...):
        or for async decorator implementations:
                @decorator()
                async def my_async_decorator(call, ...):
                        # call is a callable partial wrapping the original async function
                        return await call()
                @my_async_decorator(...)
                async def wrapped_async(...):

Examples:
---------
Synchronous decorator example:
        @decorator()
        def log_call(call, prefix: str):
                print(prefix, "calling")
                return call()
        @log_call("DEBUG:")
        def add(a, b):
                return a + b
        add(1, 2)  # prints "DEBUG: calling" and returns 3

Asynchronous decorator example:
        @decorator()
        async def async_log(call, prefix: str):
                print(prefix, "about to await")
                return await call()
        @async_log("ASYNC:")
        async def fetch(x):
                return x * 2
        await fetch(3)  # prints and returns 6

Accessing partial internals example:
        The ``call`` parameter is a ``functools.partial``, so its underlying
        function and the arguments of the current invocation are available:
        @decorator()
        def verbose(call, label: str):
                func_name = call.func.__name__      # name of the wrapped function
                positional = call.args              # tuple of positional args
                keyword = call.keywords             # dict of keyword args
                print(f"{label} calling {func_name}{positional} {keyword}")
                return call()
        @verbose("LOG")
        def add(a, b):
                return a + b
        add(1, b=2)  # prints "LOG calling add(1,) {'b': 2}" and returns 3
"""

from collections.abc import Awaitable, Callable
from functools import partial, update_wrapper, wraps
from inspect import iscoroutinefunction, markcoroutinefunction
from typing import Any, Concatenate, Generic, ParamSpec, TypeVar

DecResultT = TypeVar("DecResultT")
DecParams = ParamSpec("DecParams")
FuncResultT = TypeVar("FuncResultT")
FuncParams = ParamSpec("FuncParams")
InstanceT = TypeVar("InstanceT")

DecoratedFunctionT = Callable[FuncParams, FuncResultT]
DecoratorT = Callable[[DecoratedFunctionT], DecoratedFunctionT]
DecoratorFactoryT = Callable[DecParams, DecoratorT]

AsyncDecoratedFunctionT = Callable[FuncParams, Awaitable[FuncResultT]]
AsyncDecoratorT = Callable[[AsyncDecoratedFunctionT], AsyncDecoratedFunctionT]
AsyncDecoratorFactoryT = Callable[DecParams, AsyncDecoratorT]


class _SyncMethodAwareWrapper(Generic[FuncParams, FuncResultT]):  # noqa: UP046 type error without Generic
    def __init__(self, func: DecoratedFunctionT) -> None:
        self._func = func

    def __get__(self, instance: InstanceT | None, owner: type[InstanceT]) -> DecoratedFunctionT:
        if instance is None:
            return self._func
        return self._func.__get__(instance, owner)

    def __call__(self, *args: FuncParams.args, **kwargs: FuncParams.kwargs) -> FuncResultT:
        return self._func(*args, **kwargs)


class _AsyncMethodAwareWrapper(Generic[FuncParams, FuncResultT]):  # noqa: UP046 type error without Generic
    def __init__(self, func: AsyncDecoratedFunctionT) -> None:
        self._func = func

    def __get__(
        self, instance: InstanceT | None, owner: type[InstanceT]
    ) -> AsyncDecoratedFunctionT:
        if instance is None:
            return self._func
        return self._func.__get__(instance, owner)

    def __call__(
        self, *args: FuncParams.args, **kwargs: FuncParams.kwargs
    ) -> Awaitable[FuncResultT]:
        return self._func(*args, **kwargs)


class DecorationError(Exception):
    """Exception raised when a decorator is misused."""

    def __init__(self, decorator_name: str, function_name: str) -> None:
        """Initialize the DecorationError.

        Args:
            decorator_name: The name of the decorator being applied.
            function_name: The name of the function being decorated.
        """
        super().__init__(
            f"Decorator '{decorator_name}' cannot be applied to function '{function_name}'."
        )


class decorator:  # noqa: N801 use lowercase for decorators
    """A decorator factory that intelligently handles both synchronous and asynchronous decorators.

    This class provides a flexible framework for creating decorators that can wrap functions
    with custom behavior. It automatically detects whether the provided decorator function is
    asynchronous or synchronous and applies the appropriate wrapping strategy.
    The decorator factory ensures type safety and prevents misuse by validating that:
    - Synchronous decorators do not attempt to decorate async functions
    - Async decorators do not attempt to decorate normal functions

    The first positional parameter of the decorator implementation (``call``) receives
    a ``functools.partial`` that calls the wrapped function with the current invocation's
    arguments.  Remaining parameters become the decorator factory's public API.

    Because ``call`` is a plain ``functools.partial`` its internals are directly
    accessible:

    * ``call.func``     — the underlying wrapped function (useful for reading its
      ``__name__``, ``__doc__``, or any other attribute).
    * ``call.args``     — tuple of positional arguments supplied by the current call.
    * ``call.keywords`` — dict of keyword arguments supplied by the current call.

    Example:
        >>> @decorator()
        ... def my_decorator(call, **options):
        ...     # Custom decorator logic here
        ...     return call()
        ...
        >>> @my_decorator()
        ... def my_function(arg1, arg2):
        ...     return "result"
    """

    @staticmethod
    def _sync(dec: Callable[..., FuncResultT]) -> DecoratorFactoryT:
        def sync_factory(*args: DecParams.args, **kwargs: DecParams.kwargs) -> DecoratorT:
            def decorator_func(func: DecoratedFunctionT) -> DecoratedFunctionT:
                if iscoroutinefunction(func):
                    raise DecorationError(dec.__name__, func.__name__)

                @wraps(func)
                def wrapper(*f_args: FuncParams.args, **f_kwargs: FuncParams.kwargs) -> FuncResultT:
                    return dec(partial(func, *f_args, **f_kwargs), *args, **kwargs)

                result = _SyncMethodAwareWrapper(wrapper)
                update_wrapper(result, func)
                result._func = wrapper  # update_wrapper overwrites _func via __dict__; restore it
                return result

            return decorator_func

        return sync_factory

    @staticmethod
    def _async(dec: Callable[..., Awaitable[FuncResultT]]) -> AsyncDecoratorFactoryT:
        def sync_factory(*args: DecParams.args, **kwargs: DecParams.kwargs) -> AsyncDecoratorT:
            def decorator_func(func: AsyncDecoratedFunctionT) -> AsyncDecoratedFunctionT:
                if not iscoroutinefunction(func):
                    raise DecorationError(dec.__name__, func.__name__)

                @wraps(func)
                async def wrapper(
                    *f_args: FuncParams.args, **f_kwargs: FuncParams.kwargs
                ) -> FuncResultT:
                    return await dec(partial(func, *f_args, **f_kwargs), *args, **kwargs)

                result = _AsyncMethodAwareWrapper(wrapper)
                update_wrapper(result, func)
                result._func = wrapper  # update_wrapper overwrites _func via __dict__; restore it
                markcoroutinefunction(
                    result
                )  # iscoroutinefunction does not follow __wrapped__ in Python 3.12+
                return result

            return decorator_func

        return sync_factory

    def __call__(
        self, dec: Callable[Concatenate[Any, DecParams], FuncResultT]
    ) -> Callable[
        DecParams,
        Callable[
            [Callable[FuncParams, FuncResultT]],
            Callable[FuncParams, FuncResultT],
        ],
    ]:
        """Invoke the decorator factory with a given decorator function.

        Determines whether the provided decorator function is asynchronous or synchronous
        and returns the appropriate decorator factory implementation.

        Args:
            dec: A callable decorator function that accepts DecParams and returns either
                 a FuncResultT or an Awaitable[FuncResultT].

        Returns:
            An async decorator factory if the input decorator is a coroutine function,
            otherwise a synchronous decorator factory.
        """
        if iscoroutinefunction(dec):
            return self._async(dec)  # type: ignore[arg-type]
        return self._sync(dec)  # type: ignore[return-value]


__all__ = [
    "DecorationError",
    "decorator",
]
