import discord
from discord import ui

from translation import _


class PrivateView(ui.View):
    def __init__(self, original_interaction: discord.Interaction, *, timeout: float = 180.0):
        super().__init__(timeout=timeout)

        self._last_interaction = original_interaction

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._last_interaction.user.id:
            await interaction.response.send_message(_(interaction.locale, "views.creator_only"), ephemeral=True)
            return False

        self._last_interaction = interaction
        return True

    async def on_timeout(self) -> None:
        has_content = False
        if (message := self._last_interaction.message) is not None:
            has_content = len(message.content) or len(message.embeds) or len(message.attachments)

        try:
            if self._last_interaction.is_expired():
                if self._last_interaction.message is None:
                    return

                if has_content:
                    await self._last_interaction.message.edit(view=None)
                else:
                    await self._last_interaction.message.delete()
            else:
                if has_content:
                    await self._last_interaction.edit_original_response(view=None)
                else:
                    await self._last_interaction.delete_original_response()
        except discord.NotFound:
            pass


class EphemeralView(ui.View):
    def __init__(self, original_interaction: discord.Interaction, *, timeout: float = 180.0):
        super().__init__(timeout=timeout)

        self._last_interaction = original_interaction

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self._last_interaction = interaction
        return True

    async def on_timeout(self) -> None:
        if not self._last_interaction.is_expired():
            await self._last_interaction.edit_original_response(view=None)
