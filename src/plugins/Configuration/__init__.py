from __future__ import annotations

from typing import TYPE_CHECKING

from .cog import Configuration

if TYPE_CHECKING:
    from main import Plyoox


async def setup(bot: Plyoox):
    await bot.add_cog(Configuration(bot))
