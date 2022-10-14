from __future__ import annotations

import io
import logging
import os
import random
import time
from typing import TYPE_CHECKING, Optional

import aiohttp
import discord
from discord import app_commands, ui
from discord.ext import commands

from lib import formatting, helper, extensions
from translation import _

if TYPE_CHECKING:
    from main import Plyoox
    from lib.types import LevelUserData

_T = app_commands.locale_str
_log = logging.getLogger(__name__)


def get_xp_from_lvl(lvl: int):
    """Calculates the overall needed xp to gain this level."""
    xp = 100
    for _ in range(1, lvl + 1):
        xp += get_level_xp(_)
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


class ResetGuildModal(ui.Modal):
    def __init__(self, interaction: discord.Interaction):
        locale = interaction.locale

        super().__init__(title=_(locale, "level.reset_guild_level.modal_title"))

        self.bot: Plyoox = interaction.client  # type: ignore
        self.question = ui.TextInput(
            label=_(locale, "level.reset_guild_level.question"),
            placeholder=_(locale, "level.reset_guild_level.placeholder"),
            required=True,
        )
        self.add_item(self.question)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        lc = interaction.locale
        if self.question.value.lower() != _(lc, "level.reset_guild_level.reset_text").lower():
            await interaction.response.send_message(_(lc, "level.reset_guild_level.wrong_answer"), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self.bot.db.execute("DELETE FROM leveling_users WHERE guild_id = $1", interaction.guild_id)
        await interaction.followup.send(_(lc, "level.reset_guild_level.success"), ephemeral=True)


class Leveling(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._cooldown_by_user = commands.CooldownMapping.from_cooldown(1, 60, commands.BucketType.member)

        self.ctx_menu = app_commands.ContextMenu(
            name=_T("View rank", key="view-rank"),
            callback=self.rank_context_menu,
        )

        self.bot.tree.add_command(self.ctx_menu)
        self.imager_url = os.getenv("IMAGER_URL")

    level_group = app_commands.Group(
        name="level",
        description="Commands that are needed to interact with the level-system.",
        guild_only=True,
    )

    async def _fetch_member_data(self, member: discord.Member) -> LevelUserData:
        """Fetches the leveling data of a member."""
        return await self.bot.db.fetchrow(
            "SELECT * FROM leveling_users WHERE guild_id = $1 AND user_id = $2",
            member.guild.id,
            member.id,
        )

    async def _create_member_data(self, member: discord.Member, xp: int) -> None:
        """Creates a database entry for the member."""
        await self.bot.db.execute(
            "INSERT INTO leveling_users (guild_id, user_id, xp) VALUES ($1, $2, $3)",
            member.guild.id,
            member.id,
            xp,
        )

    async def _update_member_data(self, id: int, xp: int) -> None:
        """Adds a specific amount of xp to the user in the database."""
        await self.bot.db.execute("UPDATE leveling_users SET xp = xp + $1 WHERE id = $2", xp, id)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def _view_rank(
        self, interaction: discord.Interaction, *, member: discord.Member = None, ephemeral: bool = False
    ):
        if self.imager_url is None:
            _log.warning("No imager url given set, aborting...")

            await interaction.response.send_message(
                _(interaction.locale, "level.infrastructure_offline"), ephemeral=True
            )
            return

        guild = interaction.guild
        bot: Plyoox = interaction.client  # type: ignore

        user_data: LevelUserData = await self.bot.db.fetchrow(
            "WITH users AS (SELECT xp, user_id, row_number() OVER (ORDER BY xp DESC) AS rank FROM leveling_users WHERE guild_id = $1) SELECT xp, rank FROM users WHERE user_id = $2",
            guild.id,
            member.id,
        )

        if user_data is None:
            await helper.interaction_send(interaction, "level.rank.no_data")
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
            async with bot.session.get(f"{self.imager_url}/api/level-card", params=params) as res:
                if res.status != 200:
                    text = await res.text()
                    _log.warning(f"Received status code {res.status} and data `{text}` while fetching level card.")
                    
                    await interaction.response.send_message(
                        _(interaction.locale, "level.infrastructure_offline"), ephemeral=True
                    )
                    return
                    
                fp = io.BytesIO(await res.read())
                image = discord.File(fp, filename="level_card.png")

                await interaction.response.send_message(file=image, ephemeral=ephemeral)
        except aiohttp.ClientConnectionError as err:
            _log.error("Could not fetch level card", err)

            await interaction.response.send_message(
                _(interaction.locale, "level.infrastructure_offline"), ephemeral=True
            )
            return

    async def _add_level_roles(self, member: discord.Member):
        guild = member.guild

        if not guild.me.guild_permissions.manage_roles:
            return

        cache = await self.bot.cache.get_leveling(guild.id)
        if cache is None or not cache.active or not cache.roles:
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
        if cache is None or not cache.active:
            return

        # ignore no xp channels
        if channel.id in cache.no_xp_channels:
            return

        # ignore members with the no xp role
        if cache.no_xp_role in member._roles:
            return

        message_xp = random.randint(15, 25)  # generate a random amount of xp between 15 and 25
        member_data = await self._fetch_member_data(member)

        if member.premium_since is not None and cache.booster_xp_multiplicator is not None:
            message_xp *= cache.booster_xp_multiplicator

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

    @level_group.command(name="rank", description="Shows information about the current rank of a member.")
    @app_commands.describe(member=_T("The member from whom you want the rank.", key="level.rank.member"))
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the current ranking information about a member. If no member is provided, the user that executed
        the command will be used.
        """
        await self._view_rank(interaction, member=member or interaction.user)

    @level_group.command(name="show-roles", description="Shows the available level roles.")
    async def show_roles(self, interaction: discord.Interaction):
        """Shows the roles that are gain able through the level system"""
        lc = interaction.locale
        guild = interaction.guild
        bot: Plyoox = interaction.client  # type: ignore

        level_roles: list[list[int, int]] = await bot.db.fetchval("SELECT roles FROM leveling WHERE id = $1", guild.id)
        if not level_roles:
            await helper.interaction_send(interaction, "level.level_roles.no_roles")
            return

        roles: list[str] = []

        for [role_id, level] in level_roles:
            role = guild.get_role(role_id)
            if role is not None:
                roles.append(f"{level} - {role.mention}")

        embed = extensions.Embed(title=_(lc, "level.level_roles.title"))
        embed.description = "\n".join(roles)

        await interaction.response.send_message(embed=embed)

    @level_group.command(name="top", description="Lists the top 10 users with the highest level on this guild.")
    async def top(self, interaction: discord.Interaction):
        lc = interaction.locale
        guild = interaction.guild
        bot: Plyoox = interaction.client  # type: ignore

        await interaction.response.defer(ephemeral=True)

        if not guild.chunked:
            await guild.chunk(cache=True)

        top_users = []
        offset = 0

        while len(top_users) < 10:
            level_users = await bot.db.fetch(
                "SELECT user_id, xp FROM leveling_users WHERE guild_id = $1 ORDER BY xp DESC LIMIT 25 OFFSET $2",
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
                        {"member": member, "level": current_level, "xp_progress": f"{current_xp}/{required_xp}"}
                    )

                    if len(top_users) >= 10:
                        break

            if len(level_users) != 25:
                break

        if len(top_users) == 0:
            await interaction.followup.send(_(lc, "level.top.no_users"))
            return

        embed = extensions.Embed(
            title=_(lc, "level.top.title"),
        )

        for index, top_user in enumerate(top_users, start=1):
            embed.add_field(
                name=f"{index}. {top_user['member'].display_name}",
                value=f"> {_(lc, 'level.top.level')} {top_user['level']}\n"
                f"> {top_user['xp_progress']} {_(lc, 'level.top.xp')}",
                inline=True,
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="reset-level", description="Resets the level of a member. This action cannot be undone.")
    @app_commands.describe(member="The member from whom you want to reset rank.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only
    async def reset_level(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale
        guild = interaction.guild

        await self.bot.db.execute(
            "DELETE FROM leveling_users WHERE user_id = $1 AND guild_id = $2", member.id, guild.id
        )

        if guild.me.guild_permissions.manage_roles:
            leveling_cache = await self.bot.cache.get_leveling(guild.id)
            if leveling_cache is not None:
                if leveling_cache.roles:
                    roles_to_remove = []
                    for [role_id, __] in leveling_cache.roles:
                        if role_id in member._roles:
                            roles_to_remove.append(discord.Object(id=role_id))

                    await member.remove_roles(*roles_to_remove, reason=_(lc, "level.reset_level.reset_reason"))

        embed = extensions.Embed(description=_(lc, "level.reset_level.success"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="reset-guild-levels",
        description="Resets the levels of all members in the guild. This action cannot be undone.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only
    async def reset_guild_levels(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ResetGuildModal(interaction))


async def setup(bot: Plyoox):
    await bot.add_cog(Leveling(bot))
