from collections.abc import Callable

from discord.app_commands import locale_str

type Translate = Callable[[locale_str], str]
