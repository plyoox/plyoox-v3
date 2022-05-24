from __future__ import annotations

from typing import TYPE_CHECKING

from . import logging_cog

if TYPE_CHECKING:
    from main import Plyoox


async def setup(bot: Plyoox):
    await bot.add_cog(logging_cog.LoggingEvents(bot))
