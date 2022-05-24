from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands

from lib.enums import PlyooxModule
from lib.errors import ModuleDisabled, OwnerOnly
from translation import _

if TYPE_CHECKING:
    from main import Plyoox
    from cache import CacheManager


def owner_only_check(interaction: discord.Interaction) -> bool:
    bot: Plyoox = interaction.client  # type: ignore

    if interaction.user.id == bot.owner_id:
        return True

    raise OwnerOnly


# https://github.com/Rapptz/discord.py/blob/master/discord/app_commands/checks.py#L344
def bot_permission_check(interaction: discord.Interaction, **perms: bool) -> bool:
    guild = interaction.guild
    me = guild.me

    permissions = interaction.channel.permissions_for(me)
    missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

    if not missing:
        return True

    raise app_commands.BotMissingPermissions(missing)


async def module_enabled_check(interaction: discord.Interaction, module: PlyooxModule) -> bool:
    manager: CacheManager = interaction.client.cache  # type: ignore
    guild = interaction.guild
    lc = interaction.locale

    if module == PlyooxModule.Leveling:
        cache = await manager.get_leveling(guild.id)
        if not cache or not cache.active:
            raise ModuleDisabled(_(lc, "errors.module_disabled", module=str(module.name)))

        return True


def module_active(module: PlyooxModule):
    return discord.app_commands.check(lambda i: module_enabled_check(i, module))


def owner_only():
    return discord.app_commands.check(owner_only_check)
