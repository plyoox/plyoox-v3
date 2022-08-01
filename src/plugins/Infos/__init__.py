from main import Plyoox
from .infos_cog import Infos


async def setup(bot: Plyoox):
    await bot.add_cog(Infos(bot))
