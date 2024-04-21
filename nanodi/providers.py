from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import TracebackType


class Resource:
    def init(self) -> Any:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> Any:
        return self.init()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncResource:
    async def init(self) -> Any:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError

    async def __aenter__(self) -> Any:
        return await self.init()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()
