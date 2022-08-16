from __future__ import annotations

from typing import TYPE_CHECKING

from .anilist_cog import Anilist

if TYPE_CHECKING:
    from main import Plyoox


async def setup(bot: Plyoox) -> None:
    await bot.add_cog(Anilist(bot))
