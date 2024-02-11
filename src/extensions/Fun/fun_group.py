from __future__ import annotations

import json
import random
from typing import Optional, TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands
from discord.app_commands import locale_str as _

from lib import extensions

if TYPE_CHECKING:
    from main import Plyoox


@app_commands.guild_only
class Fun(commands.GroupCog, group_name="fun", group_description=_("Provides fun commands.")):
    gifs: dict[str, list[str]]

    def __init__(self, bot: Plyoox):
        self.bot = bot

    async def cog_load(self) -> None:
        with open("src/extensions/Fun/gifs.json") as f:
            self.gifs = json.load(f)

    @app_commands.command(name="coinflip", description=_("Flip a coin."))
    async def coinflip(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice((":coin:", ":one:")))

    @app_commands.command(name="color", description=_("Generates a random color."))
    async def color(self, interaction: discord.Interaction):
        color = random.randint(0x000000, 0xFFFFFF)
        red = color >> 16 & 0xFF
        green = color >> 8 & 0xFF
        blue = color & 0xFF

        embed = extensions.Embed(
            description=interaction.translate(_("Random color:\nHEX: `{hex}`\nRGB: `{rgb}`")).format(
                rgb=f"{red}, {green}, {blue}", hex=f"#{color:06X}"
            ),
            color=color,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slot", description=_("Spin a slot machine."))
    async def slot(self, interaction: discord.Interaction):
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
            embed.description += "\n\n" + interaction.translate(_("You won! :tada:"))
        else:
            embed.description += "\n\n" + interaction.translate(_("You lost :cry:"))

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ship", description=_("Ship two users."))
    @app_commands.describe(
        user1=_("A user to be shipped"), user2=_("Another optional user that will be shipped with the first one")
    )
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: Optional[discord.Member]):
        if user2 is None:
            user2 = interaction.user

        if user1 == user2:
            await interaction.response.send_message(
                "https://c.tenor.com/7xUwizApagsAAAAC/bud-graceandfrankie.gif", ephemeral=True
            )
            return

        percent = random.Random(f"{user1}{user2}").randint(0, 100)
        embed = extensions.Embed(
            title=f"{user1.name} :heart: {user2.name}", description=f"**`{('█' * (percent // 10)):10}` {percent}%**"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="thisorthat", description=_("Chooses one of the two given choices."))
    @app_commands.describe(this=_("The first choice"), that=_("The second choice"))
    async def thisorthat(self, interaction: discord.Interaction, this: str, that: str):
        await interaction.response.send_message(
            f"**{interaction.translate(_('My random answer'))}**\n{random.choice((this, that))}"
        )

    @app_commands.command(name="dice", description=_("Roll a dice."))
    async def dice(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            random.choice((":one:", ":two:", ":three:", ":four:", ":five:", ":six:"))
        )

    @app_commands.command(name="cat", description=_("Shows a random cat."))
    async def cat(self, interaction: discord.Interaction):
        async with self.bot.session.get("https://api.thecatapi.com/v1/images/search") as res:
            if res.status != 200:
                await interaction.response.send_translated(_("Could not get a cat :("))
                return

            js = await res.json()
            await interaction.response.send_message(embed=discord.Embed().set_image(url=js[0]["url"]))

    @app_commands.command(name="dog", description=_("Shows a random dog."))
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.defer()

        for _i in range(3):
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

    @app_commands.command(name="cry", description=_("Cries."))
    async def cry(self, interaction: discord.Interaction):
        embed = extensions.Embed(
            description=interaction.translate(_("{user.mention} cries :cry:")).format(user=interaction.user)
        )
        embed.set_image(url=random.choice(self.gifs["cry"]))

        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(name="hug", description=_("Hugs a user."))
    @app_commands.describe(member=_("The user to hug."))
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            await interaction.response.send_message(
                "https://c.tenor.com/7xUwizApagsAAAAC/bud-graceandfrankie.gif", ephemeral=True
            )
            return

        embed = extensions.Embed(
            description=interaction.translate(_("{user.mention} hugs {target.mention}")).format(
                user=interaction.user, target=member
            )
        )
        embed.set_image(url=random.choice(self.gifs["hug"]))

        await interaction.response.send_message(embed=embed)
