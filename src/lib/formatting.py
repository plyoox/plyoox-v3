from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import discord

GUILD_FORMAT_REGEX = re.compile("{guild\\.(name|id|members)}")
USER_FORMAT_REGEX = re.compile("{user\\.(name|id|mention|discriminator)}")


class LevelFormatObject:
    def __init__(self, *, level: int, role: discord.Role = None):
        self.level = level
        self.role = role

    def __repr__(self):
        return self.level


def format_welcome_message(message: str, member: discord.Member) -> str | None:
    """Formats a join or leave message."""
    guild = discord.Guild

    return (
        message.replace("{user}", str(member))
        .replace("{user.name}", member.name)
        .replace("{user.discriminator}", member.discriminator)
        .replace("{user.id}", str(member.id))
        .replace("{guild.name}", guild.name)
        .replace("{guild.members}", str(guild.member_count))
        .replace("{guild.id}", str(guild.id))
    )


def format_leveling_message(message: str, member: discord.Member, level: LevelFormatObject) -> str | None:
    """Formats a leveling message."""
    guild = member.guild

    if "{level.role}" in message and level.role is None:
        return

    return (
        message.replace("{user}", str(member))
        .replace("{user.name}", member.name)
        .replace("{user.discriminator}", member.discriminator)
        .replace("{user.id}", str(member.id))
        .replace("{guild.name}", guild.name)
        .replace("{guild.members}", str(guild.member_count))
        .replace("{level}", str(level))
        .replace("{level.role}", str(guild.id))
    )
