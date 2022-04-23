from main import Plyoox
from src.plugins.Infos import infos_cog


async def setup(bot: Plyoox):
    await bot.add_cog(infos_cog.Infos(bot))
