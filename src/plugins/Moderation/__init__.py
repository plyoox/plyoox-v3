from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.Moderation import moderation_cog, automod

if TYPE_CHECKING:
    from main import Plyoox


async def setup(bot: Plyoox):
    await bot.add_cog(moderation_cog.Moderation(bot))
    await bot.add_cog(automod.Automod(bot))
