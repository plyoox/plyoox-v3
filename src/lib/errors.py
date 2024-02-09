from discord import app_commands


class ModuleDisabled(app_commands.AppCommandError):
    pass


class AnilistQueryError(app_commands.AppCommandError):
    pass


class TranslationError(app_commands.AppCommandError):
    pass
