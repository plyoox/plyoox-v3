import discord

from discord.app_commands import locale_str

from lib import colors


type String = str | locale_str


class Embed(discord.Embed):
    def __init__(self, **kwargs: object):
        kwargs.setdefault("color", colors.DISCORD_DEFAULT)
        super().__init__(**kwargs)

    def add_field(self, *, name: String, value: String, inline: bool = False) -> None:
        super().add_field(name=name, value=value, inline=inline)

    def set_field_at(self, index: int, *, name: String, value: String, inline: bool = False) -> None:
        super().set_field_at(index, name=name, value=value, inline=inline)

    def insert_field_at(self, index: int, *, name: String, value: String, inline: bool = False) -> None:
        super().insert_field_at(index, name=name, value=value, inline=inline)
