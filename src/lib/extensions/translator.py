import discord
from discord import app_commands
from discord.ext import commands

from translation import get_command_key


Location = app_commands.TranslationContextLocation


class Translator(app_commands.Translator):
    def __init__(self):
        pass

    count = 0

    @staticmethod
    def _command_to_locale_key(command: app_commands.Command) -> list[str]:
        locale_keys = []

        if isinstance(command.binding, commands.GroupCog):
            locale_keys.append(str(command.binding.__cog_group_name__))
        elif isinstance(command.binding, app_commands.Command):
            if hasattr(command.binding, "binding"):
                if isinstance(command.binding.binding, commands.GroupCog):
                    locale_keys.append(str(command.binding.binding.__cog_group_name__))
                else:
                    locale_keys.append(str(command.binding.binding.name))
            else:
                locale_keys.append(str(command.binding.name))

        locale_keys.append(str(command.name))

        return locale_keys

    @staticmethod
    def _to_locale_key(context: app_commands.TranslationContext):
        obj = context.data
        location = context.location

        locale_keys = []

        if location is Location.command_description:
            locale_keys = Translator._command_to_locale_key(context.data)
            locale_keys.append("description")
        elif location is Location.group_description:
            locale_keys.append(str(obj.name))
            locale_keys.append("description")
        elif location is Location.parameter_description:
            locale_keys = Translator._command_to_locale_key(obj.command)
            locale_keys.append(str(obj.name))

        return ".".join(locale_keys)

    async def translate(
        self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext
    ) -> str | None:
        if locale != discord.Locale.german or str(context.location).endswith("_name"):
            return

        key = string.extras.get("key")

        # if not key:
        #     key = self._to_locale_key(context)

        print(key == self._to_locale_key(context), key, self._to_locale_key(context))

        return get_command_key(locale, key)
