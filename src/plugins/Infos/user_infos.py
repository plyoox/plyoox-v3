import datetime
from typing import Optional

import discord.app_commands as cmds
from discord import Interaction, Member, Embed, utils, Role, PublicUserFlags

from lib import checks
from src.translation import interaction_send, _
from utils import emojis, colors


class UserInfo(cmds.Group):
    def __init__(self):
        super().__init__(
            name="user-info", description="Provides information about a guild member or user."
        )

    joined_group = cmds.Group(
        name="joined", description="Provides join information about a member."
    )

    async def interaction_check(self, interaction: Interaction) -> bool:
        return await checks.guild_only_check(interaction)

    @staticmethod
    def _format_roles(roles: list[Role], /) -> str | None:
        if len(roles) == 1:
            return None

        result = []
        roles.reverse()
        roles.pop()

        for role in roles[:44]:
            result.append(role.mention)

        if len(roles) > 44:
            return " ".join(result) + "..."

        return " ".join(result)

    @staticmethod
    def sort(list_user: Member):
        return list_user.joined_at

    @staticmethod
    async def _send_joined_response(
        interaction: Interaction, member: Member, position: int
    ) -> None:
        locale = interaction.locale

        embed = Embed(title=_(locale, "user_info.joined.title"), color=colors.DISCORD_DEFAULT)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.add_field(
            name=_(locale, "user_info.joined.position"), value=f"> `{position}`", inline=False
        )
        embed.add_field(
            name=_(locale, "user_info.joined.days_since"),
            value=f"> `{(datetime.datetime.now(tz=datetime.timezone.utc) - member.joined_at).days}`",
            inline=False,
        )
        embed.add_field(
            name=_(locale, "user_info.joined_at"),
            value=f"> {utils.format_dt(member.joined_at)}",
            inline=False,
        )

        await interaction.response.send_message(embeds=[embed])

    @staticmethod
    def _get_badges(flags: PublicUserFlags):
        flag_list = []
        if flags.staff:
            flag_list.append(emojis.staff)
        if flags.partner:
            flag_list.append(emojis.partner)
        if flags.bug_hunter:
            flag_list.append(emojis.bughunter)
        if flags.early_supporter:
            flag_list.append(emojis.early_supporter)
        if flags.hypesquad:
            flag_list.append(emojis.hypesquad)
        if flags.hypesquad_balance:
            flag_list.append(emojis.hypesquad_balance)
        if flags.hypesquad_brilliance:
            flag_list.append(emojis.hypesquad_brilliance)
        if flags.hypesquad_bravery:
            flag_list.append(emojis.hypesquad_bravery)
        if flags.verified_bot_developer:
            flag_list.append(emojis.botdev)
        if flags.bug_hunter_level_2:
            flag_list.append(emojis.bughunter2)

        return flag_list

    @joined_group.command(name="position", description="Shows the user on a join position")
    @cmds.describe(position="Join position on the guild")
    async def join_position(self, interaction: Interaction, position: cmds.Range[int, 1]):
        if interaction.guild.member_count is not None and position > interaction.guild.member_count:
            return interaction_send(interaction, "user_info.joined.number_to_high")

        members = [member for member in interaction.guild.members]
        members.sort(key=self.sort)

        try:
            member = members[position - 1]
        except KeyError:
            return interaction_send(interaction, "user_info.joined.postion_no_member")

        await self._send_joined_response(interaction, member, position)

    @joined_group.command(
        name="member", description="Shows join information about a specific member."
    )
    @cmds.describe(member="The member you want the join position from.")
    async def join_member(self, interaction: Interaction, member: Optional[Member]):
        current_member = member or interaction.user

        members = [member for member in interaction.guild.members]
        members.sort(key=self.sort)
        position = members.index(current_member) + 1

        await self._send_joined_response(interaction, current_member, position)

    @cmds.command(name="about", description="Shows information's about a Discord member.")
    @cmds.describe(member="The member you want the information about.")
    async def about(self, interaction: Interaction, member: Optional[Member]):
        current_member = member or interaction.user
        roles = current_member.roles
        lc = interaction.locale
        public_flags = self._get_badges(current_member.public_flags)

        embed = Embed(
            title=_(lc, "user_info.about.user_information"),
            color=current_member.accent_color or colors.DISCORD_DEFAULT,
        )
        embed.set_author(name=str(current_member), icon_url=current_member.display_avatar.url)
        embed.set_thumbnail(url=current_member.avatar.url)
        embed.add_field(
            name=_(lc, "user"),
            value=f"> __{_(lc, 'id')}:__ {current_member.id}\n"
            f"> __{_(lc, 'nick')}:__ {current_member.nick or _(lc, 'user_info.about.no_nick')}\n"
            f"> __{_(lc, 'user_info.about.server_avatar')}:__ {_(lc, bool(current_member.guild_avatar))}",
            inline=False,
        )
        embed.add_field(
            name=_(lc, "guild"),
            value=f"> __{_(lc, 'user_info.joined_at')}:__ {utils.format_dt(current_member.joined_at)}\n"
            f"> __{_(lc, 'user_info.about.member_verification')}:__ {_(lc, current_member.pending)}\n"
            f"> __{_(lc, 'user_info.about.premium_subscriber')}:__ "
            f"{utils.format_dt(current_member.premium_since) if current_member.premium_since else _(lc, False)}",
            inline=False,
        )
        embed.add_field(
            name=_(lc, "user_info.about.account"),
            value=f"> __{_(lc, 'created_at')}:__ {utils.format_dt(current_member.created_at)}\n"
            f"> __{_(lc, 'user_info.about.bot')}:__ {_(lc, current_member.bot)}",
        )
        embed.add_field(
            name=f"{_(lc, 'roles')} ({len(roles) - 1})",
            value=f"> {self._format_roles(roles) or _(lc, 'no_roles')}",
            inline=False,
        )
        embed.add_field(
            name=f"{_(lc, 'user_info.about.public_badges')} ({len(public_flags)})",
            value=f"> {''.join(public_flags) if len(public_flags) else _(lc, 'user_info.about.no_flags')}",
            inline=False,
        )

        await interaction.response.send_message(embeds=[embed])

    @cmds.command(name="avatar", description="Shows the avatar of a user.")
    @cmds.describe(member="The member you want the avatar from.")
    async def avatar(self, interaction: Interaction, member: Optional[Member]):
        current_member = member or interaction.user

        embed = Embed(color=colors.DISCORD_DEFAULT)
        embed.set_author(name=str(current_member))
        embed.set_image(url=current_member.display_avatar.url)

        await interaction.response.send_message(embeds=[embed])
