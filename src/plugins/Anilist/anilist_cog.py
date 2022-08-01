from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

import aiolimiter
import discord
from discord import app_commands
from discord.ext import commands

from lib.errors import AnilistQueryError
from translation import _
from . import queries, _views, _helper

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
            embed=_helper.generate_search_embed(
                query=query,
                data=data,
                interaction=interaction,
                title=title.lower(),  # type: ignore  # This is a bug in pycharm type checker
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

        embed = _helper.generate_info_embed(lc=interaction.locale, data=data[0])

        await interaction.followup.send(embed=embed, view=_views.AnilistInfoView(data[0], interaction))
