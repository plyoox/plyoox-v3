from discord import app_commands


class OwnerOnly(app_commands.AppCommandError):
    pass


class ModuleDisabled(app_commands.AppCommandError):
    pass


class AnilistQueryError(app_commands.AppCommandError):
    pass
