from typing import Union

import discord

from translation import _


async def interaction_send(interaction: discord.Interaction, key: str, ephemeral=True):
    """Responds to an interaction with a locale string as ephemeral. This is mostly used to respond to errors."""
    await interaction.response.send_message(_(interaction.locale, key), ephemeral=ephemeral)


async def permission_check(
    channel: Union[discord.TextChannel, discord.VoiceChannel, discord.Thread],
    content: str = None,
    embeds: list[discord.Embed] = None,
):
    """Only sends the message if the bot has the permission to send messages in the channel."""
    if channel is None:
        return

    me = channel.guild.me

    if channel.permissions_for(me).send_messages:
        await channel.send(content=content, embeds=embeds)
