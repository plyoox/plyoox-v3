from __future__ import annotations

from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

if TYPE_CHECKING:
    import datetime
    from typing import TypedDict, Union

    from main import Plyoox

    class CommandStatistic(TypedDict):
        name: str
        guild_id: int
        author_id: int
        used_at: datetime.datetime
        failed: bool


class Statistics(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._command_statistics: list[CommandStatistic] = []
        self._insert_command_statistics.start()

    # statistics_group = commands.Group(
    #     name="stats", description="Basic stats about the Bot command usage.", guild_only=True, auto_locale_strings=False
    # )

    async def cog_unload(self) -> None:
        self._insert_command_statistics.stop()

    @tasks.loop(seconds=60)
    async def _insert_command_statistics(self):
        if not self._command_statistics:
            return

        values = list(
            map(
                lambda s: (s["name"], s["guild_id"], s["author_id"], s["failed"], s["used_at"]),
                self._command_statistics,
            )
        )

        self._command_statistics.clear()

        await self.bot.db.executemany(
            "INSERT INTO command_statistics (name, guild_id, author_id, failed, used_at) VALUES ($1, $2, $3, $4, $5)",
            values,
        )

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.reply(f"```py\n{error}```")

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, interaction: discord.Interaction, command: Union[app_commands.Command, app_commands.ContextMenu]
    ):
        statistics: CommandStatistic = {
            "name": command.name,
            "guild_id": interaction.guild_id,  # type: ignore
            "used_at": discord.utils.utcnow(),
            "author_id": interaction.user.id,
            "failed": interaction.command_failed,
        }

        self._command_statistics.append(statistics)

    @commands.group(name="stats")
    @commands.is_owner()
    async def stats(self, ctx: commands.Context):
        pass

    @stats.command(name="all")
    @commands.is_owner()
    async def stats_all(self, ctx: commands.Context, days: Optional[int]):
        if days is None:
            command_stats: list = await self.bot.db.fetch(
                "SELECT name, count(*) as usage FROM command_statistics GROUP BY name ORDER BY usage DESC"
            )
        else:
            command_stats: list = await self.bot.db.fetch(
                "SELECT name, count(*) as usage FROM command_statistics WHERE "
                f"used_at > (CURRENT_TIMESTAMP - INTERVAL '{days} days') GROUP BY name ORDER BY usage DESC",
            )

        embed = discord.Embed(title="Command stats", description="")

        for stat in command_stats:
            embed.description += f"{stat['name']}: {stat['usage']}\n"

            if len(embed.description) >= 4000:
                break

        if not embed.description:
            embed.description = "No commands executed."

        await ctx.reply(embed=embed)

    @stats.command(name="guild")
    @commands.is_owner()
    async def statistics_guild(self, ctx: commands.Context, days: Optional[int]):
        if days is None:
            command_stats: list = await self.bot.db.fetch(
                "SELECT name, count(*) as usage FROM command_statistics WHERE guild_id = $1 GROUP BY name ORDER BY usage DESC",
                ctx.guild.id,
            )
        else:
            command_stats: list = await self.bot.db.fetch(
                "SELECT name, count(*) as usage FROM command_statistics WHERE guild_id = $1 AND used_at"
                f" > (CURRENT_TIMESTAMP - INTERVAL '{days} days') GROUP BY name ORDER BY usage DESC",
                ctx.guild.id,
            )

        embed = discord.Embed(title="Command stats", description="")

        for stat in command_stats:
            embed.description += f"{stat['name']}: {stat['usage']}\n"

            if len(embed.description) >= 4000:
                break

        if not embed.description:
            embed.description = "No commands executed."

        await ctx.reply(embed=embed)


async def setup(bot: Plyoox):
    await bot.add_cog(Statistics(bot))
