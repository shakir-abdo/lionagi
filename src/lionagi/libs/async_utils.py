# Copyright (c) 2023 - 2024, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from lionagi.libs.base import DataClass
from lionagi.utils import UNDEFINED, alcall, is_coroutine_func, to_list, ucall

T = TypeVar("T")


__all__ = (
    "TCallParams",
    "ALCallParams",
    "RCallParams",
    "BCallParams",
    "tcall",
    "ucall",
    "alcall",
    "bcall",
    "rcall",
)


@dataclass
class TCallParams(DataClass):
    delay: float = 0
    error_msg: str | None = None
    timing: bool = False
    timeout: float | None = None
    default: Any = UNDEFINED
    error_map: dict[type, Callable[[Exception], None]] | None = None

    async def __call__(self, func, *args, **kwargs) -> T:
        return await tcall(
            func,
            *args,
            delay=self.delay,
            error_msg=self.error_msg,
            timing=self.timing,
            timeout=self.timeout,
            default=self.default,
            error_map=self.error_map,
            **kwargs,
        )

    def __str__(self) -> str:
        return f"TCallParams(delay={self.delay}, error_msg={self.error_msg}, timing={self.timing}, timeout={self.timeout}, default={self.default}, error_map={self.error_map})"

    def __repr__(self) -> str:
        return str(self)


@dataclass
class ALCallParams(DataClass):
    function: Callable[..., T]
    num_retries: int = 0
    delay: float = 0
    retry_delay: float = 0
    backoff_factor: float = 1
    default: Any = UNDEFINED
    timeout: float | None = None
    timing: bool = False
    verbose: bool = True
    error_msg: str | None = None
    error_map: dict[type, Callable[[Exception], None]] | None = None
    max_concurrent: int | None = None
    throttle_period: float | None = None
    flatten: bool = False
    dropna: bool = False
    unique: bool = False

    async def __call__(self, input_, *args, **kwargs):
        return await alcall(
            input_,
            self.function,
            *args,
            num_retries=self.num_retries,
            delay=self.delay,
            retry_delay=self.retry_delay,
            backoff_factor=self.backoff_factor,
            default=self.default,
            timeout=self.timeout,
            timing=self.timing,
            verbose=self.verbose,
            error_msg=self.error_msg,
            error_map=self.error_map,
            max_concurrent=self.max_concurrent,
            throttle_period=self.throttle_period,
            flatten=self.flatten,
            dropna=self.dropna,
            unique=self.unique,
            **kwargs,
        )


@dataclass
class BCallParams(DataClass):
    function: Callable[..., T]
    batch_size: int
    num_retries: int = 0
    delay: float = 0
    retry_delay: float = 0
    backoff_factor: float = 1
    default: Any = UNDEFINED
    timeout: float | None = None
    timing: bool = False
    verbose: bool = True
    error_msg: str | None = None
    error_map: dict[type, Callable[[Exception], None]] | None = None
    max_concurrent: int | None = None
    throttle_period: float | None = None
    flatten: bool = False
    dropna: bool = False
    unique: bool = False

    async def __call__(self, input_, *args, **kwargs):
        return await bcall(
            input_,
            self.function,
            *args,
            batch_size=self.batch_size,
            num_retries=self.num_retries,
            delay=self.delay,
            retry_delay=self.retry_delay,
            backoff_factor=self.backoff_factor,
            default=self.default,
            timeout=self.timeout,
            timing=self.timing,
            verbose=self.verbose,
            error_msg=self.error_msg,
            error_map=self.error_map,
            max_concurrent=self.max_concurrent,
            throttle_period=self.throttle_period,
            flatten=self.flatten,
            dropna=self.dropna,
            unique=self.unique,
            **kwargs,
        )


