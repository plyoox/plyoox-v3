from discord import Interaction, app_commands

from lib import errors


def guild_only_check(interaction: Interaction) -> bool:
    if interaction.guild is None:
        raise errors.GuildOnly

    return True


def guild_only():
    return app_commands.check(guild_only_check)
