from main import Plyoox
from plugins.Leveling import leveling_cog, level_cog


async def setup(bot: Plyoox):
    await bot.add_cog(leveling_cog.Leveling(bot))
    await bot.add_cog(level_cog.LevelCommand(bot))
