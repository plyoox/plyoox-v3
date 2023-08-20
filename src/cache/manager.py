import asyncio
from typing import Literal

import asyncpg
from lru import LRU

from .models import ModerationRule, WelcomeModel, LevelingModel, LoggingModel, ModerationModel, AutomodExecutionModel


CacheType = Literal["wel", "log", "lvl", "mod", "automod"]


class CacheManager:
    __slots__ = (
        "_pool",
        "_leveling",
        "_welcome",
        "_moderation",
        "_logging",
        "_automoderation",
        "_automoderation_queue",
    )

    def __init__(self, pool: asyncpg.Pool, cache_size: int = 128):
        self._pool = pool

        self._leveling = LRU(cache_size)
        self._welcome = LRU(cache_size)
        self._moderation = LRU(cache_size)
        self._logging = LRU(cache_size)
        self._automoderation = LRU(cache_size * 10)
        self._automoderation_queue: dict[int, asyncio.Event] = dict()

    @staticmethod
    def __to_moderation_actions(actions: list[dict] | None) -> list[AutomodExecutionModel]:
        if actions is None:
            return []

        return [
            AutomodExecutionModel(
                action=action["a"],
                check=action.get("c"),
                points=action.get("p"),
                days=action.get("d"),
                duration=action.get("t"),
            )
            for action in actions
        ]

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
        guild_cache = self._welcome.get(id, False)
        if guild_cache is not False:
            return guild_cache

        result = await self._pool.fetchrow("SELECT * FROM welcome WHERE id = $1", id)
        if result is None:
            self._welcome[id] = None
            return None

        result = dict(result)
        del result["id"]

        model = WelcomeModel(**result)
        self._welcome[id] = model

        return model

    async def get_leveling(self, id: int) -> LevelingModel | None:
        """Returns the cache for the leveling plugin."""
        guild_cache = self._leveling.get(id, False)
        if guild_cache is not False:
            return guild_cache

        result = await self._pool.fetchrow("SELECT * FROM leveling WHERE id = $1", id)
        if result is None:
            self._leveling[id] = None
            return

        result = dict(result)
        del result["id"]

        model = LevelingModel(
            active=result["active"],
            no_xp_channels=result["no_xp_channels"] or [],
            no_xp_role=result["no_xp_role"],
            remove_roles=result["remove_roles"],
            roles=result["roles"] or [],
            message=result["message"],
            channel=result["channel"],
            booster_xp_multiplier=result["booster_xp_multiplier"],
        )
        self._leveling[id] = model

        return model

    async def get_moderation(self, id: int) -> ModerationModel | None:
        """Returns the cache for the moderation plugin."""
        guild_cache = self._moderation.get(id, False)
        if guild_cache is not False:
            return guild_cache

        result = await self._pool.fetchrow("SELECT * FROM moderation WHERE id = $1", id)
        if result is None:
            self._moderation[id] = None
            return None

        model = ModerationModel(
            active=result["active"],
            invite_actions=self.__to_moderation_actions(result["invite_actions"]),
            invite_active=result["invite_active"],
            invite_whitelist_channels=result["invite_whitelist_channels"] or [],
            invite_whitelist_roles=result["invite_whitelist_roles"] or [],
            invite_allowed=result["invite_allowed"] or [],
            caps_actions=self.__to_moderation_actions(result["caps_actions"]),
            caps_active=result["caps_active"],
            caps_whitelist_roles=result["caps_whitelist_roles"] or [],
            caps_whitelist_channels=result["caps_whitelist_channels"] or [],
            log_id=result["log_id"],
            log_channel=result["log_channel"],
            log_token=result["log_token"],
            automod_actions=self.__to_moderation_actions(result["automod_actions"]),
            link_list=result["link_list"] or [],
            link_active=result["link_active"],
            link_whitelist_channels=result["link_whitelist_channels"] or [],
            link_whitelist_roles=result["link_whitelist_roles"] or [],
            link_actions=self.__to_moderation_actions(result["link_actions"]),
            link_is_whitelist=result["link_is_whitelist"],
            mod_roles=result["mod_roles"] or [],
            notify_user=result["notify_user"],
            ignored_roles=result["ignored_roles"] or [],
        )

        self._moderation[id] = model

        return model

    async def get_logging(self, id: int) -> LoggingModel | None:
        """Returns the cache for the logging plugin."""
        guild_cache = self._logging.get(id, False)
        if guild_cache is not False:
            return guild_cache

        result = await self._pool.fetchrow("SELECT * FROM logging WHERE id = $1", id)
        if result is None:
            self._logging[id] = None
            return None

        result = dict(result)
        del result["id"]

        model = LoggingModel(**result)
        self._logging[id] = model

        return model

    async def get_moderation_rule(self, rule_id: int) -> ModerationRule | None:
        """Returns the cache for the moderation rule."""
        rule_cache = self._automoderation.get(rule_id, False)
        if rule_cache is not False:
            return rule_cache

        if event := self._automoderation_queue.get(rule_id):
            await event.wait()
            return self._automoderation.get(rule_id, None)

        self._automoderation_queue[rule_id] = event = asyncio.Event()

        result = await self._pool.fetchrow(
            "SELECT actions, guild_id, reason FROM automod_rules WHERE rule_id = $1", rule_id
        )
        if result is None:
            self._automoderation[rule_id] = None
            del self._automoderation_queue[rule_id]
            event.set()

            return None

        rule_actions = self.__to_moderation_actions(result["actions"])

        self._automoderation[rule_id] = rule = ModerationRule(
            guild_id=result["guild_id"], actions=rule_actions, reason=result["reason"]
        )

        del self._automoderation_queue[rule_id]
        event.set()

        return rule

    def _get_store(self, cache: CacheType) -> LRU:
        if cache == "wel":
            return self._welcome
        elif cache == "log":
            return self._logging
        elif cache == "lvl":
            return self._leveling
        elif cache == "mod":
            return self._moderation
        elif cache == "automod":
            return self._automoderation

    def remove_cache(self, id: int, store: CacheType) -> None:
        store = self._get_store(store)
        if store.get(id, None):
            del store[id]

    def edit_cache(self, id: int, store: Literal["wel", "log", "lvl", "mod"], **kwargs) -> None:
        store = self._get_store(store)
        guild_cache = store.get(id, None)

        if guild_cache is not None:
            for key, value in kwargs.items():
                if hasattr(guild_cache, key):
                    setattr(guild_cache, key, value)
