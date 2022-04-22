import asyncpg

from src.cache.models import WelcomeModel, LevelingModel


class CacheManager:
    _welcome: dict[int, WelcomeModel] = dict()
    _leveling: dict[int, LevelingModel] = dict()
    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_welcome(self, id: int) -> WelcomeModel | None:
        """Returns the cache for the welcome plugin."""
        cache = self._welcome.get(id)

        if cache is not None:
            return cache

        result = await self._pool.fetchrow("SELECT * from welcome WHERE id = $1", id)

        if result is not None:
            model = WelcomeModel(
                active=result["active"],
                join_active=result["join_active"],
                join_role=result["join_active"],
                join_channel=result["join_channel"],
                join_message=result["join_message"],
                leave_active=result["leave_active"],
                leave_channel=result["leave_channel"],
                leave_message=result["leave_message"],
            )
            self._welcome[id] = model

            return model

    async def get_leveling(self, id: int) -> LevelingModel | None:
        """Returns the cache for the leveling plugin."""
        cache = self._leveling.get(id)

        if cache is not None:
            return cache

        result = await self._pool.fetchrow("SELECT * from leveling WHERE id = $1", id)

        if result is not None:
            model = LevelingModel(
                channel=result["channel"],
                no_xp_channels=result["no_xp_channels"],
                no_xp_role=result["no_xp_role"],
                roles=result["roles"],
                message=result["message"],
                active=result["active"],
                remove_roles=result["remove_roles"],
            )
            self._leveling[id] = model

            return model
