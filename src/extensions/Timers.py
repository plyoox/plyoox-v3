from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Any

import asyncpg
import discord
from discord import utils
from discord.ext import commands
from discord.app_commands import locale_str as _

from cache.models import TimerModel


from translation import translate

if TYPE_CHECKING:
    from main import Plyoox

    from lib.enums import TimerEnum


_log = logging.getLogger("Timer")


class Timer(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._current_timer: TimerModel | None = None
        self._task = None

    @commands.Cog.listener()
    async def on_ready(self):
        if self._task is None:
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def cog_unload(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

        self._current_timer = None

    async def get_timer(self, *, days: int = 7) -> TimerModel | None:
        record = await self.bot.db.fetchrow(
            "SELECT * FROM timer WHERE expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1",
            datetime.timedelta(days=days),
        )

        return TimerModel(**record) if record else None

    async def call_timer(self, timer: TimerModel) -> None:
        await self.bot.db.execute("DELETE FROM timer WHERE id = $1", timer.id)

        func = getattr(self, f"on_{timer.kind.replace('_', '')}_expire", None)
        if func is not None:
            await func(timer)
        else:
            _log.error(f"Could not dispatch timer {timer.type} with id {timer.id}")

    async def dispatch_timers(self) -> None:
        try:
            while not self.bot.is_closed():
                timer = await self.get_timer(days=1)

                if timer is None:
                    await asyncio.sleep(30)
                    continue

                now = utils.utcnow().replace(tzinfo=None)

                if timer.expires >= now:
                    to_sleep = (timer.expires - now).total_seconds()
                    await asyncio.sleep(to_sleep)

                await self.call_timer(timer)
        except asyncio.CancelledError:
            raise
        except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def create_timer(
        self, target_id: int, guild_id: int, kind: TimerEnum, expires: datetime.datetime, data: dict[str, Any] = None
    ) -> None:
        timer_id = await self.bot.db.fetchval(
            "INSERT INTO timer (target_id, guild_id, kind, expires, data) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            target_id,
            guild_id,
            kind,
            expires.replace(tzinfo=None),
            data,
        )

        timer = TimerModel(
            id=timer_id,
            expires=expires,
            guild_id=guild_id,
            target_id=target_id,
            kind=kind,
            data=data,
        )

        if self._current_timer and self._current_timer.expires < timer.expires:
            self._current_timer = None
            self._task.cancel()
            self._task = self.bot.loop.create_task(self.dispatch_timers())

    async def on_tempban_expire(self, timer: TimerModel):
        guild = self.bot.get_guild(timer.guild_id)

        if guild is None:
            _log.debug("Cannot unban user, guild not found")
            return

        if not guild.me.guild_permissions.ban_members:
            return

        try:
            await guild.unban(
                discord.Object(id=timer.target_id),
                reason=translate(_("Temporary ban expired"), self.bot, guild.preferred_locale),
            )
        except discord.NotFound:
            _log.debug("Cannot unban user, ban not found")


async def setup(bot: Plyoox):
    await bot.add_cog(Timer(bot))
