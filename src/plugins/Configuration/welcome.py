from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

from lib import helper, colors
from lib.types.database import WelcomeData
from translation import _

from . import views

if TYPE_CHECKING:
    from main import Plyoox


class WelcomeConfig(app_commands.Group):
    def __init__(self, **kwargs):
        super().__init__(name="welcome", description="Changes the settings for the welcome plugin.", **kwargs)

    @app_commands.command(name="list", description="Lists all settings for the welcome plugin")
    async def list_welcome(self, interaction: discord.Interaction):
        bot: Plyoox = interaction.client  # type: ignore
        lc = interaction.locale
        guild = interaction.guild

        config: WelcomeData = await bot.db.fetchrow("SELECT * FROM welcome WHERE id = $1", guild.id)

        if config is None:
            return await helper.interaction_send(interaction, "config.welcome.no_config")

        join_channel = guild.get_channel(config["join_channel"])
        leave_channel = guild.get_channel(config["leave_channel"])
        join_roles = " ".join(f"<@{role_id}>" for role_id in config["join_roles"])
        no_message = f"\n> **{_(lc, 'message')}:** {_(lc, 'no_message')}"

        embed = discord.Embed(
            color=colors.DISCORD_DEFAULT,
            title=_(lc, "config.welcome.title"),
            description=_(lc, "config.welcome.description"),
        )

        embed.add_field(
            name=_(lc, "config.welcome.member_join"),
            value=f"> **{_(lc, 'config.active')}:** {_(lc, config['join_active'])}\n"
            f"> **{_(lc, 'channel')}:** {join_channel.mention if join_channel else _(lc, 'no_channel')}\n"
            f"> **{_(lc, 'roles')}:** {join_roles or _(lc, 'no_roles')}" + no_message
            if not config["join_message"]
            else "",
            inline=False,
        )

        embed.add_field(
            name=_(lc, "config.welcome.member_leave"),
            value=f"> **{_(lc, 'config.active')}:** {_(lc, config['leave_active'])}\n"
            f"> **{_(lc, 'channel')}:** {leave_channel.mention if leave_channel else _(lc, 'no_message')}",
            inline=False,
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="join-channel", description="Sets or removes the welcome channel.")
    @app_commands.describe(channel="The new join channel. No channel will remove it from the configuration.")
    async def join_channel(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel]):
        bot: Plyoox = interaction.client  # type: ignore
        guild = interaction.guild

        if channel is None:
            await bot.db.execute("UPDATE welcome SET join_channel = NULL WHERE id = $1", guild.id)
            await helper.interaction_send(interaction, "config.channel_removed")
            bot.cache.edit_cache("wel", guild.id, "join_channel", None)
            return

        if not channel.permissions_for(guild.me).send_messages:
            await helper.interaction_send(interaction, "config.cannot_write")
            return

        await bot.db.execute(
            "INSERT INTO welcome (id, join_channel) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE SET join_channel = $2",
            guild.id,
            channel.id,
        )

        bot.cache.edit_cache("wel", guild.id, "join_channel", channel.id)
        await helper.interaction_send(interaction, "config.welcome.join_channel_set", channel=channel)

    @app_commands.command(name="join-message", description="Changes the message when a user joins.")
    async def join_message(self, interaction: discord.Interaction):
        bot: Plyoox = interaction.client  # type: ignore
        guild = interaction.guild

        message = await bot.db.fetchval("SELECT join_message FROM welcome WHERE id = $1", guild.id)
        await interaction.response.send_modal(views.WelcomeMessageModal(interaction.locale, message))
