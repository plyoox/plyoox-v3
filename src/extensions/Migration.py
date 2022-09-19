from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from lru import LRU

from lib import extensions
from translation import _

if TYPE_CHECKING:
    from main import Plyoox


OLD_COMMANDS = [
    "help",
    "level",
    "top",
    "info",
    "server",
    "todayjoined",
    "invite",
    "ban",
    "kick",
    "mute",
    "tempmute",
    "resetlevel",
    "avatar",
    "members",
    "unban",
    "unmute",
    "clear",
    "slot",
    "joined",
    "check",
    "resetpoints",
    "check",
    "softban",
    "points",
    "warn",
    "highfive",
    "minesweeper",
    "tempban",
]


class Migration(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

        self.migration_guilds = LRU(size=512)
        self.migration_command_id = None

    async def _get_migration_command_mention(self):
        """Returns the command mention for the migration command. If not set, the id is fetched."""
        if self.migration_command_id is None:
            bot_commands = await self.bot.tree.fetch_commands()
            for cmd in bot_commands:
                if cmd.name == "disable-migration-notification":
                    self.migration_command_id = cmd.id
                    break

        return f"</disable-migration-notification:{self.migration_command_id}>"

    async def _get_guild_status(self, id: int) -> bool:
        """Returns the status for the migration message"""
        if self.migration_guilds.has_key(id):
            return self.migration_guilds[id]

        migration_status = await self.bot.db.fetchval("SELECT slash_migration FROM guild_config WHERE id = $1", id)
        self.migration_guilds[id] = migration_status if migration_status is not None else True

        return self.migration_guilds[id]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.content.startswith("+"):
            if not message.channel.permissions_for(message.guild.me).send_messages:
                return

            if not await self._get_guild_status(message.guild.id):
                return

            command = message.content.split(" ")[0][1:]

            if command in OLD_COMMANDS:
                command_mention = await self._get_migration_command_mention()
                embed = extensions.Embed(
                    title="New Slash Commands",
                    description="**Plyoox now supports Slash Commands!**\n\n"
                    "Slash Commands can be viewed by typing `/` (A list of commands should pop up). "
                    "*You can read more about app commands [here](https://discord.com/blog/welcome-to-the-new-era-of-discord-apps)*.\n\n"
                    "If no commands show up, just invite the bot a again, no need to remove. "
                    f"Invite by clicking [here](https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions=274945403966).\n\n"
                    f"*You can disable this message by using {command_mention}.*",
                )

                await message.channel.send(embed=embed)

    @app_commands.command(
        name="disable-migration-notification", description="Disables the Migration-Messages when using a command."
    )
    async def disable_migration_notification(self, integration: discord.Interaction):
        await self.bot.db.execute(
            "INSERT INTO guild_config VALUES ($1, False) ON CONFLICT (id) DO UPDATE SET slash_migration = FALSE",
            integration.guild_id,
        )

        self.migration_guilds[integration.guild_id] = False

        await integration.response.send_message(
            _(integration.locale, "disable-migration-notification.successfully_disabled"), ephemeral=True
        )


async def setup(bot: Plyoox):
    await bot.add_cog(Migration(bot))
