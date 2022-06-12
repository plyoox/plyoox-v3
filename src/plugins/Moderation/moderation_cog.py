from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from plugins.Moderation import _logging_helper
from translation import _

if TYPE_CHECKING:
    from main import Plyoox


class Moderation(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @staticmethod
    async def _can_execute_on(interaction: discord.Interaction, target: discord.Member) -> bool:
        if interaction.user <= target:
            await interaction.response.send_message(
                _(interaction.locale, "moderation.hierarchy_not_permitted"), ephemeral=True
            )
            return False

        if target >= interaction.guild.me:
            await interaction.response.send_message(
                _(interaction.locale, "moderation.  bot_cannot_punish"), ephemeral=True
            )
            return False

        return True

    @app_commands.command(name="ban", description="Bans an user from the guild.")
    @app_commands.describe(member="The member that should be banned.", reason="Why the member should be banned.")
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str]):
        lc = interaction.locale
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await _logging_helper.log_ban(interaction, target=member, reason=reason)
        await guild.ban(member, reason=reason, delete_message_days=1)
        await interaction.response.send_message(_(lc, "moderation.ban.successfully_banned"))

    @app_commands.command(name="tempban", description="Bans an user from the guild for a specific time.")
    @app_commands.describe(
        member="The member that should be banned.",
        reason="Why the member should be banned.",
        duration="How long the member should be banned.",
    )
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def tempban(
        self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: Optional[str]
    ):
        pass

    @app_commands.command(name="kick", description="Kicks an user from the guild.")
    @app_commands.describe(member="The member that should be kicked.", reason="Why the member should be kicked.")
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str]):
        pass

    @app_commands.command(name="mute", description="Mutes an user permanently.")
    @app_commands.describe(member="The member that should be muted.", reason="Why the member should be muted.")
    @app_commands.checks.bot_has_permissions(manage_roles=True)
    @app_commands.default_permissions(mute_members=True)
    @app_commands.guild_only
    async def mute(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str]):
        pass

    @app_commands.command(name="tempmute", description="Mutes an user for a specific time.")
    @app_commands.describe(
        member="The member that should be muted.",
        reason="Why the member should be muted.",
        duration="How long the member should be banned.",
    )
    @app_commands.checks.bot_has_permissions(manage_roles=True, moderate_members=True)
    @app_commands.default_permissions(mute_members=True)
    @app_commands.guild_only
    async def tempmute(
        self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: Optional[str]
    ):
        pass

    @tempmute.autocomplete("duration")
    @tempban.autocomplete("duration")
    async def autocomplete_duration(self, interaction: discord.Interaction, current: str):
        lc = interaction.locale

        times = [
            {"label": f"30 {_(lc, 'times.minutes')}", "value": "30min"},
            {"label": f"1 {_(lc, 'times.hour')}", "value": "1h"},
            {"label": f"3 {_(lc, 'times.hours')}", "value": "3h"},
            {"label": f"6 {_(lc, 'times.hours')}", "value": "6h"},
            {"label": f"12 {_(lc, 'times.hours')}", "value": "12h"},
            {"label": f"1 {_(lc, 'times.day')}", "value": "1d"},
            {"label": f"3 {_(lc, 'times.days')}", "value": "3d"},
            {"label": f"7 {_(lc, 'times.days')}", "value": "7d"},
            {"label": f"14 {_(lc, 'times.days')}", "value": "14d"},
            {"label": f"1 {_(lc, 'times.month')} (28 {_(lc, 'times.days')})", "value": "28d"},
            {"label": f"3 {_(lc, 'times.months')} (90 {_(lc, 'times.days')})", "value": "14d"},
            {"label": f"6 {_(lc, 'times.months')} (180 {_(lc, 'times.days')})", "value": "14d"},
        ]

        if not current:
            return [app_commands.Choice(name=time["label"], value=time["value"]) for time in times]

        return [
            app_commands.Choice(name=time["label"], value=time["value"])
            for time in times
            if current.lower() in time["label"].lower()
        ]
