from main import Plyoox
from src.plugins.Infos import infos_cog, guild_cog, user_cog


async def setup(bot: Plyoox):
    await bot.add_cog(infos_cog.Infos(bot))
    await bot.add_cog(user_cog.UserCommand())
    await bot.add_cog(guild_cog.GuildCommand())
