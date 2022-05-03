from discord import app_commands


class OwnerOnly(app_commands.AppCommandError):
    pass
