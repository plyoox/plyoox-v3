from typing import Literal

import asyncpg
from lru import LRU

from .models import WelcomeModel, LevelingModel, LoggingModel, ModerationModel


class CacheManager:
    __slots__ = ("_pool",)

    _welcome = LRU(128)
    _leveling = LRU(128)
    _moderation = LRU(128)
    _logging = LRU(128)
    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def __get_cache(self, cache: LRU, id: int, query: str, model):
        guild_cache = cache.get(id, False)
        if guild_cache is not False:
            return guild_cache

        result = await self._pool.fetchrow(query, id)
        if result is None:
            cache[id] = None
            return

        result = dict(result)
        del result["id"]

        model = model(**result)
        cache[id] = model

        return model

    async def get_welcome(self, id: int) -> WelcomeModel | None:
        """Returns the cache for the welcome plugin."""
        return await self.__get_cache(self._welcome, id, "SELECT * FROM welcome WHERE id = $1", WelcomeModel)

    async def get_leveling(self, id: int) -> LevelingModel | None:
        """Returns the cache for the leveling plugin."""
        return await self.__get_cache(self._leveling, id, "SELECT * FROM leveling WHERE id = $1", LevelingModel)

    async def get_moderation(self, id: int) -> ModerationModel | None:
        """Returns the cache for the moderation plugin."""
        return await self.__get_cache(self._moderation, id, "SELECT * FROM moderation WHERE id = $1", ModerationModel)

    async def get_logging(self, id: int) -> LoggingModel | None:
        """Returns the cache for the logging plugin."""
        return await self.__get_cache(self._logging, id, "SELECT * FROM logging WHERE id = $1", LoggingModel)

    def edit_cache(
        self, cache: Literal["wel", "log", "lvl", "mod"], id: int, key: str, value: int | str | bool | None
    ) -> None:
        guild_cache = None

        if cache == "wel":
            guild_cache = self._welcome.get(id, None)
        elif cache == "log":
            guild_cache = self._logging.get(id, None)
        elif cache == "lvl":
            guild_cache = self._leveling.get(id, None)
        elif cache == "mod":
            guild_cache = self._moderation.get(id, None)

        if guild_cache is not None:
            if hasattr(guild_cache, key):
                setattr(guild_cache, key, value)
