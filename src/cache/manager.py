import asyncpg

from src.cache.models import WelcomeModel


class CacheManager:
    _welcome: dict[int, WelcomeModel] = dict()
    _pool: asyncpg.Pool

    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_welcome(self, id: int) -> WelcomeModel | None:
        cache = self._welcome.get(id)
        if cache:
            return cache

        result = await self._pool.fetchrow("SELECT * from welcome WHERE sid = $1", id)
        if result:
            model = WelcomeModel(*result)
            self._welcome[id] = model

            return model
