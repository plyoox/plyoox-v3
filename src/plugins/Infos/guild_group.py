from __future__ import annotations

import discord
from discord import app_commands

from lib import helper, extensions
from translation import _


_T = app_commands.locale_str


class GuildGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name=_T("guild-info", key="guild-info.name"),
            description=_T(
                "Provides information about a guild or guild specific information.", key="guild-info.description"
            ),
            guild_only=True,
        )

    @app_commands.command(
        name=_T("about", key="guild-info.about.name"),
        description=_T("Displays general information about the current guild.", key="guild-info.about.description"),
    )
    async def about(self, interaction: discord.Interaction):
        """This command shows basic information about the current guild."""
        lc = interaction.locale
        guild = interaction.guild
        roles = guild.roles

        embed = extensions.Embed(title=_(lc, "guild_info.about.title"))
        embed.set_thumbnail(url=guild.icon)
        embed.add_field(
            name=_(lc, "guild_info.about.general_information"),
            value=f"> __{_(lc, 'name')}:__ {guild.name}\n"
            f"> __{_(lc, 'id')}:__ {guild.id}\n"
            f"> __{_(lc, 'guild_info.about.owner')}:__ {guild.owner}\n"
            f"> __{_(lc, 'created_at')}:__ {discord.utils.format_dt(guild.created_at)}",
        )
        embed.add_field(name=_(lc, "guild_info.about.members"), value=f"> {str(guild.member_count)}")

        embed.add_field(name=_(lc, "roles"), value=f"> {helper.format_roles(roles) or _(lc, 'no_roles')}")
        embed.add_field(
            name=_(lc, "guild_info.about.more_infos"),
            value=f"> __{_(lc, 'guild_info.about.premium_level')}:__ {guild.premium_tier} ({guild.premium_subscription_count})\n"
            f"> __{_(lc, 'guild_info.about.vanity_url')}:__ {guild.vanity_url or _(lc, 'guild_info.about.no_vanity_url')}\n"
            f"> __{_(lc, 'guild_info.about.emojis')}:__ {len(guild.emojis)}/{guild.emoji_limit}\n"
            f"> __{_(lc, 'guild_info.about.stickers')}:__ {len(guild.stickers)}/{guild.sticker_limit}",
        )
        embed.add_field(
            name=_(lc, "guild_info.about.features"),
            value=f"> {', '.join(f'`{feature}`' for feature in guild.features) or _(lc, 'guild_info.about.no_features')}",
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name=_T("today-joined", key="guild-info.today-joined.name"),
        description=_T(
            "Shows how many members joined in the last 24 hours.", key="guild-info.today-joined.description"
        ),
    )
    async def today_joined(self, interaction: discord.Interaction):
        """Shows the amount of members that have joined in the last 24 hours. This does
        not include members that already left. This means, that this number does not represent
        an exact count on how many members the server gained or joined.
        """
        guild = interaction.guild
        lc = interaction.locale

        joined = 0

        for member in guild.members:
            if (discord.utils.utcnow() - member.joined_at).total_seconds() <= 86400:
                joined += 1

        embed = extensions.Embed(description=_(lc, "guild_info.today_joined", members=joined))

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name=_T("members", key="guild-info.members.name"),
        description=_T("Shows how many members are currently in the guild.", key="guild-info.members.description"),
    )
    async def members(self, interaction: discord.Interaction):
        """Returns the member count for the current guild."""
        guild = interaction.guild
        lc = interaction.locale

        embed = extensions.Embed(description=_(lc, "guild_info.members", members=guild.member_count))

        await interaction.response.send_message(embed=embed)
