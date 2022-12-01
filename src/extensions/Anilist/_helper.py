from __future__ import annotations

import logging
from typing import Literal, TYPE_CHECKING

import discord

from lib import extensions
from translation import _
from . import queries

if TYPE_CHECKING:
    from main import Plyoox
    from . import _views
    from lib.types.anilist import _AnilistTitle, AnilistSearchResponse, AnilistDetailedResponse

_log = logging.getLogger(__name__)

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


def get_title(title: _AnilistTitle, language: Literal["romaji", "english", "native"]) -> str:
    """Returns the title of an Anilist title"""
    return title[language] if title[language] else title["romaji"]


def to_description(description: str):
    """Converts Anilist's description to a discord-usable description"""
    description = (
        description.replace("<br>", "")
        .replace("<i>", "*")
        .replace("</i>", "*")
        .replace("<strong>", "**")
        .replace("</strong>", "**")
    )

    if len(description) > 1024:
        return description[:1021] + "..."

    return description


def generate_search_embed(
    *,
    query: str,
    data: list[AnilistSearchResponse],
    locale: discord.Locale,
    title: Literal["romaji", "english", "native"],
) -> discord.Embed:
    """Generates an embed from Anilist data"""
    embed = extensions.Embed(title=_(locale, "anilist.search.title", query=query))

    for item in data:
        embed.add_field(name=get_title(item["title"], title), value=to_description(item["description"]))

        if len(embed) > 6000:
            embed.remove_field(-1)
            return embed

    return embed


async def paginate_search(interaction: discord.Interaction, view: _views.AnilistSearchView) -> None:
    bot: Plyoox = interaction.client  # type: ignore
    if bot.anilist is None:
        await interaction.response.send_message(_(interaction.locale, "anilist.cog_not_loaded"))
        _log.warning("Anilist cog not loaded")
        return

    await interaction.response.defer()

    data = await bot.anilist._fetch_query(query=queries.SEARCH_QUERY, page=view.current_page, search=view.query)

    if not data:
        await interaction.followup.send(_(interaction.locale, "anilist.search.no_result"))
        return

    embed = generate_search_embed(
        query=view.query,
        data=data["media"],
        locale=interaction.locale,
        title=view.title_language,  # type: ignore
    )
    view._update_buttons(has_next_page=data["pageInfo"]["hasNextPage"])

    await interaction.edit_original_response(embed=embed, view=view)


def generate_info_embed(data: AnilistDetailedResponse, lc: discord.Locale) -> discord.Embed:
    title = data["title"]["romaji"]
    if data["title"]["english"]:
        title += f" ({data['title']['english']})"

    embed = extensions.Embed(color=discord.Color.from_str(data["coverImage"]["color"]))
    embed.set_author(name=title, url=data["siteUrl"])
    embed.set_thumbnail(url=data["coverImage"]["large"])
    embed.set_image(url=data["bannerImage"])

    embed.description = f"__**{_(lc, 'anilist.info.information')}**__\n"
    embed.description += f"**{_(lc, 'anilist.info.status')}:** {data['status']}\n"
    embed.description += (
        f"**{_(lc, 'anilist.info.episodes')}:** {data['episodes']} ({data['duration']} {_(lc, 'times.minutes')})\n"
    )
    embed.description += f"**{_(lc, 'anilist.info.season')}:** {data['season']}\n"
    embed.description += f"**{_(lc, 'anilist.info.year')}:** {data['seasonYear']}\n"
    embed.description += f"**{_(lc, 'anilist.info.country')}:** {data['countryOfOrigin']}\n"
    embed.description += f"**{_(lc, 'anilist.score')}:** {data['averageScore']}/100\n"

    embed.add_field(name=_(lc, "anilist.info.description"), value=to_description(data["description"]))

    if data["genres"]:
        embed.add_field(name=_(lc, "anilist.info.genres"), value=", ".join(data["genres"]))

    if data["relations"]["nodes"]:
        embed.add_field(
            name=_(lc, "anilist.info.relations"),
            value=", ".join(f"[{ep['title']['romaji']}]({ep['siteUrl']})" for ep in data["relations"]["nodes"]),
        )

    return embed
