from main import Plyoox
from .guild_cog import GuildCommand
from .infos_cog import Infos
from .user_cog import UserCommand


async def setup(bot: Plyoox):
    await bot.add_cog(Infos(bot))
    await bot.add_cog(UserCommand())
    await bot.add_cog(GuildCommand())
