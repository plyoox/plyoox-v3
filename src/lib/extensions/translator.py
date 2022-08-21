import logging

import discord
from discord import app_commands

from translation import get_command_key


_log = logging.getLogger(__name__)
Location = app_commands.TranslationContextLocation


class Translator(app_commands.Translator):
    def __init__(self):
        pass

    @staticmethod
    def _command_to_locale_key(command: app_commands.Command) -> list[str]:
        locale_keys = []
        cmd = command

        while cmd.parent is not None:
            if isinstance(cmd.parent, (app_commands.Command, app_commands.Group)):
                locale_keys.insert(0, str(cmd.parent.name))
                cmd = cmd.parent

        locale_keys.append(str(command.name))

        return locale_keys

    @staticmethod
    def _to_locale_key(context: app_commands.TranslationContext) -> str | None:
        obj = context.data
        location = context.location

        locale_keys = []

        if location is Location.command_description:
            locale_keys = Translator._command_to_locale_key(context.data)
            locale_keys.append("description")
        elif location is Location.group_description:
            locale_keys = Translator._command_to_locale_key(context.data)
            locale_keys.append("description")
        elif location is Location.parameter_description:
            locale_keys = Translator._command_to_locale_key(obj.command)
            locale_keys.append(str(obj.name))

        if not locale_keys:
            return

        return ".".join(locale_keys)

    async def translate(
        self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext
    ) -> str | None:
        if locale != discord.Locale.german:
            return

        if str(context.location).endswith("_name") and not isinstance(context.data, app_commands.ContextMenu):
            return

        locale_key = self._to_locale_key(context)
        if locale_key is not None:
            text = get_command_key(locale, locale_key)
            if text is not None:
                return text

        locale_key = string.extras.get("key")
        alternative_string = get_command_key(locale, locale_key)

        if alternative_string is None:
            _log.warning(f"No translation for key: {locale_key}")

        return alternative_string
