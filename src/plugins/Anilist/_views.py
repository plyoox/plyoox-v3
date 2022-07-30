from __future__ import annotations

import io
from typing import TYPE_CHECKING

import discord
from PIL import Image
from discord import ui
from easy_pil import Font, Editor

from lib import emojis, types
from lib.extensions import Embed
from translation import _

if TYPE_CHECKING:
    from main import Plyoox

POPPINS_md = Font.poppins(size=18)
POPPINS_xs = Font.poppins(size=14)

SCORE_COLORS = {
    10: "#d2482d",
    20: "#d2642d",
    30: "#d2802d",
    40: "#d29b2d",
    50: "#d2b72d",
    60: "#d2d22d",
    70: "#b7d22d",
    80: "#9bd22d",
    90: "#80d22d",
    100: "#64d22d",
}

TEXT_POSITIONS = {10: 29.5, 20: 78, 30: 126, 40: 178, 50: 228, 60: 277, 70: 328, 80: 378, 90: 427, 100: 475}


def _get_text_offset_multiplier(length: int) -> float:
    if length < 4:
        return 1
    elif length == 5:
        return 1.5
    else:
        return 2


def _generate_score_image(scores: list[types.AnilistScore]) -> discord.File:
    bg_image = Image.new("RGB", (525, 200), "#18181b")
    background = Editor(bg_image)

    score_amount = sum(score["amount"] for score in scores)

    index = 0
    for score in scores:
        background.rectangle(
            (25 + 50 * index, 175),
            color=SCORE_COLORS[score["score"]],
            width=25,
            height=-170 * score["amount"] / score_amount,
        )
        background.text(
            (TEXT_POSITIONS[score["score"]], 180), text=str(score["score"]), font=POPPINS_md, color="#ffffff"
        )

        score_len = len(str(score["amount"]))

        background.text(
            (
                TEXT_POSITIONS[score["score"]] - score_len * _get_text_offset_multiplier(score_len),
                200 + -170 * (score["amount"] / score_amount) - 45,
            ),
            text=str(score["amount"]),
            font=POPPINS_xs,
            color="#ffffff",
        )
        index += 1

    image_file = io.BytesIO()
    background.save(image_file, format="PNG")  # type: ignore
    image_file.seek(0)

    return discord.File(image_file, filename="anilist_score.png")


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
        await interaction.edit_original_message(embed=self.anilist_view.data_embed, view=self.anilist_view)


class BackButtonView(ui.View):
    def __init__(self, view: AnilistInfoView, *, locale: discord.Locale):
        super().__init__()

        self.add_item(BackButton(view, locale=locale))


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
            None, _generate_score_image, self.anilist_view.data["stats"]["scoreDistribution"]
        )

        embed = Embed(title=_(interaction.locale, "anilist.view.score_title"))
        embed.set_image(url="attachment://anilist_score.png")

        await interaction.edit_original_message(
            attachments=[image], embed=embed, view=BackButtonView(self.anilist_view, locale=interaction.locale)
        )


class AnilistInfoView(ui.View):
    def __init__(self, data: types.AnilistDetailedResponse, data_embed: Embed, locale: discord.Locale):
        super().__init__()

        self.data = data
        self.data_embed = data_embed

        self.add_item(ViewScoreButton(self, locale=locale))
