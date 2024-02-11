from __future__ import annotations

import datetime
import io
import logging
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.app_commands import locale_str as _

from lib import helper, extensions, types, colors
from lib.helper import italic
from translation.translator import translate as global_translate

if TYPE_CHECKING:
    from main import Plyoox
    from cache.models import ModerationModel
    from .automod import AutoModerationActionData
    from lib.enums import ModerationCommandKind, AutoModerationFinalPunishmentKind, AutoModerationPunishmentKind

_log = logging.getLogger(__name__)


async def _get_log_channel(
    bot: Plyoox, cache: ModerationModel, guild: discord.Guild
) -> discord.Webhook | discord.TextChannel | None:
    if cache.logging_channel is None:
        return None

    if cache.logging_channel.webhook_channel is not None:
        return discord.Webhook.partial(cache.logging_channel.id, cache.logging_channel.token, session=bot.session)

    channel = guild.get_channel(cache.logging_channel.id)
    if channel is None or not channel.permissions_for(guild.me).send_messages:
        _log.info(f"Cannot send log message to {cache.logging_channel.id} ({repr(channel)})")

        # Remove the channel from the database
        await bot.db.execute(
            "DELETE FROM maybe_webhook WHERE id = $1 AND guild_id = $2",
            cache.logging_channel.id,
            guild.id,
        )

        # Remove the channel from the cache
        # Moderation and Logging config can have the same webhook,
        # so it needs to be removed from both
        bot.cache.edit_cache(guild.id, "mod", logging_channel=None)
        bot.cache.remove_cache(guild.id, "log")

    return channel


async def _send_webhook(
    bot: Plyoox,
    guild_id: int,
    webhook: discord.Webhook,
    embeds: list[discord.Embed] = utils.MISSING,
    files: list[discord.File] = utils.MISSING,
) -> None:
    try:
        await webhook.send(embeds=embeds, files=files)
    except discord.NotFound:
        _log.info(f"Log channel {webhook.id} not found, deleting...")
        await bot.db.execute("DELETE FROM maybe_webhook WHERE id = $1 AND guild_id = $2", webhook.id, guild_id)

        # Remove the channel from the cache
        # Moderation and Logging config can have the same webhook,
        # so it needs to be removed from both
        bot.cache.edit_cache(guild_id, "mod", logging_channel=None)
        bot.cache.remove_cache(guild_id, "log")
    except discord.HTTPException as e:
        _log.error(f"Error while sending log message in {webhook.id} ({type(webhook)}): {e}")


async def log_simple_punish_command(
    interaction: discord.Interaction,
    target: discord.User | discord.Member,
    *,
    reason: str,
    kind: ModerationCommandKind,
    until: datetime.datetime | None = None,
) -> None:
    cache: ModerationModel = await interaction.client.cache.get_moderation(interaction.guild.id)
    if cache is None or not cache.active:
        return

    translate = interaction.translate

    notified_user = None
    if cache.notify_user and isinstance(target, discord.Member):
        until_fmt = discord.utils.format_dt(until) if until else None
        embed = _get_dynamic_log_user_message(
            interaction.translate, kind=kind, reason=reason, timestamp=until_fmt, guild=interaction.guild
        )

        try:
            await target.send(embeds=[embed])
            notified_user = True
        except discord.Forbidden:
            notified_user = False

    webhook = await _get_log_channel(interaction.client, cache, interaction.guild)
    if webhook is None:
        return

    title, description = _get_dynamic_log_description(translate, moderator=interaction.user, target=target, kind=kind)

    embed = extensions.Embed(description=description, color=colors.COMMAND_LOG_COLOR)
    embed.set_author(name=title, icon_url=target.display_avatar)
    embed.add_field(name=translate(_("Reason")), value=f"> {reason}" if reason else italic(translate(_("No reason"))))
    embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()), inline=True)
    embed.set_footer(text=f"{translate(_('User Id'))}: {target.id}")

    if until is not None:
        embed.add_field(name=translate(_("Punished until")), value=helper.embed_timestamp_format(until), inline=True)

    if notified_user is not None:
        embed.add_field(
            name=translate(_("Received DM")), value="> " + translate(_("Yes") if notified_user else _("No"))
        )

    await _send_webhook(interaction.client, interaction.guild.id, webhook, embeds=[embed])


