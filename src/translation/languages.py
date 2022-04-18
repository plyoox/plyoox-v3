import os

import yaml
from discord import Interaction, Locale

_languages = dict()


def _flatten_dict(_dict: dict[str, str | dict]):
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
    path = os.getcwd().replace("\\", "//") + "//translation//languages"
    files = os.listdir(path)

    for file in files:
        if file.endswith(".yaml"):
            with open(f"{path}//{file}", encoding="utf8") as language_file:
                data = yaml.safe_load(language_file)
                language_data = _flatten_dict(data)

                _languages[file.replace(".yaml", "")] = language_data


def _(locale: Locale, key: str | bool, **kwargs):
    locale = "de" if locale == Locale.german else "en"

    return get_key(locale, key, **kwargs)


def get_key(language: str, key: str, **kwargs: dict[str, ...]):
    lang: dict = _languages.get(language)
    message: str = lang.get(key)

    if message:
        try:
            return message.format(**kwargs)
        except KeyError:
            pass

    return f"{language}.{key}"


async def interaction_send(interaction: Interaction, key: str, ephemeral=True):
    await interaction.response.send_message(_(interaction.locale, key), ephemeral=ephemeral)


_load_languages()
