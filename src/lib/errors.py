from discord import app_commands


class OwnerOnly(app_commands.AppCommandError):
    pass


class GuildOnly(app_commands.AppCommandError):
    pass