async def tcall(
    func: Callable[..., T],
    /,
    *args: Any,
    delay: float = 0,
    error_msg: str | None = None,
    timing: bool = False,
    timeout: float | None = None,
    default: Any = UNDEFINED,
    error_map: dict[type, Callable[[Exception], None]] | None = None,
    **kwargs: Any,
) -> T | tuple[T, float]:
    """Execute a function asynchronously with timing and error handling.

    Handles both coroutine and regular functions, supporting timing,
    timeout, and custom error handling.

    Args:
        func: The function to execute (coroutine or regular).
        *args: Positional arguments for the function.
        delay: Delay before execution (seconds).
        error_msg: Custom error message prefix.
        suppress_err: If True, return default on error instead of raising.
        retry_timing: If True, return execution duration.
        retry_timeout: Timeout for function execution (seconds).
        retry_default: Value to return if an error occurs and suppress_err
        is True.
        error_map: Dict mapping exception types to error handlers.
        **kwargs: Additional keyword arguments for the function.

    Returns:
        T | tuple[T, float]: Function result, optionally with duration.

    Raises:
        asyncio.TimeoutError: If execution exceeds the timeout.
        RuntimeError: If an error occurs and suppress_err is False.

    Examples:
        >>> async def slow_func(x):
        ...     await asyncio.sleep(1)
        ...     return x * 2
        >>> result, duration = await tcall(slow_func, 5, retry_timing=True)
        >>> print(f"Result: {result}, Duration: {duration:.2f}s")
        Result: 10, Duration: 1.00s

    Note:
        - Automatically handles both coroutine and regular functions.
        - Provides timing information for performance analysis.
        - Supports custom error handling and suppression.
    """
    start = asyncio.get_event_loop().time()

    try:
        await asyncio.sleep(delay)
        result = None

        if is_coroutine_func(func):
            # Asynchronous function
            if timeout is None:
                result = await func(*args, **kwargs)
            else:
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=timeout
                )
        else:
            # Synchronous function
            if timeout is None:
                result = func(*args, **kwargs)
            else:
                result = await asyncio.wait_for(
                    asyncio.shield(asyncio.to_thread(func, *args, **kwargs)),
                    timeout=timeout,
                )

        duration = asyncio.get_event_loop().time() - start
        return (result, duration) if timing else result

    except TimeoutError as e:
        error_msg = f"{error_msg or ''} Timeout {timeout} seconds exceeded"
        if default is not UNDEFINED:
            duration = asyncio.get_event_loop().time() - start
            return (default, duration) if timing else default
        else:
            raise TimeoutError(error_msg) from e

    except Exception as e:
        if error_map and type(e) in error_map:
            error_map[type(e)](e)
            duration = asyncio.get_event_loop().time() - start
            return (None, duration) if timing else None
        error_msg = (
            f"{error_msg} Error: {e}"
            if error_msg
            else f"An error occurred in async execution: {e}"
        )
        if default is not UNDEFINED:
            duration = asyncio.get_event_loop().time() - start
            return (default, duration) if timing else default
        else:
            raise RuntimeError(error_msg) from e


async def bcall(
    input_: Any,
    func: Callable[..., T],
    /,
    batch_size: int,
    num_retries: int = 0,
    delay: float = 0,
    retry_delay: float = 0,
    backoff_factor: float = 1,
    default: Any = UNDEFINED,
    timeout: float | None = None,
    timing: bool = False,
    verbose: bool = True,
    error_msg: str | None = None,
    error_map: dict[type, Callable[[Exception], Any]] | None = None,
    max_concurrent: int | None = None,
    throttle_period: float | None = None,
    **kwargs: Any,
) -> AsyncGenerator[list[T | tuple[T, float]], None]:
    """
    Asynchronously call a function in batches with retry and timing options.

    Args:
        input_: The input data to process.
        func: The function to call.
        batch_size: The size of each batch.
        retries: The number of retries.
        delay: Initial delay before the first attempt in seconds.
        delay: The delay between retries in seconds.
        backoff_factor: Factor by which delay increases after each retry.
        default: Default value to return if an error occurs.
        timeout: The timeout for the function call in seconds.
        timing: If True, return execution time along with the result.
        verbose: If True, print retry attempts and exceptions.
        error_msg: Custom error message prefix.
        error_map: Mapping of errors to handle custom error responses.
        max_concurrent: Maximum number of concurrent calls.
        throttle_period: Throttle period in seconds.
        **kwargs: Additional keyword arguments to pass to the function.

    Yields:
        A list of results for each batch of inputs.

    Examples:
        >>> async def sample_func(x):
        ...     return x * 2
        >>> async for batch_results in bcall([1, 2, 3, 4, 5], sample_func, 2,
        ...                                  retries=3, delay=1):
        ...     print(batch_results)
    """
    input_ = to_list(input_, flatten=True, dropna=True)

    for i in range(0, len(input_), batch_size):
        batch = input_[i : i + batch_size]  # noqa: E203
        batch_results = await alcall(
            batch,
            func,
            num_retries=num_retries,
            delay=delay,
            retry_delay=retry_delay,
            backoff_factor=backoff_factor,
            default=default,
            timeout=timeout,
            timing=timing,
            verbose=verbose,
            error_msg=error_msg,
            error_map=error_map,
            max_concurrent=max_concurrent,
            throttle_period=throttle_period,
            **kwargs,
        )
        yield batch_results


