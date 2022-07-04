import datetime
import re

import discord

from dateutil.relativedelta import relativedelta


# https://github.com/Rapptz/RoboDanny/blob/rewrite/cogs/utils/time.py
_COMPILED = re.compile(
    """
       (?:(?P<months>[0-9]{1,2})(?:months?|mo))?        # e.g. 2months
       (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?           # e.g. 10w
       (?:(?P<days>[0-9]{1,5})(?:days?|d))?             # e.g. 14d
       (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?           # e.g. 12h
       (?:(?P<minutes>[0-9]{1,5})(?:minutes?|min?|m))?  # e.g. 10m
       (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?       # e.g. 15s
    """,
    re.VERBOSE,
)


def parse_datetime_from_string(_input: str) -> datetime.datetime | None:
    """Parses a string into a datetime object."""
    match = _COMPILED.fullmatch(_input)
    if match is None:
        return None

    data = {k: int(v) for k, v in match.groupdict(default=0).items()}
    return discord.utils.utcnow() + relativedelta(**data)
