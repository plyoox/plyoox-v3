from typing import Self

import discord

from lib.colors import DISCORD_DEFAULT


class Embed(discord.Embed):
    def __init__(self, **kwargs):
        kwargs.setdefault("color", DISCORD_DEFAULT)
        super().__init__(**kwargs)

    def add_field(self, *, name: str, value: str, inline: bool = False) -> Self:
        super().add_field(name=name, value=value, inline=inline)

    def set_field_at(self, index: int, *, name: str, value: str, inline: bool = False) -> Self:
        super().set_field_at(index, name=name, value=value, inline=inline)

    def insert_field_at(self, index: int, *, name: str, value: str, inline: bool = True) -> Self:
        super().insert_field_at(index, name=name, value=value, inline=inline)
