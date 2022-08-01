from __future__ import annotations

import discord
from discord import ui

from lib import emojis
from lib.extensions import Embed
from translation import _


async def _change_member_view(interaction: discord.Interaction, view: MemberView, index_change: int = 0):
    lc = interaction.locale

    view.current_index += index_change

    embed = Embed(title=_(lc, "moderation.massban.view_member_title"))
    embed.set_footer(text=f"{_(lc, 'moderation.massban.page')}: {view.current_index + 1}")

    members = view.members[
        view.current_index * MemberView.MEMBERS_PER_PAGE : MemberView.MEMBERS_PER_PAGE * (view.current_index + 1)
    ]

    embed.description = "\n".join(f"{m} ({m.id})" for m in members)  # type: ignore

    await interaction.response.defer()
    await interaction.edit_original_message(embed=embed, view=MemberView(view.massban_view, lc))


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
        await _change_member_view(interaction, MemberView(view=self.massban_view, locale=interaction.locale))


class NextMemberButton(ui.Button):
    def __init__(self, view: MemberView, locale: discord.Locale, disabled: bool = False):
        super().__init__(
            label=_(locale, "next_site"),
            style=discord.ButtonStyle.gray,
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
        embed = Embed(description=_(interaction.locale, "moderation.massban.overview_description"))
        await interaction.response.defer()

        await interaction.edit_original_message(embed=embed, view=self.massban_view)


class MemberView(ui.View):
    MEMBERS_PER_PAGE = 50

    def __init__(self, view: MassbanView, locale: discord.Locale):
        super().__init__()

        self.members = view.members
        self.current_index = 0
        self.massban_view = view

        self.add_item(BackMemberButton(self, locale, disabled=True))

        if len(view.members) < self.MEMBERS_PER_PAGE:
            self.add_item(NextMemberButton(self, locale, disabled=True))
        else:
            self.add_item(NextMemberButton(self, locale))

        self.add_item(CloseMemberViewButton(view, locale))


class MassbanView(ui.View):
    members: list[discord.Member]
    reason: str

    def __init__(self, members: list[discord.Member], reason: str, locale: discord.Locale):
        super().__init__()

        self.members = members
        self.reason = reason

        self.add_item(BanButton(self, locale))
        self.add_item(CancelButton(self, locale))
        self.add_item(ViewMemberButton(self, locale))
