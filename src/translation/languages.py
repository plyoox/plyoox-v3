import logging
import os

import discord
import yaml

logger = logging.getLogger(__name__)

_languages = dict()
_commands = dict()


def _flatten_dict(_dict: dict[str, str | dict]) -> dict:
    result = {}

    for _key, _value in _dict.items():
        if isinstance(_value, str):
            result[_key] = _value
        else:
            _flatten_result = _flatten_dict(_value)
            for __key, __value in _flatten_result.items():
                result[f"{_key}.{__key}"] = __value

    return result


def _load_languages() -> None:
    path = os.getcwd().replace("\\", "/") + "/src/translation/languages"

    dirs = os.listdir(path)

    for language in dirs:
        locale_path = f"{path}/{language}"

        if os.path.isdir(locale_path):
            if os.path.exists(f"{locale_path}/messages.yaml"):
                with open(f"{locale_path}/messages.yaml", encoding="utf8") as language_file:
                    data = yaml.safe_load(language_file)
                    language_data = _flatten_dict(data)

                    _languages[language] = language_data

            if os.path.exists(f"{locale_path}/commands.yaml"):
                with open(f"{locale_path}/commands.yaml", encoding="utf8") as language_file:
                    data = yaml.safe_load(language_file)
                    language_data = _flatten_dict(data)

                    _commands[language] = language_data


def _(locale: discord.Locale, key: str | bool, **kwargs) -> str:
    """Returns the message for the given locale. Currently, only german and english are available.
    If the user has a language that is not available it will fall back to english."""
    locale = "de" if locale == discord.Locale.german else "en"

    return get_key(locale, key, **kwargs)


def get_command_key(locale: discord.Locale, key: str) -> str | None:
    """Returns the localized values for a command localization key."""
    language = _commands.get(locale.value)  # type: ignore
    if language is not None:
        return language.get(key)


def get_key(language: str, key: str, **kwargs: dict[str, ...]) -> str:
    """Returns the localized message for a key. If the key is not available, a placeholder is returned."""
    lang: dict = _languages.get(language)
    message: str = lang.get(key)

    if message is not None:
        try:
            return message.format(**kwargs)
        except KeyError as e:
            logger.error(f"Could not format message {key}: KeyError '{str(e)}'")
            return message

    return f"{language}.{key}"


_load_languages()
