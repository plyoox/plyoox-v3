from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import ui

from lib import emojis, types
from lib.extensions import Embed, PrivateView
from translation import _
from . import _helper

if TYPE_CHECKING:
    from main import Plyoox


class BackButton(ui.Button):
    def __init__(self, view: AnilistInfoView, *, locale: discord.Locale):
        super().__init__(
            label=_(locale, "back"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.chevron_left,
        )

        self.anilist_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.edit_original_message(
            embed=_helper.generate_info_embed(self.anilist_view.data, interaction.locale),
            view=self.anilist_view,
            attachments=[],
        )


class BackButtonView(PrivateView):
    def __init__(self, view: AnilistInfoView, *, interaction: discord.Interaction):
        super().__init__(original_interaction=interaction)

        self.add_item(BackButton(view, locale=interaction.locale))


class ViewScoreButton(ui.Button):
    def __init__(self, view: AnilistInfoView, *, locale: discord.Locale):
        super().__init__(
            style=discord.ButtonStyle.gray, label=_(locale, "anilist.view.score_button"), emoji=emojis.chart_bar
        )

        self.anilist_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        bot: Plyoox = interaction.client  # type: ignore

        await interaction.response.defer()

        image = await bot.loop.run_in_executor(
            None, _helper.generate_score_image, self.anilist_view.data["stats"]["scoreDistribution"]
        )

        embed = Embed(
            title=_(interaction.locale, "anilist.view.score_title", title=self.anilist_view.data["title"]["romaji"])
        )
        embed.set_image(url="attachment://anilist_score.png")

        await interaction.edit_original_message(
            attachments=[image], embed=embed, view=BackButtonView(self.anilist_view, interaction=interaction)
        )


class AnilistInfoView(PrivateView):
    def __init__(self, data: types.AnilistDetailedResponse, interaction: discord.Interaction):
        super().__init__(original_interaction=interaction)

        self.data = data

        self.add_item(ViewScoreButton(self, locale=interaction.locale))
