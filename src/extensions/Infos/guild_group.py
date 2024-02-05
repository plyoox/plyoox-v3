from __future__ import annotations

import discord
from discord import app_commands
from discord.app_commands import locale_str as _

from lib import helper, extensions


class GuildGroup(app_commands.Group):
    def __init__(self):
        super().__init__(
            name="guild-info",
            description=_("Provides information about a guild or guild specific information."),
            guild_only=True,
        )

    @app_commands.command(name="about", description=_("Displays general information about the current guild."))
    async def about(self, interaction: discord.Interaction):
        """This command shows basic information about the current guild."""
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

        embed = extensions.Embed(title=interaction.translate(_("Guild information")))
        embed.set_thumbnail(url=guild.icon)
        embed.add_field(
            name=interaction.translate(_("General information")),
            value=f"> __{interaction.translate(_('Name'))}:__ {guild.name}\n"
            f"> __{interaction.translate(_('Id'))}:__ {guild.id}\n"
            f"> __{interaction.translate(_('Owner'))}:__ {owner}\n"
            f"> __{interaction.translate(_('Created at'))}:__ {discord.utils.format_dt(guild.created_at)}",
        )

        embed.add_field(name=interaction.translate(_("Members")), value=f"> {str(guild.member_count)}")

        embed.add_field(
            name=f"{interaction.translate(_('Roles'))} ({len(roles) - 1})",
            value=f"> {helper.format_roles(list(roles))}" if guild._roles else _("No roles"),
        )
        embed.add_field(
            name=interaction.translate(_("More information")),
            value=f"> __{interaction.translate(_('Boost level'))}:__ {guild.premium_tier} ({guild.premium_subscription_count})\n"
            f"> __{interaction.translate(_('Vanity url'))}:__ {guild.vanity_url or interaction.translate(_('No vanity url'))}\n"
            f"> __{interaction.translate(_('Emojis'))}:__ {len(guild.emojis)}/{guild.emoji_limit * 2}\n"  # normal + animated
            f"> __{interaction.translate(_('Stickers'))}:__ {len(guild.stickers)}/{guild.sticker_limit}",
        )
        embed.add_field(
            name=interaction.translate(_("Features")),
            value=f"> {', '.join(f'`{feature}`' for feature in guild.features)}" if guild.features else _("No features"),
        )

        await interaction.response.send_message(embeds=[embed])

    @app_commands.command(
        name="today-joined", description=_("Counts the members who have joined the guild in the last 24 hours.")
    )
    async def today_joined(self, interaction: discord.Interaction):
        """Shows the amount of members that have joined in the last 24 hours. This does
        not include members that already left. This means, that this number does not represent
        an exact count on how many members the server gained or joined.
        """
        guild = interaction.guild

        if not guild.chunked:
            await guild.chunk(cache=True)

        joined = 0

        for member in guild.members:
            if (discord.utils.utcnow() - member.joined_at).total_seconds() <= 86400:
                joined += 1

        await interaction.response.send_translated(
            _("member_count} users of the server have joined in the last 24 hours."),
            translation_data={"member_count": joined},
        )

    @app_commands.command(name="members", description=_("Shows how many members are currently in the guild."))
    async def members(self, interaction: discord.Interaction):
        """Returns the member count for the current guild."""
        await interaction.response.send_translated(
            _("This guild has {member_count} member."),
            translation_data={"member_count": interaction.guild.member_count},
        )
