from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.app_commands import locale_str as _

from lib import helper, extensions
from lib.enums import AutomodFinalActionEnum
from translation.translator import translate as global_translate

if TYPE_CHECKING:
    from main import Plyoox
    from cache.models import ModerationModel
    from lib.types import ModerationExecutedCommand
    from .automod import AutomodActionData


_log = logging.getLogger(__name__)


async def _get_logchannel(
    bot: Plyoox, cache: ModerationModel, guild: discord.Guild
) -> discord.Webhook | discord.TextChannel | None:
    if cache.log_channel is None:
        return None

    if cache.log_id is None:
        channel = guild.get_channel(cache.log_channel)
        if channel is not None and channel.permissions_for(guild.me).send_messages:
            return channel

        return None

    return discord.Webhook.partial(cache.log_id, cache.log_token, session=bot.session)


async def _send_webhook(
    bot: Plyoox,
    guild_id: int,
    webhook: discord.Webhook,
    embed: discord.Embed = utils.MISSING,
    embeds: list[discord.Embed] = utils.MISSING,
) -> None:
    try:
        await webhook.send(embed=embed, embeds=embeds)
        return
    except discord.Forbidden:
        _log.info(f"Not allowed to send log message in {webhook.id} ({type(webhook)})")
    except discord.NotFound:
        _log.info(f"Log channel {webhook.id} ({type(webhook)}) not found")
    except discord.HTTPException as e:
        _log.error(f"Error while sending log message in {webhook.id} ({type(webhook)}): {e}")

    await bot.db.execute(
        "UPDATE moderation SET log_channel = NULL, log_id = NULL, log_token = NULL WHERE id = $1",
        guild_id,
    )

    bot.cache.edit_cache(guild_id, "mod", log_channel=None, log_id=None, log_token=None)


async def log_simple_punish_command(
    interaction: discord.Interaction,
    target: discord.User | discord.Member,
    *,
    reason: str,
    kind: ModerationExecutedCommand,
    until: datetime.datetime | None = None,
) -> None:
    cache: ModerationModel = await interaction.client.cache.get_moderation(interaction.guild.id)  # type: ignore
    if cache is None or not cache.active:
        return

    translate = interaction.translate
    webhook = await _get_logchannel(interaction.client, cache, interaction.guild)
    if webhook is not None:
        title, description = _get_dynamic_log_description(interaction, kind, target)

        embed = extensions.Embed(description=description)
        embed.set_author(name=title, icon_url=target.display_avatar)
        embed.add_field(name=translate(_("Reason")), value="> " + (reason or translate(_("No reason"))))
        embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()))
        embed.set_footer(text=f"{translate(_("Id"))}: {target.id}")

        if until is not None:
            embed.add_field(name=translate(_("Punished until")), value=helper.embed_timestamp_format(until))

        await _send_webhook(interaction.client, interaction.guild.id, webhook, embed=embed)  # type: ignore

    if cache.notify_user and isinstance(target, discord.Member):
        reason = reason or f"*{translate(_("No reason"))}*"
        until = discord.utils.format_dt(until) if until else None
        message = _get_dynamic_log_user_message(interaction, kind, reason, until)

        try:
            await target.send(message)
        except discord.Forbidden:
            pass


async def automod_log(
    bot: Plyoox,
    data: AutomodActionData,
    *,
    until: datetime.datetime | None = None,
    points: str | None = None,
) -> None:
    guild = data.guild
    member = data.member
    lc = guild.preferred_locale

    cache = await bot.cache.get_moderation(guild.id)
    if cache is None:
        return

    webhook = await _get_logchannel(bot, cache, guild)
    if webhook is not None:
        embeds = []

        embed = extensions.Embed(description=_(lc, f"automod.{data.trigger_action.action}.description", target=member))
        embed.set_author(name=_(lc, f"automod.{data.trigger_action.action}.title"), icon_url=member.display_avatar)
        embed.add_field(name=_(lc, "reason"), value=f"> {data.trigger_reason}")
        embed.add_field(name=_(lc, "executed_at"), value="> " + utils.format_dt(utils.utcnow()))
        embed.set_footer(text=f"{_(lc, 'id')}: {member.id}")

        if until is not None:
            embed.add_field(name=_(lc, "punished_until"), value=helper.embed_timestamp_format(until))
        elif points is not None:
            embed.add_field(name=_(lc, "automod.points_added"), value="> " + points)

        embeds.append(embed)

        if data.trigger_content:
            if len(data.trigger_content) <= 1024:
                embed.add_field(name=_(lc, "message"), value=data.trigger_content)
            else:
                message_embed = extensions.Embed(title=_(lc, "message"), description=data.trigger_content)
                embeds.append(message_embed)

        await _send_webhook(bot, guild.id, webhook, embeds=embeds)

    if cache.notify_user:
        try:
            await member.send(
                _(
                    lc,
                    f"automod.{data.trigger_action.action}.user_message",
                    reason=data.trigger_reason,
                    timestamp=discord.utils.format_dt(until) if until is not None else None,
                    guild=guild,
                    points=points,
                )
            )
        except discord.Forbidden:
            pass


