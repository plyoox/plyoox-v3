from typing import TYPE_CHECKING

import discord
from discord import ui

from lib import helper, formatting, colors
from translation import _

if TYPE_CHECKING:
    from main import Plyoox


class WelcomeMessageModal(ui.Modal):
    def __init__(self, locale: discord.Locale, message: str = None) -> None:
        super().__init__(title=_(locale, "config.welcome.modal.title"))

        self.message = ui.TextInput(
            label=_(locale, "config.welcome.welcome_message"),
            max_length=3900,
            style=discord.TextStyle.paragraph,
            placeholder=_(locale, "config.welcome.modal.message_example"),
            default=message,
            required=False,
        )

        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        bot: Plyoox = interaction.client  # type: ignore
        guild = interaction.guild
        message = self.message.value

        if message is None or not message.strip():
            await bot.db.execute("UPDATE welcome SET join_message = NULL WHERE id = $1", guild.id)
            await helper.interaction_send(interaction, "config.welcome.modal.message_removed")
            return

        formatted_message = formatting.resolve_channels(message, guild)
        if len(formatted_message) > 4000:
            await helper.interaction_send(interaction, "config.message_to_long")

        await bot.db.execute(
            "INSERT INTO welcome (id, join_message) VALUES ($1, $2) ON CONFLICT (id) DO UPDATE set join_message = $2",
            guild.id,
            formatted_message,
        )

        embed = discord.Embed(
            description=formatting.format_welcome_message(formatted_message, interaction.user),
            title=_(interaction.locale, "config.welcome.welcome_message"),
            color=colors.DISCORD_DEFAULT,
        )

        if len(formatted_message) > 2000:
            await interaction.response.send_message(_(interaction.locale, "embed_used"), embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
