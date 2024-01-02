from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import ui
from discord.app_commands import locale_str as _

from lib import emojis, extensions

if TYPE_CHECKING:
    from main import Plyoox
    from lib.types import Infractions


class MemberView(extensions.PaginatedEphemeralView):
    MEMBERS_PER_PAGE = 50

    def __init__(self, interaction: discord.Interaction, members: list[discord.Member], old_view: ui.View):
        super().__init__(original_interaction=interaction, last_page=len(members) // 10)

        self.members = members
        self.old_view = old_view

        self.stop_button.label = interaction.translate(_("Back"))

    def generate_embed(self):
        translate = self._last_interaction.translate

        embed = extensions.Embed(title=translate(_("List of members")))
        embed.set_footer(text=f"{translate(_('Page'))}: {self.current_page + 1}/{self.last_page + 1}")

        members = self.members[
          self.current_page * MemberView.MEMBERS_PER_PAGE: MemberView.MEMBERS_PER_PAGE * (self.current_page + 1)
        ]

        embed.description = "\n".join(f"{m} ({m.id})" for m in members)

        return embed

    async def next(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=self.generate_embed(), view=self)

    async def back(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.edit_original_response(embed=self.generate_embed(), view=self)

    @ui.button(custom_id="stop", emoji=emojis.chevrons_left, style=discord.ButtonStyle.blurple)
    async def stop_button(self, interaction: discord.Interaction, _b: ui.Button):
        embed = extensions.Embed(description=interaction.translate(_("Confirm the selection of users to be banned.")))
        await interaction.response.defer()

        await interaction.edit_original_response(embed=embed, view=self.old_view)
        self.stop()


class MassbanView(extensions.EphemeralView):
    members: list[discord.Member]
    reason: str

    def __init__(self, interaction: discord.Interaction, members: list[discord.Member], reason: str):
        super().__init__(interaction)

        self.members = members
        self.reason = reason

        self.ban_button.label = interaction.translate(_("Ban users"))
        self.member_view.label = interaction.translate(_("View users"))
        self.stop_button.label = interaction.translate(_("Cancel"))

    @ui.button(emoji=emojis.hammer, style=discord.ButtonStyle.green)
    async def ban_button(self, interaction: discord.Interaction, _b: discord.Button):
        await interaction.response.send_translated(
            _("{user_count} users will be banned..."), translation_data={"user_count": len(self.members)}
        )

        error_count = 0
        ban_count = 0

        for member in self.members:
            try:
                await interaction.guild.ban(member, reason=self.reason)
                ban_count += 1
            except discord.Forbidden:
                error_count += 1
                if error_count == 5:
                    await interaction.edit_original_response(
                        content=interaction.translate(
                            _("Too many errors occurred while banning users. {user_count} users have been banned."),
                            data={"user_count": ban_count},
                        )
                    )
                    return
            except discord.HTTPException:
                pass

        await interaction.edit_original_response(
            content=interaction.translate(_("Successfully banned {user_count} users."), data={"user_count": ban_count}),
            view=None,
        )

    @ui.button(emoji=emojis.users)
    async def member_view(self, interaction: discord.Interaction, _b: discord.Button):
        await interaction.response.defer()

        view = MemberView(interaction, self.members, old_view=self)
        await interaction.edit_original_response(view=view, embed=view.generate_embed())

    @ui.button(emoji=emojis.close, style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, _: discord.Button):
        self.stop()

        await interaction.response.defer()
        await interaction.delete_original_response()


class WarnView(extensions.PaginatedEphemeralView):
    def __init__(self, original_interaction: discord.Interaction, user: discord.User, last_page: int = None):
        super().__init__(original_interaction, last_page=last_page)

        self.bot: Plyoox = original_interaction.client
        self.user = user
        self.view_expired = False

        self.view_expired_button.label = original_interaction.translate(_("Expired Infractions"))

    async def get_page_count(self) -> int:
        if self.view_expired:
            query = "SELECT count(*) FROM automoderation_user WHERE user_id = $1 AND guild_id = $2 AND expires_at < now()"
        else:
            query = "SELECT count(*) FROM automoderation_user WHERE user_id = $1 AND guild_id = $2 AND expires_at > now()"

        infraction_count = await self.bot.db.fetchval(query, self.user.id, self._last_interaction.guild_id)

        return infraction_count // 10

    async def generate_embed(self, page: int) -> discord.Embed:
        translate = self._last_interaction.translate

        if self.view_expired:
            query = "SELECT * from automoderation_user WHERE user_id = $1 AND guild_id = $2 AND expires_at < now() OFFSET $3 LIMIT 10"
        else:
            query = "SELECT * from automoderation_user WHERE user_id = $1 AND guild_id = $2 AND expires_at > now() OFFSET $3 LIMIT 10"

        infractions: Infractions = await self.bot.db.fetch(
            query, self.user.id, self._last_interaction.guild_id, page * 10
        )

        if len(infractions) == 0:
            return extensions.Embed(description=translate(_("This user has no warnings.")))

        embed = extensions.Embed(title=translate(_("Infractions")))
        embed.set_author(name=str(self.user), icon_url=self.user.display_avatar.url)
        embed.set_footer(text=f'{translate(_("Page"))} {self.current_page + 1}/{self.last_page + 1}')

        for infraction in infractions:
            infraction = dict(infraction)

            created_at = discord.utils.format_dt(infraction["created_at"])
            expires_at = (
                discord.utils.format_dt(infraction["expires_at"]) if infraction["expires_at"] else translate(_("Never"))
            )

            embed.add_field(
                name=f'{translate(_("Infraction"))} #{infraction["id"]}',
                value=(
                    f"**{translate(_('Points'))}:** {infraction['points']}\n"
                    f"**{translate(_('Expires at'))}:** {expires_at}\n"
                    f"**{translate(_('Created at'))}:** {created_at}\n"
                    f"**{translate(_('Reason'))}:** {infraction['reason']}"
                ),
                inline=True,
            )

        return embed

    async def initialize(self) -> discord.Embed:
        if self.last_page is None:
            self.last_page = await self.get_page_count()

            self.update_button_state()

        return await self.generate_embed(0)

    async def back(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embed = await self.generate_embed(self.current_page)
        await interaction.edit_original_response(embed=embed, view=self)

    async def next(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embed = await self.generate_embed(self.current_page)
        await interaction.edit_original_response(embed=embed, view=self)

    @ui.button(custom_id="change_expired", style=discord.ButtonStyle.blurple, row=1)
    async def view_expired_button(self, interaction: discord.Interaction, button: ui.Button):
        self.current_page = 0
        self.view_expired = not self.view_expired

        button.label = interaction.translate(_("Active Infractions") if self.view_expired else _("Expired Infractions"))

        self.last_page = await self.get_page_count()
        embed = await self.generate_embed(self.current_page)

        self.update_button_state()

        await interaction.response.defer()
        await interaction.edit_original_response(embed=embed, view=self)
