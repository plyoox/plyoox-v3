import asyncio
import json
import random
from typing import Optional

import discord
from discord import Embed, app_commands
from discord.ext import commands
from main import Plyoox
from translation import _


with open("plugins/Fun/gifs.json") as f:
    gifs = json.load(f)


@app_commands.guild_only
class Fun(
    commands.GroupCog,
    group_name="fun",
    group_description="Provides fun commands.",
):
    def __init__(self, bot: Plyoox):
        self.bot = bot

    @app_commands.command(name="coinflip", description="Flipps a coin.")
    async def coinflip(self, interaction: discord.Interaction):
        if random.randint(0, 1):
            await interaction.response.send_message(":coin:")
        else:
            await interaction.response.send_message(":one:")

    @app_commands.command(name="color", description="Generates a random color.")
    async def color(self, interaction: discord.Interaction):
        lc = interaction.locale

        color = random.randint(0x000000, 0xFFFFFF)
        red = color >> 16 & 0xFF
        green = color >> 8 & 0xFF
        blue = color & 0xFF

        embed = Embed(description=_(lc, "fun.color", rgb=f"{red}, {green}, {blue}", hex=f"#{color:06X}"), color=color)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slot", description="Rolls a slot machine.")
    async def slot(self, interaction: discord.Interaction):
        lc = interaction.locale
        result = [":grey_question:"] * 3
        embed = Embed(description=" ".join(result))
        await interaction.response.send_message(embed=embed)
        for i in range(3):
            await asyncio.sleep(0.5)
            result[i] = random.choice((":cherries:", ":strawberry:", ":grapes:", ":pineapple:", ":tangerine:"))  # 0.8% probability of winning
            embed = Embed(description=" ".join(result))
            if i == 2:
                if result[0] == result[1] == result[2]:
                    embed.description += "\n\n" + _(lc, "fun.slot.win")
                else:
                    embed.description += "\n\n" + _(lc, "fun.slot.lose")
            await interaction.edit_original_message(embed=embed)

    @app_commands.command(name="ship", description="Ships two users.")
    @app_commands.describe(user1="A user to be shipped", user2="Another optional user that will be shipped with the first one")
    async def ship(self, interaction: discord.Interaction, user1: discord.Member, user2: Optional[discord.Member]):
        lc = interaction.locale
        if user2 is None:
            user2 = interaction.user
        if user1 == user2:
            await interaction.response.send_message(_(lc, "fun.ship.same"), ephemeral=True)
            return
        percent = random.randint(0, 100)
        embed = Embed(
            title=f"{user1.name} :heart: {user2.name}",
            description=f"**`{('█' * (percent // 10)):10}` {percent}%**"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="thisorthat", description="Chooses one of the two given arguments.")
    @app_commands.describe(this="The first argument", that="The second argument")
    async def thisorthat(self, interaction: discord.Interaction, this: str, that: str):
        lc = interaction.locale
        embed = Embed(title=_(lc, "fun.thisorthat.title"), description=random.choice((this, that)))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Rolls a dice.")
    async def dice(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice((":one:", ":two:", ":three:", ":four:", ":five:", ":six:")))

    @app_commands.command(name="cat", description="Shows a cute cat.")
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(gifs["cat"]))

    @app_commands.command(name="dog", description="Shows a cute dog.")
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(gifs["dog"]))

    @app_commands.command(name="cry", description="Cries.")
    async def cry(self, interaction: discord.Interaction):
        lc = interaction.locale
        embed = Embed(description=_(lc, "fun.cry", mention=interaction.user.mention))
        embed.set_image(url=random.choice(gifs["cry"]))
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="hug", description="Hugs a user.")
    @app_commands.describe(member="The user to hug.")
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        lc = interaction.locale
        if member == interaction.user:
            await interaction.response.send_message(_(lc, "fun.hug.self_hug"), ephemeral=True)
            return
        embed = Embed(description=_(lc, "fun.hug.successfully_hugged", mention=interaction.user.mention, target=member.mention))
        embed.set_image(url=random.choice(gifs["hug"]))
        await interaction.response.send_message(embed=embed)


async def setup(bot: Plyoox):
    await bot.add_cog(Fun(bot))
