from __future__ import annotations

import discord
from discord import ui

from lib import emojis, extensions
from translation import _


async def _change_member_view(interaction: discord.Interaction, view: MemberView, index_change: int = 0):
    lc = interaction.locale

    view.current_index += index_change

    embed = extensions.Embed(title=_(lc, "moderation.massban.view_member_title"))
    embed.set_footer(text=f"{_(lc, 'moderation.massban.page')}: {view.current_index + 1}")

    members = view.members[
        view.current_index * MemberView.MEMBERS_PER_PAGE : MemberView.MEMBERS_PER_PAGE * (view.current_index + 1)
    ]

    embed.description = "\n".join(f"{m} ({m.id})" for m in members)  # type: ignore

    view._update_buttons()

    await interaction.response.defer()
    await interaction.edit_original_message(embed=embed, view=view)


class BanButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "moderation.massban.ban_button_label"), style=discord.ButtonStyle.red, emoji=emojis.hammer
        )

        self.massban_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        lc = interaction.locale

        await interaction.response.send_message(
            _(lc, "moderation.massban.ban_users", member_count=len(self.massban_view.members))
        )

        error_count = 0
        ban_count = 0

        for member in self.massban_view.members:
            try:
                await interaction.guild.ban(member, reason=self.massban_view.reason)
                ban_count += 1
            except discord.Forbidden:
                error_count += 1
                if error_count == 5:
                    await interaction.edit_original_message(
                        content=_(lc, "moderation.massban.ban_failed", member_count=ban_count)
                    )
                    return
            except discord.HTTPException:
                pass

        await interaction.edit_original_message(content=_(lc, "moderation.massban.ban_success", member_count=ban_count))


class CancelButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "moderation.massban.close_button_label"), style=discord.ButtonStyle.gray, emoji=emojis.close
        )

        self.massban_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        lc = interaction.locale

        for item in self.massban_view.children:
            item.disabled = True

        await interaction.response.defer()
        await interaction.edit_original_message(content=_(lc, "moderation.massban.cancel_ban"), view=None, embed=None)


class ViewMemberButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "moderation.massban.view_member_button_label"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.users,
        )

        self.massban_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await _change_member_view(interaction, MemberView(interaction, self.massban_view))


class NextMemberButton(ui.Button):
    def __init__(self, view: MemberView, locale: discord.Locale, disabled: bool = False):
        super().__init__(
            label=_(locale, "next_site"),
            style=discord.ButtonStyle.green,
            emoji=emojis.chevrons_right,
            disabled=disabled,
        )

        self.member_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await _change_member_view(interaction, self.member_view, 1)


class BackMemberButton(ui.Button):
    def __init__(self, view: MemberView, locale: discord.Locale, disabled: bool = False):
        super().__init__(
            label=_(locale, "previous_site"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.chevrons_left,
            disabled=disabled,
        )

        self.member_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        await _change_member_view(interaction, self.member_view, -1)


class CloseMemberViewButton(ui.Button):
    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__(
            label=_(locale, "back"),
            style=discord.ButtonStyle.gray,
            emoji=emojis.chevron_left,
        )

        self.massban_view = view

    async def callback(self, interaction: discord.Interaction) -> None:
        embed = extensions.Embed(description=_(interaction.locale, "moderation.massban.overview_description"))
        await interaction.response.defer()

        await interaction.edit_original_message(embed=embed, view=self.massban_view)


class MemberView(extensions.EphemeralView):
    MEMBERS_PER_PAGE = 50

    def __init__(self, interaction: discord.Interaction, view: MassbanView):
        super().__init__(interaction)

        self.members = view.members
        self.current_index = 0
        self.massban_view = view

        self.back_member_button = BackMemberButton(self, interaction.locale)
        self.next_member_button = NextMemberButton(self, interaction.locale)
        self.close_member_view_button = CloseMemberViewButton(view, interaction.locale)

        self.add_item(self.back_member_button)
        self.add_item(self.next_member_button)
        self.add_item(self.close_member_view_button)

    def _update_buttons(self) -> None:
        self.back_member_button.disabled = self.current_index == 0
        self.next_member_button.disabled = len(self.members) / self.MEMBERS_PER_PAGE <= self.current_index + 1


class MassbanView(extensions.EphemeralView):
    members: list[discord.Member]
    reason: str

    def __init__(self, interaction: discord.Interaction, members: list[discord.Member], reason: str):
        super().__init__(interaction)

        self.members = members
        self.reason = reason

        self.add_item(BanButton(self, interaction.locale))
        self.add_item(ViewMemberButton(self, interaction.locale))
        self.add_item(CancelButton(self, interaction.locale))
