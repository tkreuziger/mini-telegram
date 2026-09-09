"""Fire-and-forget deferred task execution in background threads."""

import atexit
import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Timer
from typing import Any, ParamSpec

P = ParamSpec("P")

_logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="minitelegram-defer")


def defer(fn: Callable[P, Any], /, *args: P.args, **kwargs: P.kwargs) -> None:
    """Run *fn* on a background thread, discarding its return value.

    Exceptions are logged but not propagated to the caller.
    """
    future: Future[object] = _executor.submit(fn, *args, **kwargs)
    future.add_done_callback(_log_failure)


def defer_after(
    seconds: float,
    fn: Callable[P, Any],
    /,
    *args: P.args,
    **kwargs: P.kwargs,
) -> None:
    """Run *fn* on a background thread after a delay.

    Args:
        seconds: Delay in seconds before executing *fn*.
        fn: Callable to execute.
        *args: Positional arguments forwarded to *fn*.
        **kwargs: Keyword arguments forwarded to *fn*.
    """
    timer = Timer(seconds, defer, args=(fn, *args), kwargs=kwargs)
    timer.daemon = True
    timer.start()


def _log_failure(fut: Future[object]) -> None:
    exc = fut.exception()
    if exc is not None:
        _logger.error("Deferred task failed", exc_info=exc)


def shutdown(wait: bool = True) -> None:
    """Shut down the background executor."""
    _executor.shutdown(wait=wait)


@atexit.register
def _shutdown_at_exit() -> None:
    shutdown(wait=True)
