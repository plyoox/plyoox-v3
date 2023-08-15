from __future__ import annotations

import contextlib
import importlib
import io
import json
import textwrap
import traceback
from typing import TYPE_CHECKING, Literal, Optional

import discord
from discord.ext import commands

from lib import extensions
from translation import languages

if TYPE_CHECKING:
    from main import Plyoox


class Owner(commands.Cog):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def cog_command_error(self, ctx: commands.Context, error):
        await ctx.send((str(error)))

    @commands.group(name="extension")
    @commands.is_owner()
    async def extension(self, ctx: commands.Context):
        pass

    @extension.command(name="load")
    async def extension_load(self, ctx: commands.Context, plugin: str):
        bot = ctx.bot

        if "." not in plugin:
            plugin = f"extensions.{plugin}"

        try:
            await bot.load_extension(plugin)
        except commands.ExtensionNotFound:
            await ctx.message.add_reaction("❓")
        except Exception as e:
            await ctx.send(embed=extensions.Embed(description=f"```py\n{e}{traceback.format_exc()}\n```"))
        else:
            await ctx.message.add_reaction("✅")

    @extension.command(name="unload")
    async def extension_unload(self, ctx: commands.Context, plugin: str):
        bot = ctx.bot

        if "." not in plugin:
            plugin = f"extensions.{plugin}"

        try:
            await bot.unload_extension(plugin)
        except commands.ExtensionNotLoaded:
            await ctx.message.add_reaction("❓")
        except Exception as e:
            await ctx.send(embed=extensions.Embed(description=f"```py\n{e}{traceback.format_exc()}\n```"))
        else:
            await ctx.message.add_reaction("✅")

    @extension.command(name="reload")
    async def extension_reload(self, ctx: commands.Context, plugin: str):
        bot = ctx.bot

        if "." not in plugin:
            plugin = f"extensions.{plugin}"

        try:
            await bot.reload_extension(plugin)
        except commands.ExtensionNotLoaded:
            await ctx.message.add_reaction("❓")
        except Exception as e:
            await ctx.send(embed=extensions.Embed(description=f"```py\n{e}{traceback.format_exc()}\n```"))
        else:
            await ctx.message.add_reaction("✅")

    @commands.command(name="reload-language")
    @commands.is_owner()
    async def reload_language(self, ctx: commands.Context):
        languages._load_languages()

        await ctx.message.add_reaction("✅")

    @commands.command(hidden=True)
    @commands.is_owner()
    async def loadfrommee6(self, ctx: commands.Context, guild_id: int):
        if not len(ctx.message.attachments):
            await ctx.send("Kein Attachment gegeben.")
            return

        if self.bot.get_guild(guild_id) is None:
            await ctx.send("Server nicht gefunden.")
            return

        attachment = ctx.message.attachments[0]
        data = await attachment.read()
        data = data.decode("utf-8")
        users = json.loads(data)

        async with self.bot.db.acquire() as con:
            async with con.transaction():
                await con.execute("DELETE FROM leveling_users WHERE guild_id = $1", guild_id)

                for user in users:
                    await con.execute(
                        "INSERT INTO leveling_users (guild_id, user_id, xp) VALUES ($1, $2, $3)",
                        guild_id,
                        user["uid"],
                        user["xp"],
                    )

        await ctx.send("Level gespeichert")

    @commands.command(name="execute", aliases=["exec"])
    @commands.is_owner()
    async def execute(self, ctx: commands.Context, *, code: str):
        env = {
            "bot": ctx.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "guild": ctx.guild,
        }

        env.update(globals())

        body = code
        stdout = io.StringIO()
        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")
            return

        func = env["func"]
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()

            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                await ctx.send(f"```py\n{value}{ret}\n```")

            await ctx.message.add_reaction("✅")

    @commands.command(name="reload-util")
    @commands.is_owner()
    async def reload_utils(self, ctx: commands.Context, path: str):
        try:
            module_name = importlib.import_module(path)
            importlib.reload(module_name)
        except ModuleNotFoundError:
            await ctx.message.add_reaction("❓")
        except Exception as e:
            await ctx.send(f"```py\n{e}{traceback.format_exc()}\n```")
        else:
            await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[discord.Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        if not guilds:
            if spec == "~":
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                ctx.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await ctx.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                ctx.bot.tree.clear_commands(guild=ctx.guild)
                await ctx.bot.tree.sync(guild=ctx.guild)
                synced = []
            else:
                synced = await ctx.bot.tree.sync()

            await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
            return

        ret = 0
        for guild in guilds:
            try:
                await ctx.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


async def setup(bot: Plyoox):
    await bot.add_cog(Owner(bot))
