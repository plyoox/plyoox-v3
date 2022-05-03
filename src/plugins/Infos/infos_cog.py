import discord
from discord import app_commands, utils, ui
from discord.ext import commands

from main import Plyoox
from translation import _
from utils import colors


class Infos(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @app_commands.command(name="bot", description="Shows information about the bot")
    async def bot(self, interaction: discord.Interaction):
        """Shows basic information about the bot."""
        lc = interaction.locale

        embed = discord.Embed(color=colors.DISCORD_DEFAULT, title=_(lc, "infos.bot.title"))
        embed.add_field(name=_(lc, "infos.bot.coder"), value=f"> JohannesIBK#9220", inline=False)
        embed.add_field(name=_(lc, "infos.bot.guild_count"), value=f"> {len(self.bot.guilds)}", inline=False)
        embed.add_field(
            name=_(lc, "infos.bot.uptime"), value=f"> {utils.format_dt(self.bot.start_time, 'R')}", inline=False
        )

        view = ui.View()
        view.add_item(ui.Button(label="GitHub", url="https://github.com/plyoox/plyoox-v3"))
        view.add_item(ui.Button(label="Dashboard", url="https://plyoox.net"))
        view.add_item(ui.Button(label="Support", url="https://discord.gg/5qPPvQe"))
        view.add_item(
            ui.Button(
                label="Invite",
                url=utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(275146828846)),
            )
        )

        await interaction.response.send_message(embed=embed, view=view)
