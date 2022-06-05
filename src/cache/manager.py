from typing import Literal

import asyncpg

from .models import WelcomeModel, LevelingModel, LoggingModel, ModerationModel


class CacheManager:
    _welcome: dict[int, WelcomeModel | None] = dict()
    _leveling: dict[int, LevelingModel | None] = dict()
    _moderation: dict[int, ModerationModel | None] = dict()
    _logging: dict[int, LoggingModel | None] = dict()
    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    def __get_cache(self, cache: dict, id: int, query: str, model):
        guild_cache = cache.get(id, False)
        if guild_cache is not False:
            return cache

        result = await self._pool.fetchrow(query, id)
        if result is None:
            cache[id] = None
            return

        result = dict(result)
        del result["id"]

        model = model(**result)
        cache[id] = model

        return model

    def remove_guild_cache(self, id: int) -> None:
        """Deletes the caches from a guild."""

        # Welcome cache
        if self._welcome.get(id, False) is not False:
            del self._welcome[id]

        # Leveling cache
        if self._leveling.get(id, False) is not False:
            del self._leveling[id]

        # Logging cache
        if self._logging.get(id, False) is not False:
            del self._logging[id]

        # Moderation cache
        if self._moderation.get(id, False) is not False:
            del self._moderation[id]

    async def get_welcome(self, id: int) -> WelcomeModel | None:
        """Returns the cache for the welcome plugin."""
        return self.__get_cache(self._welcome, id, "SELECT * from welcome WHERE id = $1", WelcomeModel)

    async def get_leveling(self, id: int) -> LevelingModel | None:
        """Returns the cache for the leveling plugin."""
        return self.__get_cache(self._leveling, id, "SELECT * from leveling WHERE id = $1", LevelingModel)

    async def get_moderation(self, id: int) -> ModerationModel | None:
        """Returns the cache for the moderation plugin."""
        return self.__get_cache(self._moderation, id, "SELECT * from moderation WHERE id = $1", ModerationModel)

    async def get_logging(self, id: int) -> LoggingModel | None:
        """Returns the cache for the logging plugin."""
        return self.__get_cache(self._logging, id, "SELECT * from logging WHERE id = $1", LoggingModel)

    def edit_cache(self, cache: Literal["wel", "log", "lvl"], id: int, key: str, value: int | str | bool | None):
        guild_cache = None

        if cache == "wel":
            guild_cache = self._welcome.get(id)
        elif cache == "log":
            guild_cache = self._logging.get(id)
        elif cache == "lvl":
            guild_cache = self._leveling.get(id)
        elif cache == "mod":
            guild_cache = self._moderation.get(id)

        if guild_cache is not None:
            if hasattr(guild_cache, key):
                setattr(guild_cache, key, value)