@dataclass
class RCallParams(DataClass):
    num_retries: int = 0
    delay: float = 0
    retry_delay: float = 0
    backoff_factor: float = 1
    default: Any = UNDEFINED
    timeout: float | None = None
    timing: bool = False
    verbose: bool = True
    error_msg: str | None = None
    error_map: dict[type, Callable[[Exception], None]] | None = None

    async def __call__(self, func, *args, **kwargs) -> T | tuple[T, float]:
        return await rcall(
            func,
            *args,
            num_retries=self.num_retries,
            delay=self.delay,
            retry_delay=self.retry_delay,
            backoff_factor=self.backoff_factor,
            default=self.default,
            timeout=self.timeout,
            timing=self.timing,
            verbose=self.verbose,
            error_msg=self.error_msg,
            error_map=self.error_map,
            **kwargs,
        )

    def __str__(self) -> str:
        return (
            f"RCallParams(num_retries={self.num_retries}, delay={self.delay}, "
            f"retry_delay={self.retry_delay}, backoff_factor={self.backoff_factor}, "
            f"default={self.default}, timeout={self.timeout}, timing={self.timing}, "
            f"verbose={self.verbose}, error_msg={self.error_msg}, error_map={self.error_map})"
        )

    def __repr__(self) -> str:
        return str(self)


async def rcall(
    func: Callable[..., T],
    /,
    *args: Any,
    num_retries: int = 0,
    delay: float = 0,
    retry_delay: float = 0,
    backoff_factor: float = 1,
    default: Any = UNDEFINED,
    timeout: float | None = None,
    timing: bool = False,
    verbose: bool = True,
    error_msg: str | None = None,
    error_map: dict[type, Callable[[Exception], None]] | None = None,
    **kwargs: Any,
) -> T | tuple[T, float]:
    """
    Retry a function asynchronously with customizable options, using `tcall` under the hood.

    Attempts to run the given function, retrying up to `num_retries` times if an exception or
    timeout occurs. The `tcall` function is used to handle execution timing, errors, and timeouts.

    Args:
        func: The function to execute (coroutine or regular).
        *args: Positional arguments for the function.
        num_retries: Number of retry attempts (default: 0).
        delay: Initial delay before the first attempt (seconds).
        retry_delay: Delay between retry attempts (seconds).
        backoff_factor: Factor to increase the retry delay after each failed attempt.
        default: Value to return if all attempts fail. If not provided, an exception will be raised.
        timeout: Timeout for each function execution (seconds).
        timing: If True, include execution duration in the return value.
        verbose: If True, print retry messages.
        error_msg: Custom error message prefix.
        error_map: Dict mapping exception types to error handlers.
        **kwargs: Additional keyword arguments for the function.

    Returns:
        T or (T, float): Result of the function call, optionally with timing.

    Raises:
        RuntimeError: If the function fails after all attempts and no default is provided.
        TimeoutError: If the function call exceeds the specified timeout.
    """
    current_retry_delay = retry_delay

    for attempt in range(num_retries + 1):
        try:
            # We do not supply `default` to tcall directly because we want to handle retries ourselves.
            # If we gave `default` to tcall, it would return the default on the first error, preventing retries.
            result = await tcall(
                func,
                *args,
                delay=delay if attempt == 0 else 0,
                error_msg=error_msg,
                timing=timing,
                timeout=timeout,
                default=...,
                error_map=error_map,
                **kwargs,
            )
            # If tcall succeeded or returned a value (including None if error_map handled it),
            # we consider this a successful attempt and return.
            return result
        except Exception as e:
            # An exception means this attempt failed.
            if attempt < num_retries:
                # If we still have retries left, print a message and try again.
                if verbose:
                    print(
                        f"Attempt {attempt + 1}/{num_retries + 1} failed: {e}, retrying..."
                    )
                await asyncio.sleep(current_retry_delay)
                current_retry_delay *= backoff_factor
            else:
                # All attempts exhausted.
                if default is not UNDEFINED:
                    # Return default if provided. Note that we do not return timing here,
                    # since we have no successful timing information to provide.
                    return default

                raise RuntimeError(
                    f"{error_msg or ''} Operation failed after {num_retries + 1} attempts: {e}"
                ) from e