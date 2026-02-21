"""
Output wrapper that mirrors Django's OutputWrapper.
"""

from collections.abc import Callable
from io import TextIOBase
from typing import Any, TextIO


class OutputWrapper:
    """
    Wrapper around stdout/stderr that adds style support and smart newline handling,
    mirroring Django's OutputWrapper.
    """

    @property
    def style_func(self) -> Callable | None:
        return self._style_func

    @style_func.setter
    def style_func(self, style_func: Callable | None) -> None:
        if style_func and self.isatty():
            self._style_func = style_func
        else:
            self._style_func = lambda x: x

    def __init__(self, out: TextIO, ending: str = "\n") -> None:
        self._out = out
        self._style_func: Callable = lambda x: x
        self.ending = ending

    def __getattr__(self, name: str) -> Any:
        return getattr(self._out, name)

    def flush(self) -> None:
        if hasattr(self._out, "flush"):
            self._out.flush()

    def isatty(self) -> bool:
        return hasattr(self._out, "isatty") and self._out.isatty()

    def write(
        self,
        msg: str = "",
        style_func: Callable | None = None,
        ending: str | None = None,
    ) -> None:
        ending = self.ending if ending is None else ending
        if ending and not msg.endswith(ending):
            msg += ending
        style_func = style_func or self.style_func
        self._out.write(style_func(msg))


# Register with TextIOBase ABC so isinstance checks work correctly
TextIOBase.register(OutputWrapper)
