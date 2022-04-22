import discord

from lib import errors


def guild_only_check(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        raise errors.GuildOnly

    return True


def guild_only():
    return discord.app_commands.check(guild_only_check)
