from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

import aiolimiter
import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import locale_str as _

from lib import errors
from . import queries, _views, _helper

if TYPE_CHECKING:
    from main import Plyoox


@app_commands.guild_only
class Anilist(commands.GroupCog, group_name="anilist", group_description=_("Commands for querying the Anilist site.")):
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
                    await self.bot.loop.create_task(self.__reset_limit(int(retry_after)))
                    raise errors.AnilistQueryError("Rate limit exceeded")

                if resp.status != 200:
                    raise errors.AnilistQueryError(f"Anilist returned status code {resp.status}")

                data = await resp.json()

                return data["data"]["Page"]

    @app_commands.command(name="search", description=_("Search for an anime on Anilist."))
    @app_commands.describe(
        query=_("The query to search for."),
        title=_("In which language the titles should be displayed (default original)."),
    )
    async def search_anilist(
        self,
        interaction: discord.Interaction,
        query: app_commands.Range[str, 3, 50],
        title: Literal["Romaji", "Native", "English"] = "Romaji",
    ):
        if not self.limiter.has_capacity() and not self.limit_lock:
            await interaction.response.send_translated(
                _("The limit of the API has been reached. Please try again later.")
            )
            return

        await interaction.response.defer()
        response = await self._fetch_query(queries.SEARCH_QUERY, query)
        data = response["media"]

        if not data:
            await interaction.followup.send(interaction.translate(_("No results found.")), ephemeral=True)
            return

        view = _views.AnilistSearchView(interaction, query, title.lower())
        view._update_buttons(has_next_page=response["pageInfo"]["hasNextPage"])

        await interaction.followup.send(
            view=view,
            embed=_helper.generate_search_embed(
                interaction.translate,
                query=query,
                data=data,
                title=title.lower(),  # type: ignore
            ),
        )

    @app_commands.command(name="info", description=_("Get information about an anime on Anilist."))
    @app_commands.describe(query=_("The query to search for."))
    async def info_anilist(self, interaction: discord.Interaction, query: str):
        if not self.limiter.has_capacity() and not self.limit_lock:
            await interaction.response.send_translated(
                _("The limit of the API has been reached. Please try again later.")
            )
            return

        await interaction.response.defer()
        response = await self._fetch_query(queries.INFO_QUERY, query)
        data = response["media"]

        if not data:
            await interaction.followup.send(interaction.translate(_("No results found.")), ephemeral=True)
            return

        embed = _helper.generate_info_embed(data=data[0], translate=interaction.translate)

        if data[0]["trailer"] is not None:
            view = _views.AnilistInfoView(data[0], interaction)
        else:
            view = discord.utils.MISSING

        await interaction.followup.send(embed=embed, view=view)
