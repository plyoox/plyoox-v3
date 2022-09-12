from __future__ import annotations

import datetime
from typing import Optional, Union

import discord
from discord import utils, app_commands

from lib import colors, helper, extensions
from translation import _


class UserGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="user-info",
            description="Provides information about a guild member or user.",
            guild_only=True,
        )

    joined_group = app_commands.Group(name="joined", description="Provides join information about a member.")

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
        embed.add_field(name=_(locale, "user_info.joined.position"), value=f"> {position}")
        embed.add_field(
            name=_(locale, "user_info.joined.days_since"),
            value=f"> {(datetime.datetime.now(tz=datetime.timezone.utc) - member.joined_at).days}",
        )
        embed.add_field(name=_(locale, "joined_at"), value=helper.embed_timestamp_format(member.joined_at))

        if interaction.extras.get("deferred"):
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @staticmethod
    async def _send_about_response(
        interaction: discord.Interaction, *, member: Union[discord.Member, discord.User], ephemeral: bool = False
    ):
        lc = interaction.locale
        public_flags = helper.get_badges(member.public_flags)

        embed = extensions.Embed(
            title=_(lc, "user_info.about.user_information"),
            color=member.accent_color or colors.DISCORD_DEFAULT,
        )  # accent color is not provided in the default member object

        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.avatar.url)
        embed.add_field(
            name=_(lc, "user_info.about.account"),
            value=f"> __{_(lc, 'id')}:__ {member.id}\n"
            f"> __{_(lc, 'created_at')}:__ {utils.format_dt(member.created_at)}\n"
            f"> __{_(lc, 'user_info.about.bot')}:__ {_(lc, member.bot)}",
        )

        embed.add_field(
            name=f"{_(lc, 'user_info.about.public_badges')} ({len(public_flags)})",
            value=f"> {''.join(public_flags)}" if len(public_flags) else _(lc, "user_info.about.no_flags"),
        )

        if isinstance(member, discord.Member):
            roles = member.roles

            embed.insert_field_at(
                0,
                name=_(lc, "user"),
                value=f"> __{_(lc, 'nick')}:__ {member.nick or _(lc, 'user_info.about.no_nick')}\n"
                f"> __{_(lc, 'user_info.about.server_avatar')}:__ {_(lc, bool(member.guild_avatar))}",
            )
            embed.insert_field_at(
                1,
                name=_(lc, "guild"),
                value=f"> __{_(lc, 'joined_at')}:__ {utils.format_dt(member.joined_at)}\n"
                + (
                    f"> __{_(lc, 'user_info.about.member_verification')}:__ {_(lc, not member.pending)}\n"
                    if "MEMBER_VERIFICATION_GATE_ENABLED" in member.guild.features
                    else ""
                )
                + f"> __{_(lc, 'user_info.about.premium_subscriber')}:__ "
                f"{utils.format_dt(member.premium_since) if member.premium_since else _(lc, False)}",
            )

            formatted_roles = helper.format_roles(roles)
            embed.insert_field_at(
                3,
                name=f"{_(lc, 'roles')} ({len(roles) - 1})",
                value=f"> {helper.format_roles(roles)}" if len(formatted_roles) else _(lc, "no_roles"),
            )

        await interaction.response.send_message(embed=embed, ephemeral=ephemeral)

    @joined_group.command(name="position", description="Shows the user on a join position")
    @app_commands.describe(position="Join position on the guild")
    async def joined_position(self, interaction: discord.Interaction, position: app_commands.Range[int, 1]):
        """Provides join information based on the join position."""
        if interaction.guild.member_count is not None and position > interaction.guild.member_count:
            await interaction.response.send_message(_(interaction.locale, "user_info.joined.number_to_high"))
            return

        if not interaction.guild.chunked:
            interaction.extras["deferred"] = True
            await interaction.response.defer()
            await interaction.guild.chunk()

        members = [member for member in interaction.guild.members]
        members.sort(key=self.sort)

        try:
            member = members[position - 1]
        except KeyError:
            return helper.interaction_send(interaction, "user_info.joined.postion_no_member")

        await self._send_joined_response(interaction, member, position)

    @joined_group.command(name="member", description="Shows join information about a specific member.")
    @app_commands.describe(member="The member you want the join position from.")
    async def joined_member(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Provides join information based on the member. If no member is provided, the user that executed
        the command will be used.
        """
        current_member = member or interaction.user

        if not interaction.guild.chunked:
            interaction.extras["deferred"] = True
            await interaction.response.defer(ephemeral=True)
            await interaction.guild.chunk(cache=True)

        members = [member for member in interaction.guild.members]
        members.sort(key=self.sort)
        position = members.index(current_member) + 1

        await self._send_joined_response(interaction, current_member, position)

    @app_commands.command(name="about", description="Shows information's about a Discord member.")
    @app_commands.describe(member="The member you want the information about.")
    async def about(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows basic information about a user. If no member is provided, the user
        that executed the command will be used.
        """
        await self._send_about_response(interaction, member=member or interaction.user)

    @app_commands.command(name="avatar", description="Shows the avatar of a user.")
    @app_commands.describe(member="The member you want the avatar from.")
    async def avatar(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the avatar of a member. If no member is provided, the user
        that executed the command will be used.
        """
        current_member = member or interaction.user

        embed = extensions.Embed()
        embed.set_author(name=str(current_member))
        embed.set_image(url=current_member.display_avatar.url)

        await interaction.response.send_message(embed=embed)
