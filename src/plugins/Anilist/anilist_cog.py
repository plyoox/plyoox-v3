from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

import aiolimiter
import discord
from discord import app_commands
from discord.ext import commands

from lib import errors
from translation import _
from . import queries, _views, _helper

if TYPE_CHECKING:
    from main import Plyoox


_T = app_commands.locale_str


@app_commands.guild_only
class Anilist(
    commands.GroupCog,
    group_name=_T("anilist", key="anilist.name"),
    group_description=_T("Commands for querying the Anilist site.", key="anilist.description"),
):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self.url = "https://graphql.anilist.co"
        self.limiter = aiolimiter.AsyncLimiter(88, 60)
        self.limit_lock = False

    async def __reset_limit(self, seconds: float):
        await asyncio.sleep(seconds)
        self.limit_lock = False

    async def _fetch_query(self, query: str, search: str, page: int = 1) -> dict:
        """Fetches data from Anilist"""

        async with self.limiter:
            variables = {"sort": "POPULARITY_DESC", "type": "ANIME", "search": search, "page": page}
            data = {"query": query, "variables": variables}

            async with self.bot.session.post(self.url, json=data) as resp:
                if retry_after := resp.headers.get("Retry-After"):
                    self.limit_lock = True
                    self.bot.loop.create_task(self.__reset_limit(int(retry_after)))
                    raise errors.AnilistQueryError("Rate limit exceeded")

                if resp.status != 200:
                    raise errors.AnilistQueryError(f"Anilist returned status code {resp.status}")

                data = await resp.json()

                return data["data"]["Page"]

    @app_commands.command(
        name=_T("search", key="anilist.search.name"),
        description=_T("Search for an anime on Anilist.", key="anilist.search.description"),
    )
    @app_commands.describe(
        query=_T("The query to search for.", key="anilist.search.query"),
        title=_T("If which language the titles should be shown (default original).", key="anilist.search.title"),
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
        response = await self._fetch_query(queries.SEARCH_QUERY, query)
        data = response["media"]

        if not data:
            await interaction.followup.send(_(interaction.locale, "anilist.search.no_result"), ephemeral=True)
            return

        view = _views.AnilistSearchView(interaction, query, title.lower())
        view._update_buttons(has_next_page=response["pageInfo"]["hasNextPage"])

        await interaction.followup.send(
            view=view,
            embed=_helper.generate_search_embed(
                query=query,
                data=data,
                locale=interaction.locale,
                title=title.lower(),  # type: ignore
            ),
        )

    @app_commands.command(
        name=_T("info", key="anilist.info.title"),
        description=_T("Get information about an anime on Anilist.", key="anilist.info.description"),
    )
    @app_commands.describe(query=_T("The query to search for.", key="anilist.search.query"))
    async def info_anilist(self, interaction: discord.Interaction, query: str):
        if not self.limiter.has_capacity() and not self.limit_lock:
            await interaction.response.send(_(interaction.locale, "anilist.rate_limit"))
            return

        await interaction.response.defer()
        response = await self._fetch_query(queries.INFO_QUERY, query)
        data = response["media"]

        if not data:
            await interaction.followup.send(_(interaction.locale, "anilist.search.no_result"))
            return

        embed = _helper.generate_info_embed(lc=interaction.locale, data=data[0])

        await interaction.followup.send(embed=embed, view=_views.AnilistInfoView(data[0], interaction))
