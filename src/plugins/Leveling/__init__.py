from main import Plyoox
from plugins.Leveling import leveling_cog


async def setup(bot: Plyoox):
    await bot.add_cog(leveling_cog.Leveling(bot), guild=bot.test_guild)
