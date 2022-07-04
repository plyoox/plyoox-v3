from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import discord
from discord import utils
from discord.utils import MISSING

from lib import helper
from lib.enums import AutomodAction
from lib.extensions import Embed
from lib.types import AutomodExecutionReason
from lib.types.types import ModerationExecutedCommand
from translation import _

if TYPE_CHECKING:
    from main import Plyoox


async def _get_logchannel(bot: Plyoox, guild: discord.Guild) -> discord.Webhook | None:
    cache = await bot.cache.get_moderation(guild.id)

    if cache is None or not cache.active or cache.log_channel is None:
        return None

    return discord.Webhook.partial(cache.log_id, cache.log_token, session=bot.session)


async def _send_webhook(
    bot: Plyoox,
    guild_id: int,
    webhook: discord.Webhook,
    embed: discord.Embed = MISSING,
    embeds: list[discord.Embed] = MISSING,
) -> None:
    try:
        await webhook.send(embed=embed, embeds=embeds)
    except discord.Forbidden:
        await bot.db.execute(
            "UPDATE moderation SET log_channel = NULL, log_id = NULL, log_token = NULL WHERE id = $1",
            guild_id,
        )

        bot.cache.edit_cache("mod", guild_id, log_channel=None, log_id=None, log_token=None)


async def log_simple_punish_command(
    interaction: discord.Interaction,
    target: discord.Member,
    *,
    reason: str,
    type: ModerationExecutedCommand,
    until: datetime.datetime | None = None,
) -> None:
    webhook = await _get_logchannel(interaction.client, interaction.guild)  # type: ignore
    if webhook is None:
        return

    lc = interaction.guild_locale

    embed = Embed(description=_(lc, f"moderation.{type}.log_description", target=target, moderator=interaction.user))
    embed.set_author(name=_(lc, f"moderation.{type}.log_title"), icon_url=target.display_avatar)
    embed.add_field(name=_(lc, "reason"), value="> " + (reason or _(lc, "no_reason")))
    embed.add_field(name=_(lc, "executed_at"), value="> " + utils.format_dt(utils.utcnow()))
    embed.set_footer(text=f"{_(lc, 'id')}: {target.id}")

    if until is not None:
        embed.add_field(name=_(lc, "punished_until"), value=helper.embed_timestamp_format(until))

    await _send_webhook(interaction.client, interaction.guild.id, webhook, embed=embed)  # type: ignore


async def automod_log(
    bot: Plyoox,
    message: discord.Message,
    action: AutomodAction,
    type: AutomodExecutionReason,
    *,
    until: datetime.datetime | None = None,
    points: str | None = None,
) -> None:
    webhook = await _get_logchannel(bot, message.guild)
    if webhook is None:
        return

    lc = message.guild.preferred_locale
    member = message.author

    embeds = []

    embed = Embed(description=_(lc, f"automod.{action}.description", target=member))
    embed.set_author(name=_(lc, f"automod.{action}.title"), icon_url=member.display_avatar)
    embed.add_field(name=_(lc, "reason"), value="> " + _(lc, f"automod.reason.{type}"))
    embed.add_field(name=_(lc, "executed_at"), value="> " + utils.format_dt(utils.utcnow()))
    embed.set_footer(text=f"{_(lc, 'id')}: {member.id}")

    if until is not None:
        embed.add_field(name=_(lc, "punished_until"), value=helper.embed_timestamp_format(until))
    elif points is not None:
        embed.add_field(name=_(lc, "automod.points_added"), value="> " + points)

    embeds.append(embed)

    if message.content:
        if len(message.content) <= 1024:
            embed.add_field(name=_(lc, "message"), value=message.content)
        else:
            message_embed = Embed(title=_(lc, "message"), description=message.content)
            embeds.append(message_embed)

    await _send_webhook(bot, message.guild.id, webhook, embeds=embeds)