async def log_clear_command(
    interaction: discord.Interaction, *, reason: str | None, total: int, deleted_messages: list[discord.Message]
) -> None:
    cache = await interaction.client.cache.get_moderation(interaction.guild.id)
    if cache is None or not cache.active:
        return

    translate = interaction.translate

    webhook = await _get_log_channel(interaction.client, cache, interaction.guild)
    if webhook is None:
        return

    deleted_count = len(deleted_messages)

    embed = extensions.Embed(
        description=translate(
            _("{deleted_count} messages have been deleted from {channel} by {moderator.mention} ({moderator})."),
            data={
                "deleted_count": deleted_count,
                "channel": interaction.channel.mention,
                "moderator": interaction.user,
            },
        ),
        color=colors.COMMAND_LOG_COLOR,
    )
    embed.set_author(name=translate(_("Messages cleared")), icon_url=interaction.user.display_avatar)
    embed.set_footer(text=f"{translate(_('Channel Id'))}: {interaction.channel_id}")

    embed.add_field(name=translate(_("Deleted Messages")), value=f"> {deleted_count}/{total}")
    embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()))

    if reason is not None:
        embed.insert_field_at(0, name=translate(_("Reason")), value=f"> {reason}")

    file = None
    if len(deleted_messages):
        messages = [f"{msg.author} ({msg.author.id}):\t{msg.content}" for msg in deleted_messages if msg.content]

        if len(messages) > 0:
            _file = io.BytesIO()
            _file.write("\n".join([msg for msg in messages]).encode("utf-8"))
            _file.seek(0)

            file = discord.File(_file, filename="cleared_messages.txt")

    await _send_webhook(interaction.client, interaction.guild.id, webhook, embeds=[embed], files=[file])


async def automod_log(
    bot: Plyoox,
    data: AutoModerationActionData,
    *,
    until: datetime.datetime | None = None,
    points: str | None = None,
) -> None:
    def translate(string: _):
        return global_translate(string, bot, guild.preferred_locale)

    guild = data.guild
    member = data.member

    cache = await bot.cache.get_moderation(guild.id)
    if not cache:
        return

    notified_user = None
    if cache.notify_user:
        timestamp = utils.format_dt(until) if until is not None else None
        embed = _get_dynamic_log_user_message(
            translate,
            guild=guild,
            reason=data.trigger_reason,
            timestamp=timestamp,
            kind=data.trigger_action.punishment.kind,
            points=points,
        )

        try:
            await member.send(embed=embed)
            notified_user = True
        except discord.Forbidden:
            notified_user = False

    webhook = await _get_log_channel(bot, cache, guild)
    if webhook is None:
        return

    if data.moderator:
        title, description = _get_dynamic_log_description(
            translate, moderator=data.moderator, target=member, kind=data.trigger_action.punishment.kind
        )
    else:
        (title, description) = _get_dynamic_auto_moderation_description(
            translate, kind=data.trigger_action.punishment.kind, target=member
        )

    embeds = []

    embed = extensions.Embed(description=description)
    embed.set_author(name=title, icon_url=member.display_avatar)
    embed.add_field(name=translate(_("Reason")), value=f"> {data.trigger_reason}")
    embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()), inline=True)
    embed.set_footer(text=f"{translate(_('User Id'))}: {member.id}")

    # data.moderator is only set when executed by the punishment command
    if data.moderator:
        embed.title = translate(_("Punishment executed"))
        embed.color = colors.PUNISHMENT_COLOR
    else:
        embed.color = colors.AUTOMOD_COLOR

    if until is not None:
        embed.add_field(name=translate(_("Punished until")), value=helper.embed_timestamp_format(until), inline=True)
    elif points is not None:
        embed.add_field(name=translate(_("Points added")), value="> " + points)

    if notified_user is not None:
        embed.add_field(
            name=translate(_("Received DM")), value="> " + translate(_("Yes") if notified_user else _("No"))
        )

    embeds.append(embed)

    if data.trigger_content:
        if len(data.trigger_content) <= 1024:
            embed.add_field(name=translate(_("Message")), value=data.trigger_content)
        else:
            message_embed = extensions.Embed(
                title=translate(_("Message")),
                description=data.trigger_content,
                color=colors.AUTOMOD_COLOR,
            )
            embeds.append(message_embed)

    await _send_webhook(bot, guild.id, webhook, embeds=embeds)


