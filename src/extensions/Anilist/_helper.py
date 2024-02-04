from __future__ import annotations

from typing import Literal, TYPE_CHECKING

import discord
from discord.app_commands import locale_str as _

from lib import extensions, errors
from . import queries

if TYPE_CHECKING:
    from main import Plyoox
    from . import _views
    from lib.types.anilist import _AnilistTitle, AnilistSearchResponse, AnilistDetailedResponse
    from lib.types import Translate


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
        .replace("<b>", "**")
        .replace("</b>", "**")
        .replace("<strong>", "**")
        .replace("</strong>", "**")
    )

    if len(description) > 1024:
        return description[:1021] + "..."

    return description


def generate_search_embed(
    translate,
    *,
    query: str,
    data: list[AnilistSearchResponse],
    title: Literal["romaji", "english", "native"],
) -> discord.Embed:
    """Generates an embed from Anilist data"""
    embed = extensions.Embed(title=translate(_("Results for {query}")).format(query=query))

    for item in data:
        embed.add_field(name=get_title(item["title"], title), value=to_description(item["description"]))

        if len(embed) > 6000:
            embed.remove_field(-1)
            return embed

    return embed


async def paginate_search(interaction: discord.Interaction, view: _views.AnilistSearchView) -> None:
    translate = interaction.translate

    bot: Plyoox = interaction.client
    await interaction.response.defer()

    try:
        data = await bot.anilist._fetch_query(query=queries.SEARCH_QUERY, page=view.current_page, search=view.query)
    except errors.AnilistQueryError as e:
        embed = extensions.Embed(title=translate(_("Anilist API Error")), description=str(e), color=discord.Color.red())

        await interaction.followup.send(embed=embed, ephemeral=True)
        return

    if not data:
        await interaction.followup.send(translate(_("No results found.")), ephemeral=True)
        return

    embed = generate_search_embed(
        translate,
        query=view.query,
        data=data["media"],
        title=view.title_language,  # type: ignore
    )
    view._update_buttons(has_next_page=data["pageInfo"]["hasNextPage"])

    await interaction.edit_original_response(embed=embed, view=view)


def generate_info_embed(data: AnilistDetailedResponse, translate: Translate) -> discord.Embed:
    title = data["title"]["romaji"]
    if data["title"]["english"]:
        title += f" ({data['title']['english']})"

    embed = extensions.Embed(color=discord.Color.from_str(data["coverImage"]["color"]))
    embed.set_author(name=title, url=data["siteUrl"])
    embed.set_thumbnail(url=data["coverImage"]["large"])
    embed.set_image(url=data["bannerImage"])

    embed.description = f"__**{translate(_('Information'))}**__\n"
    embed.description += f"**{translate(_('Status'))}:** {data['status']}\n"
    embed.description += (
        f"**{translate(_('Episodes'))}:** {data['episodes']} ({data['duration']} {translate(_('minutes'))})\n"
    )
    embed.description += f"**{translate(_('Season'))}:** {data['season']}\n"
    embed.description += f"**{translate(_('Year'))}:** {data['seasonYear']}\n"
    embed.description += f"**{translate(_('Country'))}:** {data['countryOfOrigin']}\n"
    embed.description += f"**{translate(_('Score'))}:** {data['averageScore']}/100\n"

    embed.add_field(name=translate(_("Description")), value=to_description(data["description"]))

    if data["genres"]:
        embed.add_field(name=translate(_("Genres")), value=", ".join(data["genres"]))

    if data["relations"]["nodes"]:
        embed.add_field(
            name=translate(_("Related to")),
            value=", ".join(f"[{ep['title']['romaji']}]({ep['siteUrl']})" for ep in data["relations"]["nodes"]),
        )

    return embed
