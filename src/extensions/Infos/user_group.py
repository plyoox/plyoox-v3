from __future__ import annotations

import datetime
from typing import Optional, Union

import discord
from discord import utils, app_commands
from discord.app_commands import locale_str as _

from lib import colors, helper, extensions


class UserGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="user-info",
            description=_("Provides information about a guild member or user."),
            guild_only=True,
        )

    joined_group = app_commands.Group(name="joined", description=_("Provides join information about a member."))

    @staticmethod
    def sort(list_user: discord.Member):
        """Basic sort function, based on when a member joined the guild."""
        return list_user.joined_at

    @staticmethod
    async def _send_joined_response(interaction: discord.Interaction, member: discord.Member, position: int) -> None:
        """Shortcut to send the response for the joined command."""
        embed = extensions.Embed(title=interaction.translate(_("Join information")))
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.add_field(name=interaction.translate(_("Position")), value=f"> {position}")
        embed.add_field(
            name=interaction.translate(_("Days since joined")),
            value=f"> {(datetime.datetime.now(tz=datetime.timezone.utc) - member.joined_at).days}",
        )
        embed.add_field(name=interaction.translate(_("Joined at")), value=helper.embed_timestamp_format(member.joined_at))

        if interaction.extras.get("deferred"):
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @staticmethod
    async def _send_about_response(
        interaction: discord.Interaction, *, member: Union[discord.Member, discord.User], ephemeral: bool = False
    ):
        public_flags = helper.get_badges(member.public_flags)

        embed = extensions.Embed(
            title=interaction.translate(_("User information")),
            color=member.accent_color or colors.DISCORD_DEFAULT,
        )  # accent color is not provided in the default member object

        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name=interaction.translate(_("Account")),
            value=f"> __{interaction.translate(_('Id'))}:__ {member.id}\n"
            f"> __{interaction.translate(_('Created at'))}:__ {utils.format_dt(member.created_at)}\n"
            f"> __{interaction.translate(_('Bot'))}:__ {interaction.translate(_('Yes') if member.bot else _('No'))}",
        )

        embed.add_field(
            name=f"{interaction.translate(_('Public Badges'))} ({len(public_flags)})",
            value=f"> {''.join(public_flags)}" if len(public_flags) else interaction.translate(_('No public badges')),
        )

        if isinstance(member, discord.Member):
            roles = member.roles

            embed.insert_field_at(
                0,
                name=interaction.translate(_("User information")),
                value=f"> __{interaction.translate(_('Nick'))}:__ {member.nick or interaction.translate(_('No nick'))}\n"
                f"> __{interaction.translate(_('Server avatar'))}:__ {interaction.translate(_('Yes') if member.guild_avatar else _('No'))}\n",
            )
            embed.insert_field_at(
                1,
                name=interaction.translate(_("Guild")),
                value=f"> __{interaction.translate(_('Joined at'))}:__ {utils.format_dt(member.joined_at)}\n"
                + (
                    f"> __{interaction.translate(_('Completed verification'))}:__ {interaction.translate(_('Yes') if member.pending else _('No'))}\n"
                    if "MEMBER_VERIFICATION_GATE_ENABLED" in member.guild.features
                    else ""
                )
                + f"> __{interaction.translate(_('Boosts guild'))}:__ "
                f"{utils.format_dt(member.premium_since) if member.premium_since else interaction.translate(_('No'))}",
            )

            formatted_roles = helper.format_roles(roles)
            embed.insert_field_at(
                3,
                name=f"{interaction.translate(_('Roles'))} ({len(roles) - 1})",
                value=f"> {formatted_roles}" if formatted_roles else interaction.translate(_('No roles')),
            )

        await interaction.response.send_message(embeds=[embed], ephemeral=ephemeral)

    @joined_group.command(name="position", description=_("Displays the user at the join position."))
    @app_commands.describe(position=_("Joining position in the server."))
    async def joined_position(self, interaction: discord.Interaction, position: app_commands.Range[int, 1]):
        """Provides join information based on the join position."""
        if interaction.guild.member_count is not None and position > interaction.guild.member_count:
            await interaction.response.send_translated(_("No member found at this position."))
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
            await interaction.response.send_translated(_("No member found at this position."))
            return

        await self._send_joined_response(interaction, member, position)

    @joined_group.command(name="member", description=_("Shows join information about a specific member."))
    @app_commands.describe(member=_("The member about whom you want the information."))
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

    @app_commands.command(name="about", description=_("Shows information's about a member."))
    @app_commands.describe(member=_("The member you want the information about."))
    async def about(self, interaction: discord.Interaction, member: Optional[Union[discord.Member, discord.User]]):
        """Shows basic information about a user. If no member is provided, the user
        that executed the command will be used.
        """
        await self._send_about_response(interaction, member=member or interaction.user)

    @app_commands.command(name="avatar", description=_("Shows the avatar of a user."))
    @app_commands.describe(member=_("The member you want the avatar from."))
    async def avatar(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the avatar of a member. If no member is provided, the user
        that executed the command will be used.
        """
        current_member = member or interaction.user

        embed = extensions.Embed()
        embed.set_author(name=str(current_member))
        embed.set_image(url=current_member.display_avatar.url)

        await interaction.response.send_message(embed=embed)
