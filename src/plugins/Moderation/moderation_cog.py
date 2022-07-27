from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

from lib import parsers
from lib.enums import TimerType
from lib.extensions import Embed
from plugins.Moderation import _logging_helper
from translation import _
from . import clear_command
from .automod import DISCORD_INVITE

if TYPE_CHECKING:
    from main import Plyoox


class Moderation(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    clear_group = clear_command.ClearCommand()

    @staticmethod
    async def _can_execute_on(interaction: discord.Interaction, target: discord.Member) -> bool:
        if interaction.user.top_role <= target.top_role:
            await interaction.response.send_message(
                _(interaction.locale, "moderation.hierarchy_not_permitted"), ephemeral=True
            )
            return False

        if target.top_role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                _(interaction.locale, "moderation.bot_cannot_punish"), ephemeral=True
            )
            return False

        return True

    @app_commands.command(name="ban", description="Bans an user from the guild.")
    @app_commands.describe(member="The member that should be banned.", reason="Why the member should be banned.")
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)
        await _logging_helper.log_simple_punish_command(interaction, target=member, reason=reason, type="ban")
        await guild.ban(member, reason=reason, delete_message_days=1)
        await interaction.followup.send(_(lc, "moderation.ban.successfully_banned"), ephemeral=True)

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
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        banned_until = parsers.parse_datetime_from_string(duration)
        if banned_until is None:
            await interaction.response.send_message(_(lc, "moderation.invalid_duration"), ephemeral=True)
            return

        if (banned_until - discord.utils.utcnow()).total_seconds() > 31_536_000:
            await interaction.response.send_message(_(lc, "moderation.tempban.too_long"), ephemeral=True)
            return

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(
            interaction, target=member, until=banned_until, reason=reason, type="tempban"
        )
        await self.bot.timer.create_timer(member.id, guild.id, type=TimerType.tempban, expires=banned_until)
        await guild.ban(member, reason=reason, delete_message_days=1)

        await interaction.followup.send(_(lc, "moderation.tempban.successfully_banned"), ephemeral=True)

    @app_commands.command(name="kick", description="Kicks an user from the guild.")
    @app_commands.describe(member="The member that should be kicked.", reason="Why the member should be kicked.")
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only
    async def kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.followup.defer(ephemeral=True)
        await _logging_helper.log_simple_punish_command(interaction, target=member, reason=reason, type="kick")
        await guild.kick(member, reason=reason)

        await interaction.followup.send(_(lc, "moderation.kick.successfully_kicked"), ephemeral=True)

    @app_commands.command(name="tempmute", description="Mutes an user for a specific time.")
    @app_commands.describe(
        member="The member that should be muted.",
        reason="Why the member should be muted.",
        duration="How long the member should be muted (max 28 days).",
    )
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.default_permissions(mute_members=True)
    @app_commands.guild_only
    async def tempmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        await interaction.response.defer(ephemeral=True)

        banned_until = parsers.parse_datetime_from_string(duration)
        if banned_until is None:
            await interaction.response.send_message(_(lc, "moderation.invalid_duration"), ephemeral=True)
            return

        if (banned_until - discord.utils.utcnow()).total_seconds() > 86400 * 28:
            await interaction.response.send_message(_(lc, "moderation.tempmute.too_long"), ephemeral=True)
            return

        if not await Moderation._can_execute_on(interaction, member):
            return

        await member.timeout(banned_until, reason=reason)
        await _logging_helper.log_simple_punish_command(
            interaction, target=member, until=banned_until, reason=reason, type="tempmute"
        )

        await interaction.followup.send(_(lc, "moderation.tempban.successfully_muted"), ephemeral=True)

    @app_commands.command(name="unban", description="Unbans an user from the guild.")
    @app_commands.describe(user="The member that should be unbanned.", reason="Why the member has been unbanned.")
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def unban(
        self, interaction: discord.Interaction, user: discord.User, reason: Optional[app_commands.Range[str, None, 512]]
    ):
        lc = interaction.locale
        guild = interaction.guild

        try:
            await guild.unban(user, reason=reason)
        except discord.NotFound:
            await interaction.response.send_message(_(lc, "moderation.unban.not_banned"), ephemeral=True)
            return
        await _logging_helper.log_simple_punish_command(interaction, target=user, reason=reason, type="unban")

        await self.bot.db.execute(
            "DELETE FROM timers WHERE target_id = $1 AND guild_id = $2 AND type = 'tempban'", user.id, guild.id
        )

        await interaction.response.send_message(_(lc, "moderation.unban.successfully_unbanned"), ephemeral=True)

    @app_commands.command(name="softban", description="Kicks an user from the guild and deletes their messages.")
    @app_commands.describe(member="The member that should be kicked.", reason="Why the member should be kicked.")
    @app_commands.checks.bot_has_permissions(ban_members=True)
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only
    async def softban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        guild = interaction.guild

        if not await Moderation._can_execute_on(interaction, member):
            return

        await interaction.response.defer(ephemeral=True)

        await _logging_helper.log_simple_punish_command(interaction, target=member, reason=reason, type="softban")
        await guild.ban(member, reason=reason, delete_message_days=1)
        await guild.unban(member, reason=reason)

        await interaction.followup.send(_(lc, "moderation.softban.successfully_kicked"), ephemeral=True)

    @app_commands.command(name="slowmode", description="Sets the slowmode of the current channel.")
    @app_commands.describe(duration="How long the slowmode should be (max 6hrs).")
    @app_commands.checks.cooldown(2, 10, key=lambda i: i.channel_id)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only
    async def slowmode(self, interaction: discord.Interaction, duration: Optional[app_commands.Range[int, 1, 21600]]):
        lc = interaction.locale

        if duration is None:
            await interaction.channel.edit(slowmode_delay=0)
            await interaction.response.send_message(_(lc, "moderation.slowmode.disabled"), ephemeral=True)
        else:
            await interaction.channel.edit(slowmode_delay=duration)
            await interaction.response.send_message(_(lc, "moderation.slowmode.enabled"), ephemeral=True)

    @app_commands.command(name="unmute", description="Unmutes an user.")
    @app_commands.describe(member="The member that should be unmuted.", reason="Why the member should be unmuted.")
    @app_commands.checks.bot_has_permissions(mute_members=True)
    @app_commands.default_permissions(mute_members=True)
    @app_commands.guild_only
    async def unmute(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: Optional[app_commands.Range[str, None, 512]],
    ):
        lc = interaction.locale
        await interaction.response.defer(ephemeral=True)

        if not await Moderation._can_execute_on(interaction, member):
            return

        await member.timeout(None, reason=_(lc, "moderation.unmute.reason"))
        await _logging_helper.log_simple_punish_command(interaction, target=member, type="unmute", reason=reason)

        await interaction.followup.send(_(lc, "moderation.unmute.successfully_unmuted"), ephemeral=True)

    @app_commands.command(name="invite-info", description="Shows information about a invite.")
    @app_commands.describe(invite="The invite you want to get information about.")
    @app_commands.checks.bot_has_permissions()
    @app_commands.checks.cooldown(2, 30, key=lambda i: (i.guild.id, i.author.id))
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only
    async def invite_info(self, interaction: discord.Interaction, invite: str):
        lc = interaction.locale

        if not DISCORD_INVITE.match(invite):
            await interaction.response.send_message(_(lc, "moderation.invite_info.invalid_invite"), ephemeral=True)
            return

        invite = await self.bot.fetch_invite(invite)
        if invite is None:
            await interaction.response.send_message(_(lc, "moderation.invite_info.not_found"), ephemeral=True)
            return

        embed = Embed(
            description=_(lc, "moderation.invite_info.description", code=invite.code),
            title=_(lc, "moderation.invite_info.title"),
        )
        embed.set_thumbnail(url=invite.guild.icon)

        embed.add_field(
            name=_(lc, "moderation.invite_info.creator"),
            value=f"> **{_(lc, 'id')}:** {invite.inviter.id}\n"
            f"> **{_(lc, 'name')}:** {invite.inviter}\n"
            f"> **{_(lc, 'moderation.invite_info.mention')}:** {invite.inviter.mention}",
        )
        embed.add_field(
            name=_(lc, "guild"),
            value=f"> **{_(lc, 'name')}:** {invite.guild.name}\n"
            f"> **{_(lc, 'id')}:** {invite.guild.id}\n"
            f"> **{_(lc, 'guild_info.about.vanity_url')}:** {invite.guild.vanity_url or _(lc, 'guild_info.about.no_vanity_url')}\n",
        )

        await interaction.response.send_message(embed=embed)

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
        ]

        if not current:
            return [app_commands.Choice(name=time["label"], value=time["value"]) for time in times]

        return [
            app_commands.Choice(name=time["label"], value=time["value"])
            for time in times
            if current.lower() in time["label"].lower()
        ]
