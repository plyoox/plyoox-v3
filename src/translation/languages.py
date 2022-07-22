import logging
import os
import traceback

import discord
import yaml

logger = logging.getLogger(__name__)

_languages = dict()


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


def _load_languages():
    path = os.getcwd().replace("\\", "/") + "/src/translation/languages"

    files = os.listdir(path)

    for file in files:
        if file.endswith(".yaml"):
            with open(f"{path}/{file}", encoding="utf8") as language_file:
                data = yaml.safe_load(language_file)
                language_data = _flatten_dict(data)

                _languages[file.replace(".yaml", "")] = language_data


def _(locale: discord.Locale, key: str | bool, **kwargs):
    """Returns the message for the given locale. Currently, only german and english are available.
    If the user has a language that is not available it will fall back to english."""
    # locale = "de" if locale == discord.Locale.german else "en"
    locale = "de" if locale == discord.Locale.german else "de"

    return get_key(locale, key, **kwargs)


def get_key(language: str, key: str, **kwargs: dict[str, ...]):
    """Returns the localized message for a key. If the key is not available, a placeholder is returned."""
    lang: dict = _languages.get(language)
    message: str = lang.get(key)

    if message is not None:
        try:
            return message.format(**kwargs)
        except KeyError:
            logger.error(f"Could not format message {key}\n: {traceback.format_exc()}")
            return message

    return f"{language}.{key}"


_load_languages()
