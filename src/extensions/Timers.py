from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING, Optional, Any

import asyncpg
import discord
from discord import utils
from discord.ext import commands

from cache.models import TimerModel
from lib.enums import TimerEnum
from translation import _

if TYPE_CHECKING:
    from main import Plyoox


_log = logging.getLogger("Timer")


class Timer(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._current_timer: Optional[TimerModel] = None
        self._task = bot.loop.create_task(self.dispatch_timers())

    async def cog_unload(self) -> None:
        self._task.cancel()

    async def get_active_timer(self, *, days: int = 7) -> Optional[TimerModel]:
        record = await self.bot.db.fetchrow(
            "SELECT * FROM timers WHERE timers.expires < (CURRENT_DATE + $1::interval) ORDER BY expires LIMIT 1",
            datetime.timedelta(days=days),
        )

        return TimerModel(**record) if record else None

    async def call_timer(self, timer: TimerModel) -> None:
        await self.bot.db.execute("DELETE FROM timers WHERE id = $1", timer.id)

        func = getattr(self, f"on_{timer.type}_expire", None)
        if func is not None:
            await func(timer)
        else:
            _log.error(f"Could not dispatch timer {timer.type} with id {timer.id}")

    async def dispatch_timers(self) -> None:
        try:
            while not self.bot.is_closed():
                timer = await self.get_active_timer(days=7)

                if timer is None:
                    await asyncio.sleep(30)
                    continue

                now = utils.utcnow()

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
        self, target_id: int, guild_id: int, type: TimerEnum, expires: datetime.datetime, data: dict[str, Any] = None
    ) -> None:
        timer_id = await self.bot.db.fetchval(
            "INSERT INTO timers (target_id, guild_id, type, expires, data) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            target_id,
            guild_id,
            type,
            expires,
            data,
        )

        timer = TimerModel(
            id=timer_id,
            expires=expires,
            guild_id=guild_id,
            target_id=target_id,
            type=type,
            data=data,
        )

        if self._current_timer and self._current_timer.expires < timer.expires:
            self._current_timer = None
            self._task.cancel()
            self.bot.loop.create_task(self.dispatch_timers())

    async def on_tempban_expire(self, timer: TimerModel):
        guild = self.bot.get_guild(timer.guild_id)

        if guild is None:
            return

        try:
            await guild.unban(
                discord.Object(id=timer.target_id), reason=_(guild.preferred_locale, "moderation.tempban_expired")
            )
        except discord.NotFound:
            pass


async def setup(bot: Plyoox):
    await bot.add_cog(Timer(bot))
