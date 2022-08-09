import discord
from discord import app_commands

from translation import get_command_key


Location = app_commands.TranslationContextLocation


class Translator(app_commands.Translator):
    def __init__(self):
        pass

    count = 0

    async def translate(
        self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext
    ) -> str | None:
        if locale != discord.Locale.german or str(context.location).endswith("_name"):
            return

        key = string.extras.get("key")

        if key:
            return get_command_key(locale, key)
