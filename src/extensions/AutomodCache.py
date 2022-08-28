from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from main import Plyoox


class AutomodCache(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

        self._automod_rules: dict[int, dict[int, discord.AutoModRule]] = {}

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        try:
            del self._automod_rules[guild.id]
        except KeyError:
            pass

    @commands.Cog.listener()
    async def on_automod_rule_create(self, rule: discord.AutoModRule) -> None:
        if self._automod_rules.get(rule.guild.id) is not None:
            self._automod_rules[rule.guild.id][rule.id] = rule

    @commands.Cog.listener()
    async def on_automod_rule_update(self, rule: discord.AutoModRule) -> None:
        if self._automod_rules.get(rule.guild.id) is not None:
            self._automod_rules[rule.guild.id][rule.id] = rule

    @commands.Cog.listener()
    async def on_automod_rule_delete(self, rule: discord.AutoModRule) -> None:
        try:
            del self._automod_rules[rule.guild.id][rule.id]
        except KeyError:
            pass

    async def get_automod_rules(self, guild_id: int) -> list[dict] | None:
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            return

        existing_rules = self._automod_rules.get(guild.id)

        if not guild.me.guild_permissions.manage_permissions:
            if existing_rules is not None:
                del self._automod_rules[guild.id]
            raise commands.MissingPermissions([])

        if existing_rules is not None:
            return [r.to_dict() for r in existing_rules.values()]

        rules = await guild.fetch_automod_rules()
        self._automod_rules[guild.id] = {r.id: r for r in rules}

        return [r.to_dict() for r in rules]


async def setup(bot: Plyoox):
    await bot.add_cog(AutomodCache(bot))
