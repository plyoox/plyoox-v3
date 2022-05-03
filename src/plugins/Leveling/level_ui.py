from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import ui

from translation import _
from utils import colors

if TYPE_CHECKING:
    from main import Plyoox


# maybe use this in the future
class ConfirmLevelReset(ui.Modal):
    def __init__(self, *, member: discord.Member, locale: discord.Locale):
        self.title = _(locale, "level.reset_level.modal_title", member=member.name)
        self.member_id = member.id

        super().__init__()

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot: Plyoox = interaction.client  # type: ignore
        lc = interaction.locale

        await bot.db.execute(
            "DELETE FROM leveling_users WHERE user_id = $1 AND guild_id = $2", self.member_id, interaction.guild.id
        )

        embed = discord.Embed(color=colors.DISCORD_DEFAULT, description=_(lc, "level.reset_level.level_reset"))
        await interaction.response.send_message(embed=embed, ephemeral=True)
