from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

import aiohttp
import discord
from discord import ui
from discord.app_commands import locale_str as _

from lib import emojis, types, extensions
from . import _helper

if TYPE_CHECKING:
    from main import Plyoox


_log = logging.getLogger(__name__)


class SiteBackButton(ui.Button):
    def __init__(self, view: AnilistSearchView, disabled: bool = False):
        translate = view._last_interaction.translate

        super().__init__(
            label=translate(_("Previous page")),
            style=discord.ButtonStyle.green,
            emoji=emojis.chevron_left,
            disabled=disabled,
        )

        self.search_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.search_view.current_page -= 1
        await _helper.paginate_search(interaction, self.search_view)


class SiteNextButton(ui.Button):
    def __init__(self, view: AnilistSearchView, disabled: bool = False):
        translate = view._last_interaction.translate

        super().__init__(
            label=translate(_("Next page")),
            style=discord.ButtonStyle.green,
            emoji=emojis.chevron_right,
            disabled=disabled,
        )

        self.search_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        self.search_view.current_page += 1
        await _helper.paginate_search(interaction, self.search_view)


class AnilistSearchView(extensions.PrivateView):
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
    def __init__(self, view: AnilistInfoView):
        translate = view._last_interaction.translate

        super().__init__(
            label=translate(_("Back")),
            style=discord.ButtonStyle.gray,
            emoji=emojis.chevron_left,
        )

        self.anilist_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.edit_original_response(
            embed=_helper.generate_info_embed(self.anilist_view.data, interaction.locale),
            view=self.anilist_view,
            attachments=[],
        )


class BackButtonView(extensions.PrivateView):
    def __init__(self, view: AnilistInfoView, *, interaction: discord.Interaction):
        super().__init__(original_interaction=interaction)

        self.add_item(BackButton(view, locale=interaction.locale))


class ViewScoreButton(ui.Button):
    def __init__(self, view: AnilistInfoView, *, locale: discord.Locale):
        translate = view._last_interaction.translate

        super().__init__(style=discord.ButtonStyle.gray, label=translate(_("Show rating")), emoji=emojis.chart_bar)

        self.anilist_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        bot: Plyoox = interaction.client  # type: ignore

        await interaction.response.defer()

        params = {"ratings": ",".join(str(_r["amount"]) for _r in self.anilist_view.data["stats"]["scoreDistribution"])}

        try:
            async with bot.session.get(f"{bot.imager_url}/api/anilist-rating", params=params) as res:
                if res.status != 200:
                    text = await res.text()
                    _log.warning(f"Received status code {res.status} and data `{text}` while fetching anilist rating.")

                    await interaction.followup.send(
                        interaction.translate(_("The required infrastructure is currently not available.")),
                        ephemeral=True,
                    )
                    return

                fp = io.BytesIO(await res.read())
                image = discord.File(fp, filename="anilist_score.png")
        except aiohttp.ClientConnectionError as err:
            _log.error("Could not fetch anilist score", err)

            await interaction.followup.send(
                interaction.translate(_("The required infrastructure is currently not available.")),
                ephemeral=True,
            )
            return

        embed = extensions.Embed(
            title=interaction.translate(_("Rating Statistics for {title}")).format(
                title=self.anilist_view.data["title"]["romaji"]
            ),
            description=interaction.translate(_("Rating")),
        )
        embed.set_image(url="attachment://anilist_score.png")

        await interaction.edit_original_response(
            attachments=[image], embed=embed, view=BackButtonView(self.anilist_view, interaction=interaction)
        )


class ViewTrailerButton(ui.Button):
    def __init__(self, view: AnilistInfoView, locale: discord.Locale):
        data = view.data
        translate = view._last_interaction.translate

        super().__init__(
            emoji=emojis.link, url=f"https://youtu.be/{data['trailer']['id']}", label=translate(_("View trailer"))
        )


class AnilistInfoView(extensions.PrivateView):
    def __init__(self, data: types.AnilistDetailedResponse, interaction: discord.Interaction):
        super().__init__(original_interaction=interaction)

        self.data = data

        self.add_item(ViewScoreButton(self, locale=interaction.locale))
        if data["trailer"]["site"] == "youtube":
            self.add_item(ViewTrailerButton(self, interaction.locale))