async def automod_final_log(
    bot: Plyoox,
    member: discord.Member,
    action: AutomodFinalActionEnum,
    *,
    until: datetime.datetime | None = None,
) -> None:
    def translate(str: _):
        return global_translate(str, bot, guild.preferred_locale)

    guild = member.guild

    cache = await bot.cache.get_moderation(guild.id)
    if cache is None or not cache.active:
        return

    webhook = await _get_logchannel(bot, cache, guild)
    if webhook is not None:
        (title,) = _get_dynamic_log_description(bot, action, member)

        embed = extensions.Embed(
            description=translate(
                _("The user {target.mention} ({target}) has reached the maximum number of points.")
            ).format(target=member)
        )
        embed.set_author(name=translate(_("Automod: Maximum points reached")), icon_url=member.display_avatar)
        embed.add_field(name=translate(_("Action")), value=f"> {title}")
        embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()))
        embed.set_footer(text=f"{translate(_("Id"))}: {member.id}")

        if until is not None:
            embed.add_field(name=translate(_("Punished until")), value=helper.embed_timestamp_format(until))

        await _send_webhook(bot, guild.id, webhook, embed=embed)

    if cache.notify_user:
        until = discord.utils.format_dt(until) if until is not None else None
        message = _get_dynamic_log_user_message(
            translate, guild, reason=translate(_("Maximum amount of points reached")), timestamp=until
        )

        try:
            await member.send(message)
        except discord.Forbidden:
            pass


async def warn_log(bot: Plyoox, member: discord.Member, moderator: discord.Member, reason: str, points: str) -> None:
    def translate(str: _):
        return global_translate(str, bot, guild.preferred_locale)

    guild = member.guild

    cache = await bot.cache.get_moderation(guild.id)
    if cache is None or not cache.active:
        return

    webhook = await _get_logchannel(bot, cache, guild)

    if webhook is not None:
        embed = extensions.Embed(
            description=translate(_("The user {target} ({target.id}) has been warned by {moderator}.")).format(
                target=member, moderator=moderator
            )
        )
        embed.set_author(name=translate(_("User has been warned")), icon_url=member.display_avatar)
        embed.add_field(name=translate(_("Reason")), value=f"> {reason}")
        embed.add_field(name=translate(_("Moderator")), value=f"> {moderator} ({moderator.id})")
        embed.add_field(name=translate(_("Executed at")), value="> " + utils.format_dt(utils.utcnow()))
        embed.set_footer(text=f"{translate(_("Id"))}: {member.id}")
        embed.add_field(name=translate(_("Points added")), value=f"> {points}")

        await _send_webhook(bot, guild.id, webhook, embed=embed)

    if cache.notify_user:
        try:
            await member.send(
                translate(
                    _("You have been warned in `{guild.name}` for **{reason}** and now have `{points}` points.")
                ).format(reason=reason, guild=guild, points=points)
            )
        except discord.Forbidden:
            pass


def _get_dynamic_log_description(
    interaction: discord.Interaction, kind: ModerationExecutedCommand, target: discord.User
) -> (str, str):
    translate = interaction.translate

    match kind:
        case "tempban":
            return (
                translate(_("User has been temporary banned")),
                translate(_("The user {target.mention} ({target}) has been temporarily banned by {moderator}.")).format(
                    target=target, moderator=interaction.user
                ),
            )
        case "ban":
            return (
                translate(_("User has been banned")),
                translate(_("The user {target.mention} ({target}) has been banned by {moderator}.")).format(
                    target=target, moderator=interaction.user
                ),
            )
        case "tempmute":
            return (
                translate(_("User has been temporary muted")),
                translate(_("The user {target.mention} ({target}) has been temporarily muted by {moderator}.")).format(
                    target=target, moderator=interaction.user
                ),
            )
        case "kick":
            return (
                translate(_("User has been kicked")),
                translate(_("The user {target.mention} ({target}) has been kicked by {moderator}.")).format(
                    target=target, moderator=interaction.user
                ),
            )
        case "unban":
            return (
                translate(_("User has been unbanned")),
                translate(_("The user {target.mention} ({target}) has been unbanned by {moderator}.")).format(
                    target=target, moderator=interaction.user
                ),
            )
        case "softban":
            return (
                translate(_("User has been softbanned")),
                translate(_("The user {target.mention} ({target}) has been softbanned by {moderator}.")).format(
                    target=target, moderator=interaction.user
                ),
            )
        case "unmute":
            return (
                translate(_("User has been unmuted")),
                translate(_("The user {target.mention} ({target}) has been unmuted by {moderator}.")).format(
                    target=target, moderator=interaction.user
                ),
            )


def _get_dynamic_log_user_message(
    interaction: discord.Interaction, kind: ModerationExecutedCommand, reason: str, timestamp: str | None
) -> str:
    translate = interaction.translate

    match kind:
        case "tempban":
            return translate(_("You have been banned from {guild.name} until {timestamp} for {reason}.")).format(
                guild=interaction.guild, reason=reason, timestamp=timestamp
            )
        case "ban":
            return translate(_("You have been banned from {guild.name} for {reason}.")).format(
                guild=interaction.guild, reason=reason
            )
        case "tempmute":
            return translate(_("You have been muted from {guild.name} until {timestamp} for {reason}.")).format(
                guild=interaction.guild, reason=reason, timestamp=timestamp
            )
        case "kick":
            return translate(_("You have been kicked from {guild.name} for {reason}.")).format(
                guild=interaction.guild, reason=reason
            )
        case "softban":
            return translate(_("You have been kicked from {guild.name} for {reason}.")).format(
                guild=interaction.guild, reason=reason
            )
        case "unmute":
            return translate(_("You have been unmuted from {guild.name} for {reason}.")).format(
                guild=interaction.guild, reason=reason
            )
