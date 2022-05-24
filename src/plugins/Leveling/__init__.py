from __future__ import annotations

from typing import TYPE_CHECKING

from . import level_command, leveling_cog

if TYPE_CHECKING:
    from main import Plyoox


async def setup(bot: Plyoox):
    await bot.add_cog(leveling_cog.Leveling(bot))
    await bot.add_cog(level_command.LevelCommand(bot))
