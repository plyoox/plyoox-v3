from __future__ import annotations

from typing import TYPE_CHECKING

from discord import utils

from lib.colors import DISCORD_DEFAULT
from translation import _

if TYPE_CHECKING:
    import discord
    from main import Plyoox


async def _get_logchannel(interaction: discord.Interaction) -> discord.TextChannel | None:
    bot: Plyoox = interaction.client  # type: ignore
    guild = interaction.guild
    cache = await bot.cache.get_moderation(guild.id)

    if cache is None or not cache.active or cache.logchannel is None:
        return

    channel = guild.get_channel(cache.logchannel)
    if channel is not None and channel.permissions_for(guild.me).send_messages:
        return channel


async def log_ban(interaction: discord.Interaction, *, target: discord.Member, reason: str | None) -> None:
    logchannel = await _get_logchannel(interaction)
    if logchannel is None:
        return

    lc = interaction.guild_locale

    embed = discord.Embed(color=DISCORD_DEFAULT)
    embed.set_author(name=_(lc, "moderation.logging.ban"), icon_url=target.display_avatar)
    embed.description = _(lc, "moderation.logging.ban_description", target=target, moderator=interaction.user)
    embed.add_field(name=_(lc, "reason"), value=reason or _(lc, "no_reason"))
    embed.add_field(name=_(lc, "timestamp"), value=utils.format_dt(utils.utcnow(), "F"))
    embed.set_footer(text=f"{_(lc, 'id')}: {target.id}")

    await logchannel.send(embed=embed)


async def log_kick(interaction: discord.Interaction, *, target: discord.Member, reason: str | None) -> None:
    logchannel = await _get_logchannel(interaction)
    if logchannel is None:
        return

    lc = interaction.guild_locale

    embed = discord.Embed(color=DISCORD_DEFAULT)
    embed.set_author(name=_(lc, "moderation.logging.kick"), icon_url=target.display_avatar)
    embed.description = _(lc, "moderation.logging.kick_description", target=target, moderator=interaction.user)
    embed.add_field(name=_(lc, "reason", reason=reason), value=reason or _(lc, "no_reason"))
    embed.add_field(name=_(lc, "timestamp"), value=utils.format_dt(utils.utcnow(), "F"))
    embed.set_footer(text=f"{_(lc, 'id')}: {target.id}")
