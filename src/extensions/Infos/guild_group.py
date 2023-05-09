from __future__ import annotations

import discord
from discord import app_commands

from lib import helper, extensions
from translation import _


class GuildGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="guild-info",
            description="Provides information about a guild or guild specific information.",
            guild_only=True,
        )

    @app_commands.command(name="about", description="Displays general information about the current guild.")
    async def about(self, interaction: discord.Interaction):
        """This command shows basic information about the current guild."""
        lc = interaction.locale
        guild = interaction.guild
        roles = guild.roles

        # Due to not chunking the guild, the owner might not be cached.
        if guild.owner is None:
            if (owner := interaction.client.get_user(guild.owner_id)) is None:
                # guild.query_members uses the gateway, so members are cached.
                queried_user = await guild.query_members(user_ids=[guild.owner_id])
                owner = queried_user[0] if queried_user else None
        else:
            owner = guild.owner

        embed = extensions.Embed(title=_(lc, "guild_info.about.title"))
        embed.set_thumbnail(url=guild.icon)
        embed.add_field(
            name=_(lc, "guild_info.about.general_information"),
            value=f"> __{_(lc, 'name')}:__ {guild.name}\n"
            f"> __{_(lc, 'id')}:__ {guild.id}\n"
            f"> __{_(lc, 'guild_info.about.owner')}:__ {owner}\n"
            f"> __{_(lc, 'created_at')}:__ {discord.utils.format_dt(guild.created_at)}",
        )
        embed.add_field(name=_(lc, "guild_info.about.members"), value=f"> {str(guild.member_count)}")

        embed.add_field(
            name=f"{_(lc, 'roles')} ({len(roles) - 1})",
            value=f"> {helper.format_roles(list(roles))}" if guild._roles else _(lc, "no_roles"),
        )
        embed.add_field(
            name=_(lc, "guild_info.about.more_infos"),
            value=f"> __{_(lc, 'guild_info.about.premium_level')}:__ {guild.premium_tier} ({guild.premium_subscription_count})\n"
            f"> __{_(lc, 'guild_info.about.vanity_url')}:__ {guild.vanity_url or _(lc, 'guild_info.about.no_vanity_url')}\n"
            f"> __{_(lc, 'guild_info.about.emojis')}:__ {len(guild.emojis)}/{guild.emoji_limit * 2}\n"  # normal + animated
            f"> __{_(lc, 'guild_info.about.stickers')}:__ {len(guild.stickers)}/{guild.sticker_limit}",
        )
        embed.add_field(
            name=_(lc, "guild_info.about.features"),
            value=f"> {', '.join(f'`{feature}`' for feature in guild.features)}"
            if guild.features
            else _(lc, "guild_info.about.no_features"),
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="today-joined", description="Shows how many members joined in the last 24 hours.")
    async def today_joined(self, interaction: discord.Interaction):
        """Shows the amount of members that have joined in the last 24 hours. This does
        not include members that already left. This means, that this number does not represent
        an exact count on how many members the server gained or joined.
        """
        guild = interaction.guild
        lc = interaction.locale

        if not guild.chunked:
            await guild.chunk(cache=True)

        joined = 0

        for member in guild.members:
            if (discord.utils.utcnow() - member.joined_at).total_seconds() <= 86400:
                joined += 1

        await interaction.response.send_message(_(lc, "guild_info.today_joined", members=joined))

    @app_commands.command(name="members", description="Shows how many members are currently in the guild.")
    async def members(self, interaction: discord.Interaction):
        """Returns the member count for the current guild."""
        guild = interaction.guild
        lc = interaction.locale

        await interaction.response.send_message(_(lc, "guild_info.members", members=guild.member_count))
