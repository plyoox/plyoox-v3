from __future__ import annotations

import io
import logging
import random
from typing import TYPE_CHECKING, Optional

import aiohttp
import discord
from discord import app_commands, ui
from discord.app_commands import locale_str as _
from discord.ext import commands

from lib import formatting, helper, extensions

if TYPE_CHECKING:
    from main import Plyoox
    from lib.types import LevelUserData

_log = logging.getLogger(__name__)


def get_xp_from_lvl(lvl: int):
    """Calculates the overall needed xp to gain this level."""
    xp = 100
    for i in range(1, lvl + 1):
        xp += get_level_xp(i)
    return xp


def get_level_xp(lvl: int) -> int:
    """Calculates the needed xp for the level."""
    return 5 * (lvl**2) + 50 * lvl + 100


def get_level_from_xp(xp: int) -> tuple[int, int]:
    """Calculates the level from the xp. Returns the current level and the remaining xp."""
    level = 0
    while xp >= get_level_xp(level):
        xp -= get_level_xp(level)
        level += 1
    return level, xp


RESET_LEVEL_CONFIRMATION_TEXT = "Yes, reset all levels"


class ResetGuildModal(ui.Modal):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(title=interaction.translate(_("Reset server levels")))

        self.bot: Plyoox = interaction.client
        self.question = ui.TextInput(
            label=interaction.translate(_("Are you sure you want to reset all levels?")),
            placeholder=f"{interaction.translate(_('Repeat:'))} {RESET_LEVEL_CONFIRMATION_TEXT}",
            required=True,
        )
        self.add_item(self.question)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.question.value.lower() != RESET_LEVEL_CONFIRMATION_TEXT.lower():
            await interaction.response.send_translated(_("Wrong answer provided, aborting."), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self.bot.db.execute("DELETE FROM level_user WHERE guild_id = $1", interaction.guild_id)

        await interaction.followup.send(
            interaction.translate(_("The level of all guild members has been successfully reset.")),
            ephemeral=True,
        )


class Leveling(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._cooldown_by_user = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.member)

        self.ctx_menu = app_commands.ContextMenu(
            name=_("View rank"),
            callback=self.rank_context_menu,
        )

        self.bot.tree.add_command(self.ctx_menu)

    level_group = app_commands.Group(
        name="level",
        description=_("Commands that are needed to interact with the level-system."),
        guild_only=True,
    )

    async def _fetch_member_data(self, member: discord.Member) -> LevelUserData:
        """Fetches the leveling data of a member."""
        return await self.bot.db.fetchrow(
            "SELECT * FROM level_user WHERE guild_id = $1 AND user_id = $2",
            member.guild.id,
            member.id,
        )

    async def _create_member_data(self, member: discord.Member, xp: int) -> None:
        """Creates a database entry for the member."""
        await self.bot.db.execute(
            "INSERT INTO level_user (guild_id, user_id, xp) VALUES ($1, $2, $3)",
            member.guild.id,
            member.id,
            xp,
        )

    async def _update_member_data(self, id: int, xp: int) -> None:
        """Adds a specific amount of xp to the user in the database."""
        await self.bot.db.execute("UPDATE level_user SET xp = xp + $1 WHERE id = $2", xp, id)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        cache = await self.bot.cache.get_leveling(interaction.guild_id)
        if not cache:
            if interaction.user.guild_permissions.administrator:
                await interaction.response.send_translated(
                    _("The level system has not been enabled. Go to the [Dashboard](https://plyoox.net) to enabled it."),
                    ephemeral=True,
                )
                return False

            await interaction.response.send_translated(_("This module is currently disabled."), ephemeral=True)

            return False

        return True

    async def _view_rank(
        self,
        interaction: discord.Interaction,
        *,
        member: discord.Member = None,
        ephemeral: bool = False,
    ):
        if self.bot.imager_url is None:
            _log.warning("No imager url given set, aborting...")

            await interaction.response.send_translated(
                _("The required infrastructure is currently not available."),
                ephemeral=True,
            )
            return

        guild = interaction.guild
        bot: Plyoox = interaction.client  # type: ignore

        user_data: LevelUserData = await self.bot.db.fetchrow(
            "WITH users AS (SELECT xp, user_id, row_number() OVER (ORDER BY xp DESC) AS rank FROM level_user WHERE guild_id = $1) SELECT xp, rank FROM users WHERE user_id = $2",
            guild.id,
            member.id,
        )

        if user_data is None:
            interaction.response.send_translated(
                _("This user has never written anything or is excluded."),
                ephemeral=True,
            )
            return

        current_level, remaining_xp = get_level_from_xp(user_data["xp"])
        required_xp = get_level_xp(current_level)

        params = {
            "language": "de" if interaction.locale == "de" else "en",
            "xp": remaining_xp,
            "required-xp": required_xp,
            "level": current_level,
            "username": member.name,
            "avatar": member.display_avatar.with_size(512).with_format("png").url,
            "discriminator": member.discriminator,
            "rank": user_data["rank"],
        }

        try:
            async with bot.session.get(f"{self.bot.imager_url}/api/level-card", params=params) as res:
                if res.status != 200:
                    text = await res.text()
                    _log.warning(f"Received status code {res.status} and data `{text}` while fetching level card.")

                    await interaction.response.send_translated(
                        _("The required infrastructure is currently not available."),
                        ephemeral=True,
                    )

                    return

                fp = io.BytesIO(await res.read())
                image = discord.File(fp, filename="level_card.png")

                await interaction.response.send_message(file=image, ephemeral=ephemeral)
        except aiohttp.ClientConnectionError as err:
            _log.error("Could not fetch level card", err)

            await interaction.response.send_translated(
                _("The required infrastructure is currently not available."),
                ephemeral=True,
            )
            return

    async def _add_level_roles(self, member: discord.Member):
        guild = member.guild

        if not guild.me.guild_permissions.manage_roles:
            return

        cache = await self.bot.cache.get_leveling(guild.id)
        if not cache or not cache.roles:
            return

        user_data = await self._fetch_member_data(member)
        if user_data is None:
            return

        level, _ = get_level_from_xp(user_data["xp"])

        roles = []

        for level_role in cache.roles:
            if level_role[1] > level:
                continue

            role = guild.get_role(level_role[0])
            if role is None:
                continue

            roles.append(role)

        await member.add_roles(*roles)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # ignore dm's and other bots
        if message.guild is None or message.author.bot:
            return

        member = message.author
        channel = message.channel
        guild = message.guild

        # user is on cooldown
        bucket = self._cooldown_by_user.get_bucket(message)
        if bucket.update_rate_limit(message.created_at.timestamp()):
            return False

        cache = await self.bot.cache.get_leveling(guild.id)

        # leveling is deactivated on this guild
        if not cache:
            return

        # ignore no xp channels
        if channel.id in cache.exempt_channels:
            return

        # ignore members with the no xp role
        if cache.exempt_role in member._roles:
            return

        message_xp = random.randint(15, 25)  # generate a random amount of xp between 15 and 25
        member_data = await self._fetch_member_data(member)

        if member.premium_since is not None and cache.booster_xp_multiplier is not None:
            message_xp *= cache.booster_xp_multiplier

        # member has no data saved
        if member_data is None:
            await self._create_member_data(member, message_xp)
            return

        await self._update_member_data(member_data["id"], message_xp)

        before_level = get_level_from_xp(member_data["xp"])[0]  # level with the current xp
        after_level = get_level_from_xp(member_data["xp"] + message_xp)[0]  # level with the added xp
        highest_add_role = None

        if before_level != after_level:
            # only add role if available and the bot has proper permissions
            if len(cache.roles) and guild.me.guild_permissions.manage_roles:
                add_role_id = list(filter(lambda r: r[1] == after_level, cache.roles))
                if add_role_id:
                    highest_add_role = guild.get_role(add_role_id[0][0])

                    if cache.remove_roles and highest_add_role:
                        try:
                            await member.add_roles(highest_add_role, reason="Add new level role")

                            remove_roles = []

                            # adds the roles that should be removed to a list
                            # that are all roles that are not for the current level
                            for [role_id, level] in cache.roles:
                                if level == after_level:
                                    continue

                                new_role = guild.get_role(role_id)
                                if new_role is not None:
                                    remove_roles.append(new_role)

                            await member.remove_roles(*remove_roles, reason="Remove old level roles")
                        except discord.Forbidden:
                            pass
                    else:
                        add_lvl_roles = []

                        # adds all roles that are for the current level or below
                        for [role_id, role_level] in cache.roles:
                            if role_id in member._roles:
                                continue

                            if role_level > after_level:
                                continue

                            new_role = guild.get_role(role_id)
                            if new_role is not None:
                                add_lvl_roles.append(new_role)

                        try:
                            await member.add_roles(*add_lvl_roles, reason="Add new level roles")
                        except discord.Forbidden:
                            pass

            if cache.message:
                # format the messages with the variables
                f_level = formatting.LevelFormatObject(level=after_level, role=highest_add_role)
                level_message = formatting.format_leveling_message(cache.message, member=member, level=f_level)

                if not level_message:  # can be none when {level.role} is used and no role was given to the user
                    if level_message is not None:  # currently only for debugging
                        _log.warning(f'Message is empty after formatting: "{cache.message}" -> "{level_message}"')

                    return

                # if a channel is given send the message to it
                # else the message will be sent to the current channel
                if cache.channel is None:
                    await helper.permission_check(channel, content=level_message)
                else:
                    level_channel = guild.get_channel(cache.channel)
                    await helper.permission_check(level_channel, content=level_message)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.pending:
            await self._add_level_roles(member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.pending and not after.pending:
            await self._add_level_roles(after)

    async def rank_context_menu(self, interaction: discord.Interaction, member: discord.Member):
        """Shows the current ranking information about a member. This can is context menu command."""
        await self._view_rank(interaction, member=member, ephemeral=True)

    @level_group.command(
        name="rank",
        description=_("Shows information about the current rank of a member."),
    )
    @app_commands.describe(member=_("The member from whom you want the rank."))
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the current ranking information about a member. If no member is provided, the user that executed
        the command will be used.
        """
        await self._view_rank(interaction, member=member or interaction.user)

    @level_group.command(name="show-roles", description=_("Shows the available level roles."))
    async def show_roles(self, interaction: discord.Interaction):
        """Shows the roles that are gain able through the level system"""
        guild = interaction.guild
        bot: Plyoox = interaction.client

        # Result must be defined, because the command can only be invoked if the level system is enabled.
        pg_result = await bot.db.fetchrow("SELECT roles, remove_roles FROM level_config WHERE id = $1", guild.id)

        level_roles = [[role["role"], role["level"]] for role in (pg_result["roles"] or [])]
        if len(level_roles) == 0:
            await interaction.response.send_translated(_("The server has no level roles configured."), ephemeral=True)
            return

        roles: list[str] = []

        for [role_id, level] in level_roles:
            role = guild.get_role(role_id)
            if role is not None:
                roles.append(f"{level} - {role.mention}")

        remove_roles_str = interaction.translate(_("Yes") if pg_result["remove_roles"] else _("No"))

        embed = extensions.Embed(title=interaction.translate(_("Available level roles")))
        embed.description = (
            interaction.translate(_("**Remove previous roles:** {remove_roles}")).format(remove_roles=remove_roles_str)
            + "\n"
        )
        embed.description += "\n".join(roles)

        await interaction.response.send_message(embeds=[embed])

    @level_group.command(
        name="top",
        description=_("Lists the top 10 users with the highest level on this guild."),
    )
    async def top(self, interaction: discord.Interaction):
        guild = interaction.guild
        bot: Plyoox = interaction.client

        await interaction.response.defer(ephemeral=True)

        if not guild.chunked:
            await guild.chunk(cache=True)

        top_users = []
        offset = 0

        while len(top_users) < 10:
            level_users = await bot.db.fetch(
                "SELECT user_id, xp FROM level_user WHERE guild_id = $1 ORDER BY xp DESC LIMIT 25 OFFSET $2",
                guild.id,
                offset,
            )

            offset += 25

            for level_user in level_users:
                member = guild.get_member(level_user["user_id"])

                if member is not None:
                    current_level, current_xp = get_level_from_xp(level_user["xp"])
                    required_xp = get_level_xp(current_level)

                    top_users.append(
                        {
                            "member": member,
                            "level": current_level,
                            "xp_progress": f"{current_xp}/{required_xp}",
                        }
                    )

                    if len(top_users) >= 10:
                        break

            if len(level_users) != 25:
                break

        if len(top_users) == 0:
            await interaction.followup.send(
                interaction.translate(_("There is no user tracked by the level system.")),
                ephemeral=True,
            )
            return

        embed = extensions.Embed(
            title=interaction.translate(_("Top 10 users with the highest level")),
        )

        for index, top_user in enumerate(top_users, start=1):
            embed.add_field(
                name=f"{index}. {top_user['member'].display_name}",
                value=f"> {interaction.translate(_('Level'))} {top_user['level']}\n"
                f"> {top_user['xp_progress']} {interaction.translate(_('XP'))}",
                inline=True,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="reset-level",
        description=_("Resets the level of a member. This action cannot be undone."),
    )
    @app_commands.describe(member=_("The member from whom you want to reset rank."))
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only
    async def reset_level(self, interaction: discord.Interaction, member: discord.Member):
        guild = interaction.guild

        await self.bot.db.execute(
            "DELETE FROM level_user WHERE user_id = $1 AND guild_id = $2",
            member.id,
            guild.id,
        )

        if guild.me.guild_permissions.manage_roles:
            leveling_cache = await self.bot.cache.get_leveling(guild.id)
            if leveling_cache and leveling_cache.roles:
                roles_to_remove = []
                for [role_id, __] in leveling_cache.roles:
                    if role_id in member._roles:
                        roles_to_remove.append(discord.Object(id=role_id))

                await member.remove_roles(
                    *roles_to_remove,
                    reason=interaction.translate(_("The level progress of this user was reset.")),
                )

        embed = extensions.Embed(description=interaction.translate(_("The levels of this user were successfully reset.")))
        await interaction.response.send_message(embeds=[embed], ephemeral=True)

    @app_commands.command(
        name="reset-guild-levels",
        description=_("Resets the levels of all members in the guild. This action cannot be undone."),
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only
    async def reset_guild_levels(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ResetGuildModal(interaction))


async def setup(bot: Plyoox):
    await bot.add_cog(Leveling(bot))
