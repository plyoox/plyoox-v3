import discord

from lib import colors


class Embed(discord.Embed):
    def __init__(self, **kwargs: object):
        kwargs.setdefault("color", colors.DISCORD_DEFAULT)
        super().__init__(**kwargs)

    def add_field(self, *, name: str, value: str, inline: bool = False) -> None:
        super().add_field(name=name, value=value, inline=inline)

    def set_field_at(self, index: int, *, name: str, value: str, inline: bool = False) -> None:
        super().set_field_at(index, name=name, value=value, inline=inline)

    def insert_field_at(self, index: int, *, name: str, value: str, inline: bool = False) -> None:
        super().insert_field_at(index, name=name, value=value, inline=inline)
