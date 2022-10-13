from __future__ import annotations

import re

import discord

GUILD_FORMAT_REGEX = re.compile(r"{guild\.(name|id|members)}")
USER_FORMAT_REGEX = re.compile(r"{user\.(name|id|mention|discriminator)}")

CHANNEL_REGEX = re.compile("(#.{1,100})")


class LevelFormatObject:
    def __init__(self, *, level: int, role: discord.Role = None):
        self.level = level
        self.role = role

    def __repr__(self):
        return self.level

    def __str__(self):
        return str(self.level)


def format_welcome_message(message: str, member: discord.Member) -> str:
    """Formats a join or leave message."""
    guild = member.guild

    return (
        message.replace("{user}", str(member))
        .replace("{user.name}", member.name)
        .replace("{user.mention}", member.mention)
        .replace("{user.discriminator}", member.discriminator)
        .replace("{user.id}", str(member.id))
        .replace("{guild.name}", guild.name)
        .replace("{guild.member_count}", str(guild.member_count))
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
        .replace("{user.mention}", member.mention)
        .replace("{user.discriminator}", member.discriminator)
        .replace("{user.id}", str(member.id))
        .replace("{guild.name}", guild.name)
        .replace("{guild.id}", str(guild.id))
        .replace("{guild.member_count}", str(guild.member_count))
        .replace("{level}", str(level))
        .replace("{level.role}", level.role.mention)
    )


def resolve_channels(message: str, guild: discord.Guild) -> str:
    resolved_channels: list[str] = CHANNEL_REGEX.findall(message)

    for channel in set(resolved_channels):
        if channel.count("#") != 1:
            continue

        guild_channel: discord.TextChannel = discord.utils.get(guild.text_channels, name=channel[1:])

        if guild_channel is not None:
            message = message.replace(channel, guild_channel.mention)

    return message
