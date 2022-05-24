from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from .owner_cog import Owner

if TYPE_CHECKING:
    from main import Plyoox


async def setup(bot: Plyoox):
    await bot.add_cog(Owner(bot), guild=discord.Object(505438986672537620))
