from __future__ import annotations

import io
from typing import Optional, TYPE_CHECKING

import discord
import easy_pil
from PIL import Image, ImageDraw, ImageChops
from discord import app_commands

from lib import checks, helper, extensions
from lib.enums import PlyooxModule
from translation import _
from . import _helper

if TYPE_CHECKING:
    from main import Plyoox
    from lib.types import LevelUserData


def _crop_to_circle(avatar: Image):
    big_size = (128 * 3, 128 * 3)

    mask = Image.new("L", big_size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0) + big_size, fill=255)
    mask = mask.resize((128, 128))
    mask = ImageChops.darker(mask, avatar.split()[-1])
    avatar.putalpha(mask)


@app_commands.default_permissions()
@app_commands.guild_only
@checks.module_active(PlyooxModule.Leveling)
class LevelGroup(app_commands.Group):
    BACKGROUND = Image.open("./src/assets/level_card.png")
    FONT = easy_pil.Font.poppins(size=24)
    FONT_sm = easy_pil.Font.poppins(size=18)
    FONT_xs = easy_pil.Font.poppins(size=16)

    def __init__(self, bot: Plyoox):
        super().__init__(name="level", description="Commands that are needed to interact with the level-system.")

        self.db = bot.db

    @staticmethod
    def _generate_image(username: str, avatar: Image, level: int, current_xp: int, needed_xp: int) -> Image:
        background = easy_pil.Editor(LevelGroup.BACKGROUND.copy())

        _crop_to_circle(avatar)

        percentage = min(current_xp / needed_xp, 1)

        background.paste(avatar, (30, 36))
        background.rectangle((190, 100), width=int(250 * percentage), height=19, fill="#24C689", radius=10)
        background.text((190, 70), username, font=LevelGroup.FONT, color="white")
        background.text((190, 130), f"Level", font=LevelGroup.FONT_sm, color="#dedede")
        background.text((290, 130), f"XP", font=LevelGroup.FONT_sm, color="#dedede")
        background.text((190, 150), f"{level}", font=LevelGroup.FONT_xs, color="gray")
        background.text((290, 150), f"{current_xp}/{needed_xp}", font=LevelGroup.FONT_xs, color="gray")

        buffer = io.BytesIO()
        background.image.save(buffer, format="PNG")
        buffer.seek(0)

        return discord.File(buffer, filename=f"{username.split('#')[0]}.png")

    @staticmethod
    async def _create_level_image(
        bot: Plyoox, member: discord.Member, level: int, current_xp: int, needed_xp: int
    ) -> discord.File:
        avatar_image_raw = await member.display_avatar.with_size(128).read()
        avatar_image = Image.open(io.BytesIO(avatar_image_raw))

        return await bot.loop.run_in_executor(
            None, LevelGroup._generate_image, str(member), avatar_image, level, current_xp, needed_xp
        )

    @app_commands.command(name="rank", description="Shows information about the current rank of a member.")
    @app_commands.describe(member="The member from whom you want the rank.")
    async def rank(self, interaction: discord.Interaction, member: Optional[discord.Member]):
        """Shows the current ranking information about a member. If no member is provided, the user that executed
        the command will be used.
        """
        guild = interaction.guild
        current_member = member or interaction.user

        user_data: LevelUserData = await self.db.fetchrow(
            "SELECT * FROM leveling_users WHERE guild_id = $1 AND user_id = $2",
            guild.id,
            current_member.id,
        )

        if user_data is None:
            await helper.interaction_send(interaction, "level.rank.no_data")
            return

        current_level, remaining_xp = _helper.get_level_from_xp(user_data["xp"])
        required_xp = _helper.get_level_xp(current_level)

        image = await self._create_level_image(
            interaction.client, current_member, current_level, remaining_xp, required_xp  # type: ignore
        )

        await interaction.response.send_message(file=image)

    @app_commands.command(name="show-roles", description="Shows the available level roles.")
    async def show_roles(self, interaction: discord.Interaction):
        """Shows the roles that are gain able through the level system"""
        lc = interaction.locale
        guild = interaction.guild

        level_roles: list[list[int, int]] = await self.db.fetchval("SELECT roles FROM leveling WHERE id = $1", guild.id)
        if not level_roles:
            await helper.interaction_send(interaction, "level.level_roles.no_roles")
            return

        roles: list[str] = []

        for [role_id, level] in level_roles:
            role = guild.get_role(role_id)
            if role is not None:
                roles.append(f"{level} - {role.mention}")

        embed = extensions.Embed(title=_(lc, "level.level_roles.title"))
        embed.description = "\n".join(roles)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="top", description="Lists the top 10 users with the highest level on this guild.")
    async def top(self, interaction: discord.Interaction):
        lc = interaction.locale
        guild = interaction.guild

        top_users = []

        while len(top_users) != 10:
            level_users = await self.db.fetch(
                "SELECT user_id, xp FROM leveling_users WHERE guild_id = $1 ORDER BY xp DESC LIMIT 15", guild.id
            )

            for level_user in level_users:
                member = guild.get_member(level_user["userId"])

                if member is not None:
                    current_level, current_xp = _helper.get_level_from_xp(level_user["xp"])
                    required_xp = _helper.get_level_xp(current_level)

                    top_users.append(
                        {"member": member, "level": current_level, "xp_progress": f"{current_xp}/{required_xp}"}
                    )

            if len(level_users) != 15:
                break

        if len(top_users) == 0:
            await helper.interaction_send(interaction, "level.top.no_users")
            return

        embed = extensions.Embed(
            title=_(lc, "level.top.title"),
        )

        for index, top_user in enumerate(top_users):
            embed.add_field(
                name=f"{index + 1}. {top_user['member'].display_name}",
                value=f"> {_(lc, 'level.top.level')} {top_user['level']}\n"
                f"> {top_user['xp_progress']} {_(lc, 'level.top.xp')}",
                inline=True,
            )

        await interaction.response.send_message(embed=embed)
