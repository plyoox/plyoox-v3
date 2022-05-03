from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from lib import errors
from lib.types import enums

if TYPE_CHECKING:
    from src.main import Plyoox


def owner_only_check(interaction: discord.Interaction) -> bool:
    bot: Plyoox = interaction.client  # type: ignore

    if interaction.user.id == bot.owner_id:
        return True

    raise errors.OwnerOnly


# https://github.com/Rapptz/discord.py/blob/master/discord/app_commands/checks.py#L344
def bot_permission_check(interaction: discord.Interaction, **perms: bool) -> bool:
    guild = interaction.guild
    me = guild.me

    permissions = interaction.channel.permissions_for(me)
    missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

    if not missing:
        return True

    raise app_commands.BotMissingPermissions(missing)


def module_active(module: enums.PlyooxModule):
    async def predicate(interaction: discord.Interaction) -> bool:
        bot: Plyoox = interaction.client  # type: ignore
        cache = bot.cache
        guild = interaction.guild

        if module == enums.PlyooxModule.Leveling:
            cache = await cache.get_leveling(guild.id)
            return cache.active


def owner_only():
    return discord.app_commands.check(owner_only_check)
