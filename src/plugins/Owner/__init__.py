from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from plugins.Owner import owner_cog

if TYPE_CHECKING:
    from main import Plyoox


async def setup(bot: Plyoox):
    await bot.add_cog(owner_cog.Owner(bot), guild=discord.Object(505438986672537620))
