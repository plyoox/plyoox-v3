import re

from discord import Member

GUILD_FORMAT_REGEX = re.compile("{guild\\.(name|id|members)}")
USER_FORMAT_REGEX = re.compile("{user\\.(name|id|mention|discriminator)}")


def format_welcome_message(message: str, member: Member):
    guild = member.guild

    try:
        return message.format(guild=guild, user=member)
    except KeyError:
        return message\
            .replace("{user}", str(member))\
            .replace("{user.name}", member.name)\
            .replace("{user.discriminator}", member.discriminator)\
            .replace("{user.id}", str(member.id)) \
            .replace("{guild.name}", guild.name) \
            .replace("{user.members}", str(guild.member_count)) \
            .replace("{guild.id}", str(guild.id))

