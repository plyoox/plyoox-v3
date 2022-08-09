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


_T = app_commands.locale_str


@app_commands.guild_only
class Fun(
    commands.GroupCog,
    group_name=_T("fun", key="fun.name"),
    group_description=_T("Provides fun commands.", key="fun.description"),
):
    gifs: dict[str, list[str]]

    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def cog_load(self) -> None:
        with open("src/plugins/Fun/gifs.json") as f:
            self.gifs = json.load(f)

    @app_commands.command(
        name=_T("coinflip", key="fun.coinflip.name"), description=_T("Flips a coin.", key="fun.coinflip.description")
    )
    async def coinflip(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice((":coin:", ":one:")))

    @app_commands.command(
        name=_T("color", key="fun.color.description"),
        description=_T("Generates a random color.", key="fun.color.description"),
    )
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

    @app_commands.command(
        name=_T("slot", key="fun.slot.name"), description=_T("Rolls a slot machine.", key="fun.slot.description")
    )
    async def slot(self, interaction: discord.Interaction):
        lc = interaction.locale

        result = []
        embed = extensions.Embed(description=" ".join(result))

        for i in range(3):
            result[i] = random.choice(
                (":cherries:", ":strawberry:", ":grapes:", ":pineapple:", ":tangerine:")
            )  # 0.8% probability of winning

            embed = extensions.Embed(description=" ".join(result))

        if len(set(result)) == 1:
            embed.description += "\n\n" + _(lc, "fun.slot.win")
        else:
            embed.description += "\n\n" + _(lc, "fun.slot.lose")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name=_T("ship", key="fun.ship.name"), description=_T("Ships two users.", key="fun.ship.description")
    )
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

        percent = random.randint(0, 100)
        embed = extensions.Embed(
            title=f"{user1.name} :heart: {user2.name}", description=f"**`{('█' * (percent // 10)):10}` {percent}%**"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name=_T("thisorthat", key="fun.thisorthat.name"),
        description=_T("Chooses one of the two given choices.", key="fun.thisorthat.description"),
    )
    @app_commands.describe(
        this=_T("The first choice", key="fun.thisorthat.this"), that=_T("The second choice", key="fun.thisorthat.that")
    )
    async def thisorthat(self, interaction: discord.Interaction, this: str, that: str):
        lc = interaction.locale

        await interaction.response.send_message(f"**{_(lc, 'fun.thisorthat.title')}**\n{random.choice((this, that))}")

    @app_commands.command(
        name=_T("dice", key="fun.dice.name"), description=_T("Rolls a dice.", key="fun.dice.description")
    )
    async def dice(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            random.choice((":one:", ":two:", ":three:", ":four:", ":five:", ":six:"))
        )

    @app_commands.command(
        name=_T("cat", key="fun.cat.name"), description=_T("Shows a cute cat.", key="fun.cat.description")
    )
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(self.gifs["cat"]))

    @app_commands.command(
        name=_T("dog", key="fun.dog.name"), description=_T("Shows a cute dog.", key="fun.dog.description")
    )
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(self.gifs["dog"]))

    @app_commands.command(name=_T("cry", key="fun.cry.name"), description=_T("Cries.", key="fun.cry.description"))
    async def cry(self, interaction: discord.Interaction):
        lc = interaction.locale

        await interaction.response.send_message(
            f"{_(lc, 'fun.cry', user=interaction.user)} {random.choice(self.gifs['cry'])}"
        )

    @app_commands.command(
        name=_T("hug", key="fun.hug.name"), description=_T("Hugs a user.", description="fun.hug.description")
    )
    @app_commands.describe(member=_T("The user to hug.", key="fun.hug.member"))
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale

        if member == interaction.user:
            await interaction.response.send_message(
                "https://c.tenor.com/7xUwizApagsAAAAC/bud-graceandfrankie.gif", ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"{_(lc, 'fun.hug', user=interaction.user, target=member)} {random.choice(self.gifs['hug'])}"
        )
