import discord
from discord import ui
from discord.app_commands import locale_str as _

from lib import emojis


class PrivateView(ui.View):
    def __init__(self, original_interaction: discord.Interaction, *, timeout: float = 180.0):
        super().__init__(timeout=timeout)

        self._last_interaction = original_interaction

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self._last_interaction.user.id:
            await interaction.response.send_translated(_("Only the creator can use this action."), ephemeral=True)
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
            await self._last_interaction.delete_original_response()


class PaginatedEphemeralView(EphemeralView):
    current_page: int
    last_page: int

    def __init__(self, original_interaction: discord.Interaction, last_page: int):
        super().__init__(original_interaction)

        self.current_page = 0
        self.last_page = last_page
        self.update_button_state()

        self.stop_button.label = original_interaction.translate(_("Cancel"))

    def update_button_state(self):
        self.back_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page == self.last_page

    @ui.button(custom_id="back_page", emoji=emojis.chevron_left)
    async def back_button(self, interaction: discord.Interaction, _: ui.Button):
        self.current_page -= 1
        self.update_button_state()
        await self.back(interaction)

    @ui.button(custom_id="next_page", emoji=emojis.chevron_right)
    async def next_button(self, interaction: discord.Interaction, _: ui.Button):
        self.current_page += 1
        self.update_button_state()
        await self.next(interaction)

    @ui.button(emoji=emojis.close, style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, _: ui.Button):
        self.stop()

        await interaction.response.defer()
        await interaction.delete_original_response()

    async def back(self, interaction: discord.Interaction):
        pass

    async def next(self, interaction: discord.Interaction):
        pass
