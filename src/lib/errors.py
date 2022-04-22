from discord import app_commands


class GuildOnly(app_commands.AppCommandError):
    pass
