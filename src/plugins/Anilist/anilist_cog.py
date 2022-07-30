from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

import aiolimiter
import discord
from discord import app_commands
from discord.ext import commands

from lib.errors import AnilistQueryError
from lib.extensions import Embed
from lib.types.anilist import AnilistSearchResponse, _AnilistTitle, AnilistDetailedResponse
from translation import _
from . import queries, _views

if TYPE_CHECKING:
    from main import Plyoox


@app_commands.guild_only
class Anilist(commands.GroupCog, group_name="anilist", group_description="Commands for querying the Anilist site."):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self.url = "https://graphql.anilist.co"
        self.limiter = aiolimiter.AsyncLimiter(88, 60)
        self.limit_lock = False

    async def __reset_limit(self, seconds: float):
        await asyncio.sleep(seconds)
        self.limit_lock = False

    @staticmethod
    def __get_title(title: _AnilistTitle, language: Literal["romaji", "english", "native"]) -> str:
        """Returns the title of an Anilist title"""
        return title[language] if title[language] else title["romaji"]

    @staticmethod
    def __to_description(description: str):
        """Converts Anilist's description to a discord-usable description"""
        description = description.replace("<br>", "").replace("<i>", "*").replace("</i>", "*")

        if len(description) > 1024:
            return description[:1021] + "..."

        return description

    async def _fetch_query(self, query: str, search: str) -> list:
        """Fetches data from Anilist"""

        async with self.limiter:
            variables = {"sort": "POPULARITY_DESC", "type": "ANIME", "search": search}
            data = {"query": query, "variables": variables}

            async with self.bot.session.post(self.url, json=data) as resp:
                if retry_after := resp.headers.get("Retry-After"):
                    self.limit_lock = True
                    self.bot.loop.create_task(self.__reset_limit(int(retry_after)))
                    raise AnilistQueryError("Rate limit exceeded")

                if resp.status != 200:
                    raise AnilistQueryError(f"Anilist returned status code {resp.status}")

                data = await resp.json()

                return data["data"]["Page"]["media"]

    def _generate_search_embed(
        self,
        *,
        query: str,
        data: list[AnilistSearchResponse],
        interaction: discord.Interaction,
        title: Literal["romaji", "english", "native"],
    ) -> discord.Embed | None:
        """Generates an embed from Anilist data"""
        lc = interaction.locale
        embed = Embed(title=_(lc, "anilist.search.title", query=query))

        for item in data:
            embed.add_field(
                name=self.__get_title(item["title"], title), value=self.__to_description(item["description"])
            )

            if len(embed) > 6000:
                embed.remove_field(-1)
                return embed

        return embed

    def _generate_info_embed(self, *, interaction: discord.Interaction, data: AnilistDetailedResponse):
        lc = interaction.locale

        title = data["title"]["romaji"]
        if data["title"]["english"]:
            title += f" ({data['title']['english']})"

        embed = Embed(color=discord.Color.from_str(data["coverImage"]["color"]))
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
        embed.description += f"**{_(lc, 'anilist.info.score')}:** {data['averageScore']}/100\n"

        embed.add_field(name=_(lc, "anilist.info.description"), value=self.__to_description(data["description"]))

        if data["genres"]:
            embed.add_field(name=_(lc, "anilist.info.genres"), value=", ".join(data["genres"]))

        if data["trailer"]["site"] == "youtube":
            embed.add_field(
                name=_(lc, "anilist.info.trailer"),
                value=f"[youtu.be/{data['trailer']['id']}](https://youtu.be/{data['trailer']['id']})",
            )

        if data["relations"]["nodes"]:
            embed.add_field(
                name=_(lc, "anilist.info.relations"),
                value=", ".join(f"[{ep['title']['romaji']}]({ep['siteUrl']})" for ep in data["relations"]["nodes"]),
            )

        return embed

    @app_commands.command(name="search", description="Search for an anime on Anilist.")
    @app_commands.describe(
        query="The query to search for.", title="If which language the titles should be shown (default original)."
    )
    async def search_anilist(
        self,
        interaction: discord.Interaction,
        query: app_commands.Range[str, 3, 50],
        title: Literal["Romaji", "Native", "English"] = "Romaji",
    ):
        if not self.limiter.has_capacity() and not self.limit_lock:
            await interaction.response.send(_(interaction.locale, "anilist.rate_limit"))
            return

        await interaction.response.defer()
        data = await self._fetch_query(queries.SEARCH_QUERY, query)

        if data is None:
            await interaction.followup.send(_(interaction.locale, "anilist.search.no_result"))
            return

        await interaction.followup.send(
            embed=self._generate_search_embed(
                query=query, data=data, interaction=interaction, title=title.lower()  # type: ignore
            )
        )

    @app_commands.command(name="info", description="Get information about an anime on Anilist.")
    @app_commands.describe(query="The query to search for.")
    async def info_anilist(self, interaction: discord.Interaction, query: str):
        if not self.limiter.has_capacity() and not self.limit_lock:
            await interaction.response.send(_(interaction.locale, "anilist.rate_limit"))
            return

        await interaction.response.defer()
        data = await self._fetch_query(queries.INFO_QUERY, query)

        if data is None:
            await interaction.followup.send(_(interaction.locale, "anilist.search.no_result"))
            return

        embed = self._generate_info_embed(interaction=interaction, data=data[0])

        await interaction.followup.send(embed=embed, view=_views.AnilistInfoView(data[0], embed, interaction.locale))
