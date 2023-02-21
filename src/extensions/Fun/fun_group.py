from __future__ import annotations

import json
import random
from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from lib import extensions
from translation import _

if TYPE_CHECKING:
    from main import Plyoox


@app_commands.guild_only
class Fun(commands.GroupCog, group_name="fun", group_description="Provides fun commands."):
    gifs: dict[str, list[str]]

    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def cog_load(self) -> None:
        with open("src/extensions/Fun/gifs.json") as f:
            self.gifs = json.load(f)

    @app_commands.command(name="coinflip", description="Flips a coin.")
    async def coinflip(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice((":coin:", ":one:")))

    @app_commands.command(name="color", description="Generates a random color.")
    async def color(self, interaction: discord.Interaction):
        lc = interaction.locale

        color = random.randint(0x000000, 0xFFFFFF)
        red = color >> 16 & 0xFF
        green = color >> 8 & 0xFF
        blue = color & 0xFF

        embed = extensions.Embed(
            description=_(lc, "fun.color", rgb=f"{red}, {green}, {blue}", hex=f"#{color:06X}"), color=color
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slot", description="Rolls a slot machine.")
    async def slot(self, interaction: discord.Interaction):
        lc = interaction.locale

        result = []
        embed = extensions.Embed(description=" ".join(result))

        for i in range(3):
            result.append(
                random.choice(
                    (":cherries:", ":strawberry:", ":grapes:", ":pineapple:", ":tangerine:")
                )  # 0.8% probability of winning
            )

            embed = extensions.Embed(description=" ".join(result))

        if len(set(result)) == 1:
            embed.description += "\n\n" + _(lc, "fun.slot.win")
        else:
            embed.description += "\n\n" + _(lc, "fun.slot.lose")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ship", description="Ships two users.")
    @app_commands.describe(
        user1="A user to be shipped", user2="Another optional user that will be shipped with the first one"
    )
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: Optional[discord.Member]):
        lc = interaction.locale

        if user2 is None:
            user2 = interaction.user

        if user1 == user2:
            await interaction.response.send_message(_(lc, "fun.ship.same"), ephemeral=True)
            return

        percent = random.Random(f"{user1}{user2}").randint(0, 100)
        embed = extensions.Embed(
            title=f"{user1.name} :heart: {user2.name}", description=f"**`{('█' * (percent // 10)):10}` {percent}%**"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="thisorthat", description="Chooses one of the two given choices.")
    @app_commands.describe(this="The first choice", that="The second choice")
    async def thisorthat(self, interaction: discord.Interaction, this: str, that: str):
        lc = interaction.locale

        await interaction.response.send_message(f"**{_(lc, 'fun.thisorthat.title')}**\n{random.choice((this, that))}")

    @app_commands.command(name="dice", description="Rolls a dice.")
    async def dice(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            random.choice((":one:", ":two:", ":three:", ":four:", ":five:", ":six:"))
        )

    @app_commands.command(name="cat", description="Shows a random cat.")
    async def cat(self, interaction: discord.Interaction):
        lc = interaction.locale

        async with self.bot.session.get("https://api.thecatapi.com/v1/images/search") as res:
            if res.status != 200:
                await interaction.response.send_message(_(lc, "fun.cat.bad_response"))
                return

            js = await res.json()
            await interaction.response.send_message(embed=discord.Embed().set_image(url=js[0]["url"]))

    @app_commands.command(name="dog", description="Shows a random dog.")
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.defer()

        for _ in range(3):
            async with self.bot.session.get("https://random.dog/woof") as resp:
                if resp.status != 200:
                    await interaction.followup.send("No dog found :(")
                    return

                filename = await resp.text()

                if not filename.endswith(".mp4"):
                    url = f"https://random.dog/{filename}"
                    await interaction.followup.send(embed=discord.Embed().set_image(url=url))
                    return

        await interaction.followup.send("No dog found :(")

    @app_commands.command(name="cry", description="Cries.")
    async def cry(self, interaction: discord.Interaction):
        lc = interaction.locale

        embed = extensions.Embed(description=_(lc, "fun.cry", user=interaction.user))
        embed.set_image(url=random.choice(self.gifs["cry"]))

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hug", description="Hugs a user.")
    @app_commands.describe(member="The user to hug.")
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale

        if member == interaction.user:
            await interaction.response.send_message(
                "https://c.tenor.com/7xUwizApagsAAAAC/bud-graceandfrankie.gif", ephemeral=True
            )
            return

        embed = extensions.Embed(description=_(lc, "fun.hug", user=interaction.user, target=member))
        embed.set_image(url=random.choice(self.gifs["hug"]))

        await interaction.response.send_message(embed=embed)
