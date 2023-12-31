import discord
from discord import app_commands, utils, ui
from discord.ext import commands

from lib import extensions
from main import Plyoox
from . import guild_group, user_group


_ = app_commands.locale_str


class Infos(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

        self.ctx_menu = app_commands.ContextMenu(
            name=_("View user info."),
            callback=self.about_context_menu,
        )

        self.bot.tree.add_command(self.ctx_menu)

    guild_commands = guild_group.GuildGroup()
    user_commands = user_group.UserGroup()

    @app_commands.command(name="bot", description=_("Shows information about the bot."))
    async def bot(self, interaction: discord.Interaction):
        """Shows basic information about the bot."""
        translate = interaction.translate

        embed = extensions.Embed(title=translate(_("Bot information")))
        embed.add_field(name=translate(_("Developer")), value="> JohannesIBK#9220")
        embed.add_field(name=translate(_("Contributors")), value="> X Gamer Guide#1866")
        embed.add_field(name=translate(_("Guild count")), value=f"> {len(self.bot.guilds)}")
        embed.add_field(name=translate(_("Uptime")), value=f"> {utils.format_dt(self.bot.start_time, 'R')}")
        embed.add_field(
            name=translate(_("Privacy Policy")),
            value="> [plyoox.net](https://plyoox.net/privacy-discord)",
        )

        view = ui.View()
        view.add_item(ui.Button(label="GitHub", url="https://gitlab.com/plyoox/plyoox-v3"))
        view.add_item(ui.Button(label="Dashboard", url="https://plyoox.net"))
        view.add_item(ui.Button(label="Support", url="https://discord.gg/5qPPvQe"))
        view.add_item(
            ui.Button(
                label=translate(_("Invite")),
                url=utils.oauth_url(self.bot.user.id, permissions=discord.Permissions(275146828846)),
            )
        )

        await interaction.response.send_message(embed=embed, view=view)

    async def about_context_menu(self, interaction: discord.Interaction, member: discord.Member):
        """Shows basic information about a user. This can is context menu command."""
        await self.user_commands._send_about_response(interaction, member=member, ephemeral=True)
