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


class GuildFormatObject:
    def __init__(self, guild: discord.Guild):
        self.name = guild.name
        self.id = guild.id
        self.member_count = guild.member_count

    def __repr__(self):
        return self.name


class MemberFormatObject:
    def __init__(self, member: discord.Member):
        self.name = member.name
        self.discriminator = member.discriminator
        self.id = member.id

    def __repr__(self):
        return f"{self.name}#{self.discriminator}"

    @property
    def mention(self):
        return f"<@{self.id}>"


def format_welcome_message(
    message: str, member: MemberFormatObject, guild: GuildFormatObject
) -> str | None:
    try:
        return message.format(guild=guild, user=member)
    except KeyError:
        return (
            message.replace("{user}", str(member))
            .replace("{user.name}", member.name)
            .replace("{user.discriminator}", member.discriminator)
            .replace("{user.id}", str(member.id))
            .replace("{guild.name}", guild.name)
            .replace("{guild.members}", str(guild.member_count))
            .replace("{guild.id}", str(guild.id))
        )


def format_leveling_message(
    message: str, member: MemberFormatObject, guild: GuildFormatObject, level: LevelFormatObject
) -> str | None:
    if "{level.role}" in message and level.role is None:
        return

    try:
        return message.format(guild=guild, user=member, level=level)
    except KeyError:
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
