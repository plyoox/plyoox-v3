from __future__ import annotations

import gettext
import importlib.resources
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

import discord
from discord import app_commands

from lib.errors import TranslationError

if TYPE_CHECKING:
    from main import Plyoox


_LOCALES_PATH = Path(str(importlib.resources.files(__package__).joinpath("locales")))

DOMAIN = "plyoox"

_log = logging.getLogger(__name__)


def locale_to_gnu(locale: discord.Locale) -> str:
    return str(locale).replace("-", "_")


def yield_mo_paths() -> Iterator[Path]:
    if not _LOCALES_PATH.is_dir():
        return

    for locale in _LOCALES_PATH.iterdir():
        lc_messages = locale / "LC_MESSAGES"
        if not lc_messages.is_dir():
            continue

        yield from lc_messages.glob("*.mo")


class EmptyTranslations(gettext.NullTranslations):
    """Returns an empty message to indicate no translation is available."""

    def gettext(self, message: str) -> None:
        return None

    def ngettext(self, msgid1: str, msgid2: str, n: int) -> None:
        return None

    def pgettext(self, context: str, message: str) -> None:
        return None

    def npgettext(self, context: str, msgid1: str, msgid2: str, n: int) -> None:
        return None


class GettextTranslator(app_commands.Translator):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if not any(yield_mo_paths()):
            _log.warning("No compiled localizations detected")

    def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContextTypes,
    ) -> str | None:
        try:
            t = gettext.translation(
                domain=DOMAIN,
                localedir=str(_LOCALES_PATH),
                languages=(locale_to_gnu(locale), "en_US"),
            )
        except OSError as e:
            _log.error(f"Failed to load locale {locale}", e)
            raise TranslationError(f"Failed to load locale {locale}") from e

        t.add_fallback(EmptyTranslations())

        plural: str | None = string.extras.get("plural")
        if plural is not None:
            assert isinstance(context.data, int)
            translated = t.ngettext(string.message, plural, context.data)
        else:
            translated = t.gettext(string.message)

        if context.location is app_commands.TranslationContextLocation.other and isinstance(context.data, dict):
            translated = translated.format(**context.data)

        return translated or f"~~{str(string)}~~"


def plural_locale_str(
    singular: str,
    plural: str,
    **kwargs,
) -> app_commands.locale_str:
    """A shorthand for defining a string with singular and plural variants.

    This should be aliased to ngettext, ungettext, or dngettext
    so the `xgettext` program can recognize the function.

    """
    return app_commands.locale_str(singular, plural=plural, **kwargs)


def translate(
    message: app_commands.locale_str,
    obj: Plyoox,
    locale: discord.Locale | None = None,
    data: Any = None,
) -> str:
    """A shorthand for translating a message.

    Unlike the methods built into discord.py, this will use the original message
    if a translation could not be found.
    """
    if locale is None:
        return str(message)

    assert obj.tree.translator is not None
    context = app_commands.TranslationContext(
        location=app_commands.TranslationContextLocation.other,
        data=data,
    )
    translated = obj.tree.translator.translate(
        message,
        locale=locale,
        context=context,
    )

    return translated or f"~~{str(message)}~~"