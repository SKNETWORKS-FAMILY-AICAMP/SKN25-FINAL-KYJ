from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
ResultT = TypeVar("ResultT")


async def run_blocking(call: Callable[P, ResultT], /, *args: P.args, **kwargs: P.kwargs) -> ResultT:
    return await asyncio.to_thread(partial(call, *args, **kwargs))
