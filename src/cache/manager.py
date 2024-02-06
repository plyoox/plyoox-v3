import asyncio
from typing import Literal

from discord import utils

import asyncpg
from lru import LRU

from lib.enums import LoggingKind

from .models import (
    AutoModerationAction,
    AutoModerationCheck,
    AutoModerationPunishment,
    LevelRole,
    LoggingSettings,
    MaybeWebhook,
    ModerationRule,
    WelcomeModel,
    LevelingModel,
    LoggingModel,
    ModerationModel,
    Punishment,
    ModerationPoints,
)


type CacheType = Literal["wel", "log", "lvl", "mod", "automod", "punishment"]
type Falsify = None | bool


class CacheManager:
    __slots__ = (
        "_pool",
        "_leveling",
        "_welcome",
        "_moderation",
        "_logging",
        "_automoderation",
        "_automoderation_queue",
        "_punishment_cache",
    )

    def __init__(self, pool: asyncpg.Pool, cache_size: int = 128):
        self._pool = pool

        self._leveling = LRU(cache_size)
        self._welcome = LRU(cache_size)
        self._automoderation = LRU(cache_size * 10)
        self._punishment_cache = LRU(cache_size)
        self._automoderation_queue: dict[int, asyncio.Event] = dict()

        # Those caches are larger, because they are used for message caching
        self._logging = LRU(cache_size * 2)
        self._moderation = LRU(cache_size * 2)

    @staticmethod
    def __to_moderation_actions(actions: list[dict] | None):
        if not actions:
            return []

        formatted_actions = []

        for action in actions:
            punishment_key = action["punishment"]
            duration = None
            points = None

            if isinstance(punishment_key, dict):
                punishment_key = tuple(punishment_key.keys())[0]
                duration = action["punishment"][punishment_key].get("duration")
                amount = action["punishment"][punishment_key].get("points")

                if amount is not None:
                    points = ModerationPoints(
                        amount=amount,
                        expires_in=action["punishment"][punishment_key].get("expires_in"),
                    )

            punishment = AutoModerationPunishment(kind=punishment_key, points=points, duration=duration)

            check = action.get("check")
            if check is not None:
                check_time = None

                if isinstance(check, dict):
                    check = tuple(check.keys())[0]
                    check_time = action["check"][check].get("time")

                check = AutoModerationCheck(kind=check, time=check_time)

            formatted_actions.append(AutoModerationAction(punishment=punishment, check=check))

        return formatted_actions

    async def get_welcome(self, id: int) -> WelcomeModel | Falsify:
        """
        Returns the cache for the welcome plugin.

        If the guild has no configuration, it will return `None`,
        if the configuration is disabled it will return `False`.
        """
        guild_cache = self._welcome.get(id, utils.MISSING)
        if guild_cache is not utils.MISSING:
            return guild_cache

        result = await self._pool.fetchrow("SELECT * FROM welcome_config WHERE id = $1", id)
        if result is None:
            self._welcome[id] = False
            return None

        if not result["active"]:
            self._welcome[id] = False
            return False

        result = dict(result)
        del result["id"], result["active"]

        self._welcome[id] = model = WelcomeModel(**result)

        return model

    async def get_leveling(self, id: int) -> LevelingModel | Falsify:
        """Returns the cache for the leveling plugin.

        If the guild has no configuration, it will return `None`,
        if the configuration is disabled it will return `False`.
        """
        guild_cache = self._leveling.get(id, utils.MISSING)
        if guild_cache is not utils.MISSING:
            return guild_cache

        result = await self._pool.fetchrow("SELECT * FROM level_config WHERE id = $1", id)
        if result is None:
            self._leveling[id] = None
            return

        if not result["active"]:
            self._leveling[id] = False
            return False

        result = dict(result)
        del result["id"], result["active"]

        roles = [LevelRole(**role) for role in (result["roles"] or [])]

        model = LevelingModel(
            exempt_channels=result["exempt_channels"] or [],
            exempt_role=result["exempt_role"],
            remove_roles=result["remove_roles"],
            roles=roles,
            message=result["message"],
            channel=result["channel"],
            booster_xp_multiplier=result["booster_xp_multiplier"],
        )
        self._leveling[id] = model

        return model

    async def get_moderation(self, id: int) -> ModerationModel | None:
        """Returns the cache for the moderation plugin."""
        guild_cache = self._moderation.get(id, utils.MISSING)
        if guild_cache:
            return guild_cache

        result = await self._pool.fetchrow(
            "SELECT m.*, w.id as mwh_id, w.token as mwh_token, w.webhook_channel as mwh_webhook_channel, "
            "w.guild_id as mwh_guild_id FROM moderation_config m LEFT JOIN public.maybe_webhook w "
            "ON w.id = m.logging_channel WHERE m.id = $1",
            id,
        )
        if result is None:
            self._moderation[id] = None
            return None

        if result["logging_channel"]:
            logging_channel = MaybeWebhook(
                id=result["mwh_id"],
                token=result["mwh_token"],
                webhook_channel=result["mwh_webhook_channel"],
                guild_id=result["mwh_guild_id"],
            )
        else:
            logging_channel = None

        model = ModerationModel(
            active=result["active"],
            invite_actions=self.__to_moderation_actions(result["invite_actions"]),
            invite_active=result["invite_active"],
            invite_exempt_channels=result["invite_exempt_channels"] or [],
            invite_exempt_roles=result["invite_exempt_roles"] or [],
            invite_exempt_guilds=result["invite_exempt_guilds"] or [],
            caps_actions=self.__to_moderation_actions(result["caps_actions"]),
            caps_active=result["caps_active"],
            caps_exempt_roles=result["caps_exempt_roles"] or [],
            caps_exempt_channels=result["caps_exempt_channels"] or [],
            logging_channel=logging_channel,
            point_actions=self.__to_moderation_actions(result["point_actions"]),
            link_allow_list=result["link_allow_list"] or [],
            link_active=result["link_active"],
            link_exempt_channels=result["link_exempt_channels"] or [],
            link_exempt_roles=result["link_exempt_roles"] or [],
            link_actions=self.__to_moderation_actions(result["link_actions"]),
            moderation_roles=result["moderation_roles"] or [],
            notify_user=result["notify_user"],
            ignored_roles=result["ignored_roles"] or [],
        )

        self._moderation[id] = model

        return model

    async def get_logging(self, id: int) -> LoggingModel | Falsify:
        """Returns the cache for the logging plugin.

        If the guild has no configuration, it will return `None`,
        if the configuration is disabled it will return `False`.
        """
        guild_cache = self._logging.get(id, utils.MISSING)
        if guild_cache is not utils.MISSING:
            return guild_cache

        result = await self._pool.fetchrow("SELECT * FROM logging_config WHERE id = $1", id)
        if result is None:
            self._logging[id] = None
            return None

        if not result["active"]:
            self._logging[id] = False
            return False

        settings_query = await self._pool.fetch(
            "SELECT l.*, w.id as mwh_id, w.token as mwh_token, w.webhook_channel as mwh_webhook_channel, "
            " w.guild_id as mwh_guild_id FROM logging_settings l LEFT JOIN maybe_webhook w ON w.id = l.channel "
            "WHERE l.guild_id = $1 AND active = true",
            id,
        )
        settings: dict[LoggingKind, LoggingSettings] = {}

        for setting in settings_query:
            # Do not cache disabled settings
            if not setting["active"]:
                continue

            channel: MaybeWebhook | None = None

            if setting["mwh_id"]:
                channel = MaybeWebhook(
                    id=setting["mwh_id"],
                    token=setting["mwh_token"],
                    webhook_channel=setting["mwh_webhook_channel"],
                    guild_id=setting["mwh_guild_id"],
                )

            current_setting = LoggingSettings(
                channel=channel,
                kind=setting["kind"],
                exempt_channels=setting["exempt_channels"] or [],
                exempt_roles=setting["exempt_roles"] or [],
            )

            settings[setting["kind"]] = current_setting

        model = LoggingModel(settings=settings)
        self._logging[id] = model

        return model

    async def get_punishments(self, id: int) -> dict[int, Punishment] | Falsify:
        punishment_cache = self._punishment_cache.get(id, utils.MISSING)
        if punishment_cache is not utils.MISSING:
            return punishment_cache

        rows = await self._pool.fetch(
            "SELECT id, actions, enabled, name, reason FROM moderation_punishment WHERE guild_id = $1", id
        )

        punishments = dict()

        for row in rows:
            if not row["enabled"]:
                continue

            punishment = Punishment(
                id=row["id"],
                actions=self.__to_moderation_actions(row["actions"]),
                name=row["name"],
                reason=row["reason"],
            )

            punishments[row["id"]] = punishment

        self._punishment_cache[id] = punishments

        return punishments

    async def get_moderation_rule(self, rule_id: int) -> ModerationRule | None | bool:
        """Returns the cache for the moderation rule."""
        rule_cache = self._automoderation.get(rule_id, utils.MISSING)
        if rule_cache:
            return rule_cache

        if event := self._automoderation_queue.get(rule_id):
            await event.wait()
            return self._automoderation.get(rule_id, None)

        self._automoderation_queue[rule_id] = event = asyncio.Event()

        result = await self._pool.fetchrow(
            "SELECT actions, guild_id, reason FROM automoderation_rule WHERE rule_id = $1", rule_id
        )
        # Rule does not exist
        if result is None:
            self._automoderation[rule_id] = None
            del self._automoderation_queue[rule_id]
            event.set()

            return None

        # If the rule has no actions, there is no need to store it
        if not result["actions"]:
            self._automoderation[rule_id] = False
            del self._automoderation_queue[rule_id]
            event.set()

            return False

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
        elif cache == "punishment":
            return self._punishment_cache

    def remove_cache(self, id: int, store_key: CacheType) -> None:
        store = self._get_store(store_key)
        if store.get(id, None):
            del store[id]

    def edit_cache(self, id: int, store: Literal["wel", "log", "lvl", "mod"], **kwargs) -> None:
        store = self._get_store(store)
        guild_cache = store.get(id, None)

        if guild_cache is not None:
            for key, value in kwargs.items():
                if hasattr(guild_cache, key):
                    setattr(guild_cache, key, value)
