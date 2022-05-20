import asyncpg

from src.cache.models import WelcomeModel, LevelingModel, LoggingModel


class CacheManager:
    _welcome: dict[int, WelcomeModel] = dict()
    _leveling: dict[int, LevelingModel] = dict()
    _logging: dict[int, LoggingModel] = dict()
    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    def remove_guild_cache(self, id: int) -> None:
        """Deletes the caches from a guild."""

        # Welcome cache
        if self._welcome.get(id) is not None:
            del self._welcome[id]

        # Leveling cache
        if self._leveling.get(id) is not None:
            del self._leveling[id]

        # Logging cache
        if self._logging.get(id) is not None:
            del self._logging[id]

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

    async def get_logging(self, id: int) -> LoggingModel | None:
        """Returns the cache for the logging plugin."""
        cache = self._logging.get(id)

        if cache is not None:
            return cache

        return await self._set_logging(id)

    async def _set_logging(self, id: int, *, query_result=None) -> LoggingModel | None:
        if query_result is None:
            query_result = await self._pool.fetchrow("SELECT * from logging WHERE id = $1", id)

        if query_result is not None:
            model = LoggingModel(
                active=query_result["active"],
                webhook_id=query_result["webhook_id"],
                webhook_token=query_result["webhook_token"],
                member_ban=query_result["member_ban"],
                member_unban=query_result["member_unban"],
                member_join=query_result["member_join"],
                member_leave=query_result["member_leave"],
                member_rename=query_result["member_rename"],
                message_edit=query_result["message_edit"],
                message_delete=query_result["message_delete"],
                member_role_change=query_result["member_role_change"],
            )
            self._logging[id] = model

            return model
