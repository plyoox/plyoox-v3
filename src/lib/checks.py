from __future__ import annotations

from typing import TYPE_CHECKING

import discord

from lib.enums import PlyooxModule
from lib.errors import ModuleDisabled
from translation import _

if TYPE_CHECKING:
    from cache import CacheManager


async def module_enabled_check(interaction: discord.Interaction, module: PlyooxModule) -> bool:
    """Raise an error if the module is not enabled."""
    manager: CacheManager = interaction.client.cache  # type: ignore
    guild = interaction.guild
    lc = interaction.locale
    cache = None

    if module == PlyooxModule.Leveling:
        cache = await manager.get_leveling(guild.id)

    if not cache or not cache.active:
        raise ModuleDisabled(_(lc, "errors.module_disabled", module=str(module.name)))

    return True


def module_active(module: PlyooxModule):
    return discord.app_commands.check(lambda i: module_enabled_check(i, module))
