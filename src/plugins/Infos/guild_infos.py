import discord.app_commands as cmds
from discord import Interaction, Embed, utils

from lib import checks
from plugins.Infos.user_infos import UserInfo
from translation import _
from utils import colors


class GuildInfo(cmds.Group):
    def __init__(self):
        super().__init__(
            name="guild-info",
            description="Provides information about a guild or guild specific information.",
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        return checks.guild_only_check(interaction)

    @cmds.command(
        name="about",
        description="Displays general information about the current guild.",
    )
    async def about(self, interaction: Interaction):
        lc = interaction.locale
        guild = interaction.guild
        roles = guild.roles

        embed = Embed(title=_(lc, "guild_info.about.title"), color=colors.DISCORD_DEFAULT)
        embed.set_thumbnail(url=guild.icon)
        embed.add_field(
            name=_(lc, "guild_info.about.general_information"),
            value=f"> __{_(lc, 'name')}:__ {guild.name}\n"
            f"> __{_(lc, 'id')}:__ {guild.id}\n"
            f"> __{_(lc, 'guild_info.about.owner')}:__ {guild.owner}\n"
            f"> __{_(lc, 'created_at')}:__ {utils.format_dt(guild.created_at)}",
            inline=False,
        )
        embed.add_field(
            name=_(lc, "guild_info.about.members"),
            value=f"> {str(guild.member_count)}",
            inline=False,
        )

        embed.add_field(
            name=_(lc, "roles"),
            value=f"> {UserInfo._format_roles(roles) or _(lc, 'no_roles')}",
            inline=False,
        )
        embed.add_field(
            name=_(lc, "guild_info.about.more_infos"),
            value=f"> __{_(lc, 'guild_info.about.premium_level')}:__ {guild.premium_tier} ({guild.premium_subscription_count})\n"
            f"> __{_(lc, 'guild_info.about.vanity_url')}:__ {guild.vanity_url or _(lc, 'guild_info.about.no_vanity_url')}\n"
            f"> __{_(lc, 'guild_info.about.emojis')}:__ {len(guild.emojis)}/{guild.emoji_limit}\n"
            f"> __{_(lc, 'guild_info.about.stickers')}:__ {len(guild.stickers)}/{guild.sticker_limit}",
            inline=False,
        )
        embed.add_field(
            name=_(lc, "guild_info.about.features"),
            value=f"> {', '.join(f'`{feature}`' for feature in guild.features) or _(lc, 'guild_info.about.no_features')}\n",
            inline=False,
        )

        await interaction.response.send_message(embeds=[embed])

    @cmds.command(
        name="today-joined",
        description="Shows how many members joined in the last 24 hours.",
    )
    async def today_joined(self, interaction: Interaction):
        guild = interaction.guild
        lc = interaction.locale

        joined = len(
            [
                member.id
                for member in guild.members
                if (utils.utcnow() - member.joined_at).total_seconds() <= 86400
            ]
        )
        embed = Embed(
            description=_(lc, "guild_info.today_joined", members=joined),
            color=colors.DISCORD_DEFAULT,
        )

        await interaction.response.send_message(embeds=[embed])

    @cmds.command(name="members", description="Shows how many members are currently in the guild.")
    async def members(self, interaction: Interaction):
        guild = interaction.guild
        lc = interaction.locale

        embed = Embed(
            color=colors.DISCORD_DEFAULT,
            description=_(lc, "guild_info.members", members=guild.member_count),
        )

        await interaction.response.send_message(embeds=[embed])
