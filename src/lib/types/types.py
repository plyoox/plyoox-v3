import datetime
from collections.abc import Callable
from typing import TypedDict

from discord.app_commands import locale_str

type Translate = Callable[[locale_str], str]
type Infractions = list[Infraction]


class Infraction(TypedDict):
    id: int
    user_id: int
    guild_id: int
    expires_at: datetime.datetime
    created_at: datetime.datetime
    points: int
    reason: str | None