async def automod_final_log(
    bot: Plyoox,
    member: discord.Member,
    action: AutoModerationFinalPunishmentKind,
    *,
    until: datetime.datetime | None = None,
) -> None:
    def translate(string: _):
        return global_translate(string, bot, guild.preferred_locale)

    guild = member.guild

    cache = await bot.cache.get_moderation(guild.id)
    if cache is None or not cache.active:
        return

    notified_user = None
    if cache.notify_user:
        embed = _get_dynamic_log_user_message(
            translate,
            guild=guild,
            reason=translate(_("Maximum amount of points reached")),
            timestamp=discord.utils.format_dt(until) if until else None,
            kind=action,
        )

        try:
            await member.send(embeds=[embed])
            notified_user = True
        except discord.Forbidden:
            notified_user = False

    webhook = await _get_log_channel(bot, cache, guild)
    if webhook is None:
        return

    (title, _description) = _get_dynamic_auto_moderation_description(translate, kind=action, target=member)

    embed = extensions.Embed(
        description=translate(
            _("The user {target.mention} ({target}) has reached the maximum number of points.")
        ).format(target=member),
        color=colors.AUTOMOD_COLOR,
    )
    embed.set_author(name=translate(_("Automod: Maximum points reached")), icon_url=member.display_avatar)
    embed.add_field(name=translate(_("Action")), value=f"> {title}")
    embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()), inline=True)
    embed.set_footer(text=f"{translate(_('User Id'))}: {member.id}")

    if until is not None:
        embed.add_field(name=translate(_("Punished until")), value=helper.embed_timestamp_format(until), inline=True)

    if notified_user is not None:
        embed.add_field(
            name=translate(_("Received DM")), value="> " + translate(_("Yes") if notified_user else _("No"))
        )

    await _send_webhook(bot, guild.id, webhook, embeds=[embed])


async def warn_log(bot: Plyoox, member: discord.Member, moderator: discord.Member, reason: str, points: str) -> None:
    def translate(string: _):
        return global_translate(string, bot, guild.preferred_locale)

    guild = member.guild

    cache = await bot.cache.get_moderation(guild.id)
    if cache is None or not cache.active:
        return

    notified_user = None
    if cache.notify_user:
        try:
            embed = _get_dynamic_log_user_message(
                translate,
                guild=guild,
                reason=reason,
                kind=AutoModerationPunishmentKind.point,
                points=points,
                timestamp=None,
            )

            await member.send(
                embed=embed,
            )
            notified_user = True
        except discord.Forbidden:
            notified_user = False

    webhook = await _get_log_channel(bot, cache, guild)
    if webhook is None:
        return

    embed = extensions.Embed(
        description=translate(_("The user {target} ({target.id}) has been warned by {moderator}.")).format(
            target=member, moderator=moderator
        ),
        color=colors.POINT_COLOR,
    )
    embed.set_author(name=translate(_("User has been warned")), icon_url=member.display_avatar)
    embed.add_field(name=translate(_("Reason")), value=f"> {reason}")
    embed.add_field(name=translate(_("Moderator")), value=f"> {moderator} ({moderator.id})")
    embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()))
    embed.add_field(name=translate(_("Points added")), value=f"> {points}")
    embed.set_footer(text=f"{translate(_('User Id'))}: {member.id}")

    if notified_user is not None:
        embed.add_field(
            name=translate(_("Received DM")), value="> " + translate(_("Yes") if notified_user else _("No"))
        )

    await _send_webhook(bot, guild.id, webhook, embeds=[embed])


def _get_dynamic_log_description(
    translate: types.Translate,
    *,
    moderator: discord.Member | None,
    target: discord.User | discord.Member,
    kind: ModerationCommandKind | AutoModerationPunishmentKind,
) -> (str, str):
    match kind:
        case "point":
            return (
                translate(_("User has reached the maximum number of points")),
                translate(_("The user {target.mention} ({target}) has reached the maximum number of points.")).format(
                    target=target
                ),
            )
        case "delete":
            return (
                translate(_("Message has been deleted")),
                translate(
                    _(
                        "The message from {target.mention} ({target}) has been deleted by {moderator.mention} ({moderator})."
                    )
                ).format(target=target, moderator=moderator),
            )
        case "tempban":
            return (
                translate(_("User has been temporary banned")),
                translate(
                    _(
                        "The user {target.mention} ({target}) has been temporarily banned by {moderator.mention} ({moderator})."
                    )
                ).format(target=target, moderator=moderator),
            )
        case "ban":
            return (
                translate(_("User has been banned")),
                translate(
                    _("The user {target.mention} ({target}) has been banned by {moderator.mention} ({moderator}).")
                ).format(target=target, moderator=moderator),
            )
        case "tempmute":
            return (
                translate(_("User has been temporary muted")),
                translate(
                    _(
                        "The user {target.mention} ({target}) has been temporarily muted by {moderator.mention} ({moderator})."
                    )
                ).format(target=target, moderator=moderator),
            )
        case "kick":
            return (
                translate(_("User has been kicked")),
                translate(
                    _("The user {target.mention} ({target}) has been kicked by {moderator.mention} ({moderator}).")
                ).format(target=target, moderator=moderator),
            )
        case "unban":
            return (
                translate(_("User has been unbanned")),
                translate(
                    _("The user {target.mention} ({target}) has been unbanned by {moderator.mention} ({moderator}).")
                ).format(target=target, moderator=moderator),
            )
        case "softban":
            return (
                translate(_("User has been softbanned")),
                translate(
                    _("The user {target.mention} ({target}) has been softbanned by {moderator.mention} ({moderator}).")
                ).format(target=target, moderator=moderator),
            )
        case "unmute":
            return (
                translate(_("User has been unmuted")),
                translate(
                    _("The user {target.mention} ({target}) has been unmuted by {moderator.mention} ({moderator}).")
                ).format(target=target, moderator=moderator),
            )


