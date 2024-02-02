from __future__ import annotations

import io
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands, tasks

if TYPE_CHECKING:
    import datetime
    from typing import TypedDict, Union, NotRequired

    from main import Plyoox

    class CommandStatistic(TypedDict):
        command: str
        guild_id: int
        user_id: int
        executed_at: datetime.datetime
        usage: NotRequired[int]


class Statistics(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot
        self._command_statistics: list[CommandStatistic] = []
        self._insert_command_statistics.start()

    async def cog_unload(self) -> None:
        self._insert_command_statistics.stop()

    @tasks.loop(seconds=60)
    async def _insert_command_statistics(self):
        def map_values(val: CommandStatistic) -> tuple:
            return val["command"], val["guild_id"], val["user_id"], val["executed_at"]

        if not self._command_statistics:
            return

        values = list(map(map_values, self._command_statistics))

        self._command_statistics.clear()

        await self.bot.db.executemany(
            "INSERT INTO command_statistics (command, guild_id, user_id, executed_at) VALUES ($1, $2, $3, $4)",
            values,
        )

    @commands.Cog.listener()
    async def on_app_command_completion(
        self, interaction: discord.Interaction, command: Union[app_commands.Command, app_commands.ContextMenu]
    ):
        statistics: CommandStatistic = {
            "command": command.qualified_name,
            "guild_id": interaction.guild_id,  # type: ignore
            "executed_at": discord.utils.utcnow().replace(tzinfo=None),
            "user_id": interaction.user.id,
        }

        print(statistics)

        self._command_statistics.append(statistics)

    @commands.group(name="stats")
    @commands.is_owner()
    async def stats(self, ctx: commands.Context):
        pass

    @stats.command(name="all")
    @commands.is_owner()
    async def stats_all(self, ctx: commands.Context, days: int | None):
        if days is None:
            command_stats: list[CommandStatistic] = await self.bot.db.fetch(
                "SELECT command, count(*) as usage FROM command_statistics GROUP BY command ORDER BY usage DESC"
            )
        else:
            command_stats: list[CommandStatistic] = await self.bot.db.fetch(
                "SELECT name, count(*) as usage FROM command_statistics WHERE "
                f"used_at > (CURRENT_TIMESTAMP - INTERVAL '{days} days') GROUP BY name ORDER BY usage DESC",
            )

        embed = discord.Embed(title="Command stats", description="")

        for stat in command_stats:
            embed.description += f"{stat['command']}: {stat['usage']}\n"

            if len(embed.description) >= 4000:
                break

        if not embed.description:
            embed.description = "No commands executed."

        await ctx.reply(embed=embed)

    @stats.command(name="guild")
    @commands.is_owner()
    async def statistics_guild(self, ctx: commands.Context, days: int | None):
        if days is None:
            command_stats: list = await self.bot.db.fetch(
                "SELECT command, count(*) as usage FROM command_statistics WHERE guild_id = $1 GROUP BY command ORDER BY usage DESC",
                ctx.guild.id,
            )
        else:
            command_stats: list[CommandStatistic] = await self.bot.db.fetch(
                "SELECT name, count(*) as usage FROM command_statistics WHERE guild_id = $1 AND used_at"
                f" > (CURRENT_TIMESTAMP - INTERVAL '{days} days') GROUP BY name ORDER BY usage DESC",
                ctx.guild.id,
            )

        embed = discord.Embed(title="Command stats", description="")

        for stat in command_stats:
            embed.description += f"{stat['command']}: {stat['usage']}\n"

            if len(embed.description) >= 4000:
                break

        if not embed.description:
            embed.description = "No commands executed."

        await ctx.reply(embed=embed)

    @commands.command(name="servers")
    @commands.is_owner()
    async def servers(self, ctx: commands.Context):
        count = 0
        msg = "Count,Id,Members,Bots,Name,Owner,Chunked\n"

        guilds = [guild for guild in self.bot.guilds]
        guilds.sort(key=lambda g: g.member_count, reverse=True)

        for guild in guilds:
            bots = len([m.bot for m in guild.members if m.bot])
            count += 1
            msg += f"{count},{guild.id},{guild.member_count}s,{bots},{guild.name},{guild.owner},{guild.chunked}\n"

        data = io.BytesIO(msg.encode())
        file = discord.File(data, filename="guilds.csv")

        await ctx.reply(file=file)


async def setup(bot: Plyoox):
    await bot.add_cog(Statistics(bot))
