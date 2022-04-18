import discord.app_commands as cmds
from discord import Interaction, Embed
from discord.ext.commands import Cog

from main import Plyoox
from plugins.Infos.guild_infos import GuildInfo
from plugins.Infos.user_infos import UserInfo
from utils import colors


class Infos(Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    guild_info_commands = GuildInfo()
    user_info_commands = UserInfo()

    @cmds.command(name="bot", description="Shows information about the bot")
    async def bot(self, interaction: Interaction):
        embed = Embed(color=colors.DISCORD_DEFAULT)

        await interaction.response.send_message("Zesz")