def _get_dynamic_auto_moderation_description(
    translate: types.Translate,
    *,
    target: discord.User | discord.Member,
    kind: AutoModerationFinalPunishmentKind | AutoModerationPunishmentKind,
) -> (str, str):
    match kind:
        case "point":
            return (
                translate(_("User has reached the maximum number of points")),
                translate(_("The user {target.mention} ({target}) has reached the maximum number of points.")).format(
                    target=target
                ),
            )
        case "delete":
            return (
                translate(_("Message has been deleted")),
                translate(
                    _("The message from {target.mention} ({target}) has been deleted by the automoderation system.")
                ).format(target=target),
            )
        case "tempban":
            return (
                translate(_("User has been temporary banned")),
                translate(
                    _("The user {target.mention} ({target}) has been temporarily banned by the automoderation system.")
                ).format(target=target),
            )
        case "ban":
            return (
                translate(_("User has been banned")),
                translate(
                    _("The user {target.mention} ({target}) has been banned by the automoderation system.")
                ).format(target=target),
            )
        case "tempmute":
            return (
                translate(_("User has been temporary muted")),
                translate(
                    _("The user {target.mention} ({target}) has been temporarily muted the automoderation system.")
                ).format(target=target),
            )
        case "kick":
            return (
                translate(_("User has been kicked")),
                translate(
                    _("The user {target.mention} ({target}) has been kicked by the automoderation system.")
                ).format(target=target),
            )


def _get_dynamic_log_user_message(
    translate: types.Translate,
    *,
    guild: discord.Guild,
    kind: ModerationCommandKind | AutoModerationFinalPunishmentKind | AutoModerationPunishmentKind,
    reason: str,
    timestamp: str | None,
    points: str | None = None,
) -> discord.Embed:
    embed = extensions.Embed()
    embed.set_author(icon_url=guild.icon.url, name=guild.name)
    embed.set_footer(text=f"{translate(_('Guild Id'))}: {guild.id}")

    if reason:
        embed.add_field(name=translate(_("Reason")), value=f"> {reason}")

    match kind:
        case "tempban":
            embed.title = translate(_("Temporary Ban"))
            embed.description = translate(_("You have been temporarily banned."))

            embed.insert_field_at(0, name=translate(_("Punished until")), value=f"> {timestamp}")

            return embed
        case "ban":
            embed.title = translate(_("Permanent Ban"))
            embed.description = translate(_("You have been permanently banned."))

            return embed
        case "tempmute":
            embed.title = translate(_("Temporary Mute"))
            embed.description = translate(_("You have been temporarily muted."))

            embed.insert_field_at(0, name=translate(_("Punished until")), value=f"> {timestamp}")

            return embed
        case "kick" | "softban":
            embed.title = translate(_("Kick"))
            embed.description = translate(_("You have been kicked."))

            return embed
        case "unmute":
            embed.title = translate(_("Unmute"))
            embed.description = translate(_("You have been unmuted."))

            return embed
        case "delete":
            embed.title = translate(_("Message deleted"))
            embed.description = translate(_("A message has been deleted."))

            return embed
        case "point":
            embed.title = translate(_("Points received"))
            embed.description = translate(_("You have received points for your actions."))

            embed.insert_field_at(0, name=translate(_("Points")), value=f"> `{points}`")

            return embed
