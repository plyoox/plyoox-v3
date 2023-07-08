from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import discord
from discord import utils

from lib import helper, extensions
from lib.enums import AutomodFinalActionEnum
from translation import _

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

    webhook = await _get_logchannel(interaction.client, cache, interaction.guild)
    if webhook is not None:
        lc = interaction.guild_locale

        embed = extensions.Embed(
            description=_(lc, f"moderation.{kind}.log_description", target=target, moderator=interaction.user)
        )
        embed.set_author(name=_(lc, f"moderation.{kind}.log_title"), icon_url=target.display_avatar)
        embed.add_field(name=_(lc, "reason"), value="> " + (reason or _(lc, "no_reason")))
        embed.add_field(name=_(lc, "executed_at"), value="> " + utils.format_dt(utils.utcnow()))
        embed.set_footer(text=f"{_(lc, 'id')}: {target.id}")

        if until is not None:
            embed.add_field(name=_(lc, "punished_until"), value=helper.embed_timestamp_format(until))

        await _send_webhook(interaction.client, interaction.guild.id, webhook, embed=embed)  # type: ignore

    if cache.notify_user and isinstance(target, discord.Member):
        lc = interaction.locale

        try:
            await target.send(
                _(
                    lc,
                    f"moderation.{kind}.user_message",
                    reason=reason or _(lc, "no_reason"),
                    timestamp=discord.utils.format_dt(until) if until is not None else None,
                    guild=interaction.guild,
                )
            )
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
    guild = member.guild
    lc = guild.preferred_locale

    cache = await bot.cache.get_moderation(guild.id)
    if cache is None or not cache.active:
        return

    webhook = await _get_logchannel(bot, cache, guild)
    if webhook is not None:
        embed = extensions.Embed(description=_(lc, f"automod.final.description", target=member))
        embed.set_author(name=_(lc, f"automod.final.title"), icon_url=member.display_avatar)
        embed.add_field(name=_(lc, "automod.final.action"), value=f"> {_(lc, f'moderation.{action}.log_title')}")
        embed.add_field(name=_(lc, "executed_at"), value="> " + utils.format_dt(utils.utcnow()))
        embed.set_footer(text=f"{_(lc, 'id')}: {member.id}")

        if until is not None:
            embed.add_field(name=_(lc, "punished_until"), value=helper.embed_timestamp_format(until))

        await _send_webhook(bot, guild.id, webhook, embed=embed)

    if cache.notify_user:
        try:
            await member.send(
                _(
                    lc,
                    f"automod.{action}.user_message",
                    reason=_(lc, f"automod.reason.points"),
                    timestamp=discord.utils.format_dt(until) if until is not None else None,
                    guild=guild,
                )
            )
        except discord.Forbidden:
            pass


async def warn_log(bot: Plyoox, member: discord.Member, moderator: discord.Member, reason: str, points: str) -> None:
    guild = member.guild
    lc = guild.preferred_locale

    cache = await bot.cache.get_moderation(guild.id)
    if cache is None or not cache.active:
        return

    webhook = await _get_logchannel(bot, cache, guild)
    if webhook is not None:
        embed = extensions.Embed(description=_(lc, "moderation.warn.description", target=member, moderator=moderator))
        embed.set_author(name=_(lc, "moderation.warn.title"), icon_url=member.display_avatar)
        embed.add_field(name=_(lc, "reason"), value=f"> {reason}")
        embed.add_field(name=_(lc, "moderation.moderator"), value=f"> {moderator.mention} ({moderator.id})")
        embed.add_field(name=_(lc, "executed_at"), value="> " + utils.format_dt(utils.utcnow()))
        embed.set_footer(text=f"{_(lc, 'id')}: {member.id}")
        embed.add_field(name=_(lc, "automod.points_added"), value=f"> {points}")

        await _send_webhook(bot, guild.id, webhook, embed=embed)

    if cache.notify_user:
        try:
            await member.send(_(lc, "moderation.warn.user_message", reason=reason, guild=guild, points=points))
        except discord.Forbidden:
            pass
