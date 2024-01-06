from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.app_commands import locale_str as _

from lib.enums import PlyooxModuleEnum
from lib.errors import ModuleDisabled

if TYPE_CHECKING:
    from cache import CacheManager


async def module_enabled_check(interaction: discord.Interaction, module: PlyooxModuleEnum) -> bool:
    """Raise an error if the module is not enabled."""
    manager: CacheManager = interaction.client.cache
    guild = interaction.guild
    cache = None

    if module == PlyooxModuleEnum.Leveling:
        cache = await manager.get_leveling(guild.id)

    if not cache:
        raise ModuleDisabled(interaction.translate(
            _("The module {module} is deactivated on this guild."), data={"module": str(module.name)})
        )

    return True


def module_active(module: PlyooxModuleEnum):
    return discord.app_commands.check(lambda i: module_enabled_check(i, module))
