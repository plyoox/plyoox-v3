from __future__ import annotations

from typing import TYPE_CHECKING
import datetime

import discord

from lib import emojis

if TYPE_CHECKING:
    from datetime import datetime


def format_roles(roles: list[discord.Role]) -> str | None:
    """
    Converts a list of roles to a string of mentions. If the result is longer than 1024 characters
    (limit of embed field) "..." is added to the end.
    """
    if len(roles) == 1:
        return None

    _roles = roles.copy()

    result = []
    _roles.reverse()
    _roles.pop()

    for role in _roles[:44]:  # max 1024 characters
        result.append(role.mention)

    if len(_roles) > 44:
        return " ".join(result) + "..."

    return " ".join(result)


def get_badges(flags: discord.PublicUserFlags) -> list[str]:
    """Returns a list of the public flags a user has."""
    flag_list = []

    if flags.staff:
        flag_list.append(emojis.staff)
    if flags.partner:
        flag_list.append(emojis.partner)
    if flags.bug_hunter:
        flag_list.append(emojis.bughunter)
    if flags.early_supporter:
        flag_list.append(emojis.early_supporter)
    if flags.hypesquad:
        flag_list.append(emojis.hypesquad)
    if flags.hypesquad_balance:
        flag_list.append(emojis.hypesquad_balance)
    if flags.hypesquad_brilliance:
        flag_list.append(emojis.hypesquad_brilliance)
    if flags.hypesquad_bravery:
        flag_list.append(emojis.hypesquad_bravery)
    if flags.verified_bot_developer:
        flag_list.append(emojis.botdev)
    if flags.bug_hunter_level_2:
        flag_list.append(emojis.bughunter2)
    if flags.active_developer:
        flag_list.append(emojis.active_developer)

    return flag_list


async def permission_check(
    channel: discord.TextChannel | discord.VoiceChannel | discord.Thread,
    content: str = None,
    embeds: list[discord.Embed] = None,
) -> None:
    """Only sends the message if the bot has the permission to send messages in the channel."""
    if channel is None:
        return

    if channel.permissions_for(channel.guild.me).send_messages:
        await channel.send(content=content, embeds=embeds)


def embed_timestamp_format(timestamp: datetime) -> str:
    return f"> {discord.utils.format_dt(timestamp)}\n> {discord.utils.format_dt(timestamp, 'R')}"


def format_timedelta(delta: datetime.timedelta) -> str:
    parts = []
    if delta.days > 0:
        parts.append("{}d".format(delta.days))

    hours, remainder = divmod(delta.seconds, 3600)
    if hours > 0:
        parts.append("{}h".format(hours))

    minutes, seconds = divmod(remainder, 60)
    if minutes > 0:
        parts.append("{}m".format(minutes))
    if seconds > 0:
        parts.append("{}s".format(seconds))
    return " ".join(parts)


def italic(string: str) -> str:
    return f"*{string}*"
