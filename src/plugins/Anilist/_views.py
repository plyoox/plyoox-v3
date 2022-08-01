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


class SiteBackButton(ui.Button):
    def __init__(self, view: AnilistSearchView, locale: discord.Locale, disabled: bool = False):
        super().__init__(
            label=_(locale, "previous_site"),
            style=discord.ButtonStyle.green,
            emoji=emojis.chevron_left,
            disabled=disabled,
        )

        self.search_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.search_view.current_page -= 1
        await _helper.paginate_search(interaction, self.search_view)


class SiteNextButton(ui.Button):
    def __init__(self, view: AnilistSearchView, locale: discord.Locale, disabled: bool = False):
        super().__init__(
            label=_(locale, "next_site"), style=discord.ButtonStyle.green, emoji=emojis.chevron_right, disabled=disabled
        )

        self.search_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.search_view.current_page += 1
        await _helper.paginate_search(interaction, self.search_view)


class AnilistSearchView(PrivateView):
    def __init__(self, interaction: discord.Interaction, query: str, title: str):
        super().__init__(interaction)

        self._back_button = SiteBackButton(self, interaction.locale, disabled=True)
        self._next_button = SiteNextButton(self, interaction.locale)

        self.current_page = 1
        self.add_item(self._back_button)
        self.add_item(self._next_button)
        self.query = query
        self.title_language = title

    def _update_buttons(self, *, has_next_page: bool):
        self._back_button.disabled = self.current_page <= 1
        self._next_button.disabled = not has_next_page


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
        lc = interaction.locale

        await interaction.response.defer()

        image = await bot.loop.run_in_executor(
            None, _helper.generate_score_image, self.anilist_view.data["stats"]["scoreDistribution"]
        )

        embed = Embed(
            title=_(lc, "anilist.view.score_title", title=self.anilist_view.data["title"]["romaji"]),
            description=f"{_(lc, 'anilist.score')}: {self.anilist_view.data['averageScore']}/100",
        )
        embed.set_image(url="attachment://anilist_score.png")

        await interaction.edit_original_message(
            attachments=[image], embed=embed, view=BackButtonView(self.anilist_view, interaction=interaction)
        )


class ViewTrailerButton(ui.Button):
    def __init__(self, view: AnilistInfoView, locale: discord.Locale):
        data = view.data

        super().__init__(
            emoji=emojis.link, url=f"https://youtu.be/{data['trailer']['id']}", label=_(locale, "anilist.info.trailer")
        )


class AnilistInfoView(PrivateView):
    def __init__(self, data: types.AnilistDetailedResponse, interaction: discord.Interaction):
        super().__init__(original_interaction=interaction)

        self.data = data

        self.add_item(ViewScoreButton(self, locale=interaction.locale))
        if data["trailer"]["site"] == "youtube":
            self.add_item(ViewTrailerButton(self, interaction.locale))
