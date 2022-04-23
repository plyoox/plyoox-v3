import discord

from utils import emojis


def format_roles(roles: list[discord.Role]) -> str | None:
    """Converts a list of roles to a string of mentions. If the result is longer than 1024 characters
    (limit of embed field) "..." is added to the end.
    """
    if len(roles) == 1:
        return None

    result = []
    roles.reverse()
    roles.pop()

    for role in roles[:44]:
        result.append(role.mention)

    if len(roles) > 44:
        return " ".join(result) + "..."

    return " ".join(result)


def get_badges(flags: discord.PublicUserFlags):
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

    return flag_list
