from __future__ import annotations

import datetime
from typing import Optional

import discord
from discord import utils, app_commands

from lib import colors, helper, extensions
from translation import _


_T = app_commands.locale_str


class UserGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name=_T("user-info", key="user-info.name"),
            description=_T("Provides information about a guild member or user.", key="user-info.description"),
            guild_only=True,
        )

    joined_group = app_commands.Group(
        name=_T("joined", key="user-info.joined.name"),
        description=_T("Provides join information about a member.", key="user-info.joined.description"),
    )

    @staticmethod
    def sort(list_user: discord.Member):
        """Basic sort function, based on when a member joined the guild."""
        return list_user.joined_at

    @staticmethod
    async def _send_joined_response(interaction: discord.Interaction, member: discord.Member, position: int) -> None:
        """Shortcut to send the response for the joined command."""
        locale = interaction.locale

        embed = extensions.Embed(title=_(locale, "user_info.joined.title"))
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.add_field(name=_(locale, "user_info.joined.position"), value=f"> `{position}`")
        embed.add_field(
            name=_(locale, "user_info.joined.days_since"),
            value=f"> `{(datetime.datetime.now(tz=datetime.timezone.utc) - member.joined_at).days}`",
        )
        embed.add_field(name=_(locale, "joined_at"), value=f"> {discord.utils.format_dt(member.joined_at)}")

        await interaction.response.send_message(embed=embed)

    @joined_group.command(
        name=_T("position", key="user-info.joined.position.name"),
        description=_T("Shows the user on a join position", key="user-info.joined.position.description"),
    )
    @app_commands.describe(position=_T("Join position on the guild", key="user-info.joined.position.position"))
    async def joined_position(self, interaction: discord.Interaction, position: app_commands.Range[int, 1]):
        """Provides join information based on the join position."""
        if interaction.guild.member_count is not None and position > interaction.guild.member_count:
            return helper.interaction_send(interaction, "user_info.joined.number_to_high")

        members = [member for member in interaction.guild.members]
        members.sort(key=self.sort)

        try:
            member = members[position - 1]
        except KeyError:
            return helper.interaction_send(interaction, "user_info.joined.postion_no_member")

        await self._send_joined_response(interaction, member, position)

    @joined_group.command(
        name=_T("member", key="user-info.joined.member.name"),
        description=_T("Shows join information about a specific member.", key="user-info.joined.member.description"),
    )
    @app_commands.describe(
        member=_T("The member you want the join position from.", key="user-info.joined.member.member")
    )
    async def joined_member(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Provides join information based on the member. If no member is provided, the user that executed
        the command will be used.
        """
        current_member = member or interaction.user

        members = [member for member in interaction.guild.members]
        members.sort(key=self.sort)
        position = members.index(current_member) + 1

        await self._send_joined_response(interaction, current_member, position)

    @app_commands.command(
        name=_T("about", key="user-info.about.name"),
        description=_T("Shows information's about a Discord member.", key="user-info.about.description"),
    )
    @app_commands.describe(member=_T("The member you want the information about.", key="user-info.about.member"))
    async def about(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows basic information about a user. If no member is provided, the user
        that executed the command will be used.
        """
        current_member = member or interaction.user
        roles = current_member.roles
        lc = interaction.locale
        public_flags = helper.get_badges(current_member.public_flags)

        embed = extensions.Embed(
            title=_(lc, "user_info.about.user_information"),
            color=current_member.accent_color or colors.DISCORD_DEFAULT,
        )  # accent color is not provided in the default member object

        embed.set_author(name=str(current_member), icon_url=current_member.display_avatar.url)
        embed.set_thumbnail(url=current_member.avatar.url)
        embed.add_field(
            name=_(lc, "user"),
            value=f"> __{_(lc, 'id')}:__ {current_member.id}\n"
            f"> __{_(lc, 'nick')}:__ {current_member.nick or _(lc, 'user_info.about.no_nick')}\n"
            f"> __{_(lc, 'user_info.about.server_avatar')}:__ {_(lc, bool(current_member.guild_avatar))}",
        )
        embed.add_field(
            name=_(lc, "guild"),
            value=f"> __{_(lc, 'joined_at')}:__ {utils.format_dt(current_member.joined_at)}\n"
            f"> __{_(lc, 'user_info.about.member_verification')}:__ {_(lc, current_member.pending)}\n"
            f"> __{_(lc, 'user_info.about.premium_subscriber')}:__ "
            f"{utils.format_dt(current_member.premium_since) if current_member.premium_since else _(lc, False)}",
        )
        embed.add_field(
            name=_(lc, "user_info.about.account"),
            value=f"> __{_(lc, 'created_at')}:__ {utils.format_dt(current_member.created_at)}\n"
            f"> __{_(lc, 'user_info.about.bot')}:__ {_(lc, current_member.bot)}",
        )
        embed.add_field(
            name=f"{_(lc, 'roles')} ({len(roles) - 1})", value=f"> {helper.format_roles(roles) or _(lc, 'no_roles')}"
        )
        embed.add_field(
            name=f"{_(lc, 'user_info.about.public_badges')} ({len(public_flags)})",
            value=f"> {''.join(public_flags) if len(public_flags) else _(lc, 'user_info.about.no_flags')}",
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name=_T("avatar", key="user-info.avatar.name"),
        description=_T("Shows the avatar of a user.", key="user-info.avatar.description"),
    )
    @app_commands.describe(member=_T("The member you want the avatar from.", key="user-info.avatar.member"))
    async def avatar(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the avatar of a member. If no member is provided, the user
        that executed the command will be used.
        """
        current_member = member or interaction.user

        embed = extensions.Embed()
        embed.set_author(name=str(current_member))
        embed.set_image(url=current_member.display_avatar.url)

        await interaction.response.send_message(embed=embed)
