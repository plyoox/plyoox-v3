import random

import discord
from discord import Embed, app_commands
from discord.ext import commands
from main import Plyoox
from translation import _


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


async def setup(bot: Plyoox):
    await bot.add_cog(Fun(bot))
