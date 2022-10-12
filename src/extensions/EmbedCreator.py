"""
Original work from Imp
- Discord:  imp#2573 (364487161250316289)
- GitHub:   https://github.com/imptype

Source: https://gist.github.com/imptype/7b35c6769684fb68178e5719e5f81b6d
"""
from __future__ import annotations

import copy
import datetime
import io
import json
import re
from typing import Callable, TYPE_CHECKING

import discord
from discord import app_commands, ui
from discord.ext import commands

from lib import extensions, errors
from translation import _

if TYPE_CHECKING:
    import aiohttp


MESSAGE_REGEX = re.compile(r"\bhttps://(canary.)?discord.com/channels/\d{17,20}/\d{17,20}/\d{17,20}\b")
MAX_SELECT_OPTIONS = 25  # max options in a select


def url_conversion(url: str) -> str | None:
    if not url:
        return None

    if not url.startswith(("http://", "https://")):
        raise errors.ConversionError("embed-creator.url_conversion_error")

    return url


class InputModal(ui.Modal):
    interaction: discord.Interaction

    def __init__(self, name: str, *text_inputs: ui.TextInput):
        super().__init__(title=f"{name} Modal", timeout=300.0)

        for text_input in text_inputs:
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.interaction = interaction


class ImportView(ui.View):
    if TYPE_CHECKING:
        return_callback: Callable
        return_to: str

    def __init__(self, base_view: BaseView, lc: discord.Locale):
        super().__init__()
        self.base_view = base_view

        self.has_message_button = True

        self.import_json = ui.Button(label=_(lc, "embed-creator.import_json_button"), style=discord.ButtonStyle.green)
        self.import_json.callback = self.import_json_callback
        self.add_item(self.import_json)

        self.import_message = ui.Button(
            label=_(lc, "embed-creator.import_message_button"), style=discord.ButtonStyle.green
        )
        self.import_message.callback = self.import_message_callback
        self.add_item(self.import_message)

        self.back_button = ui.Button(label=_(lc, "back"), style=discord.ButtonStyle.gray)
        self.back_button.callback = self.back_callback
        self.add_item(self.back_button)

    async def import_json_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.json_data_label"),
            placeholder=_(interaction.locale, "embed-creator.json_data_placeholder"),
            style=discord.TextStyle.long,
        )

        modal = InputModal(self.import_json.label, text_input)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        try:
            data = json.loads(text_input.value)
        except Exception as error:
            error.interaction = modal.interaction
            raise error

        await self.return_callback(modal.interaction, data)

    async def import_message_callback(self, interaction: discord.Interaction):
        lc = interaction.locale

        text_input = ui.TextInput(
            label=_(lc, "embed-creator.message_link"),
            placeholder="https://discord.com/channels/XXXXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXXXX",
        )

        modal = InputModal(_(lc, "embed-creator.message_link"), text_input)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        try:
            if MESSAGE_REGEX.match(text_input.value) is None:
                await modal.interaction.response.send_message(_(lc, "embed-creator.invalid_link"), ephemeral=True)
                return

            value = text_input.value.split("/")[-3:]
            guild_id, channel_id, message_id = map(int, value)
            guild = interaction.guild

            if interaction.guild_id != guild_id:
                await modal.interaction.response.send_message(_(lc, "embed-creator.invalid_guild_id"), ephemeral=True)
                return

            channel = guild.get_channel(channel_id)
            if channel is None:
                await modal.interaction.response.send_message(_(lc, "embed-creator.invalid_channel"), ephemeral=True)
                return

            try:
                message = await channel.fetch_message(message_id)
            except discord.NotFound:
                await modal.interaction.response.send_message(_(lc, "embed-creator.message_not_found"), ephemeral=True)
                return

            data = {}
            if message.content:
                data["content"] = message.content
            if message.embeds:
                data["embeds"] = [embed.to_dict() for embed in message.embeds]
        except Exception as error:
            error.interaction = modal.interaction
            raise error

        await self.return_callback(modal.interaction, data)

    async def back_callback(self, interaction: discord.Interaction):
        self.base_view.set_view(self.return_to)

        await interaction.response.edit_message(view=self.base_view)


class SelectView(ui.View):
    if TYPE_CHECKING:
        return_to: str

    def __init__(self, base_view: BaseView, lc: discord.Locale):
        super().__init__()
        self.base_view = base_view
        self.locale = lc

        self.options_list = []
        self.page_index = 0
        self.has_page_buttons = False

        self.dynamic_select = ui.Select()
        self.add_item(self.dynamic_select)

        self.left_button = ui.Button(label="<", row=1)
        self.left_button.callback = self.left_callback

        self.right_button = ui.Button(label=">", row=1)
        self.right_button.callback = self.right_callback

        self.what_button = ui.Button(disabled=True, row=1)

        self.back_button = ui.Button(label=_(lc, "back"), row=2, style=discord.ButtonStyle.gray)
        self.back_button.callback = self.back_callback
        self.add_item(self.back_button)

    def set_select_options(self, options: list[discord.SelectOption]):
        if len(options) > 25:
            if self.has_page_buttons is False:
                self.add_item(self.left_button)
                self.add_item(self.what_button)
                self.add_item(self.right_button)

                self.has_page_buttons = True

            self.options_list = [
                options[i : i + MAX_SELECT_OPTIONS] for i in range(0, len(options), MAX_SELECT_OPTIONS)
            ]
            self.dynamic_select.options = self.options_list[0]
            self.page_index = 0

            self.left_button.disabled = True
            self.right_button.disabled = False
            self.what_button.label = f"{_(self.locale, 'page')} 1/{len(self.options_list)}"

        else:
            if self.has_page_buttons is True:
                self.remove_item(self.left_button)
                self.remove_item(self.what_button)
                self.remove_item(self.right_button)
                self.has_page_buttons = False

            self.dynamic_select.options = options

    async def left_callback(self, interaction: discord.Interaction):
        self.page_index -= 1
        if self.page_index == 0:
            self.left_button.disabled = True

        self.right_button.disabled = False
        self.what_button.label = f"{_(self.locale, 'page')} {self.page_index + 1}/{len(self.options_list)}"
        self.dynamic_select.options = self.options_list[self.page_index]

        await interaction.response.edit_message(view=self.base_view)

    async def right_callback(self, interaction: discord.Interaction):
        self.page_index += 1
        if self.page_index == len(self.options_list) - 1:
            self.right_button.disabled = True

        self.left_button.disabled = False
        self.what_button.label = f"{_(self.locale, 'page')} {self.page_index + 1}/{len(self.options_list)}"
        self.dynamic_select.options = self.options_list[self.page_index]

        await interaction.response.edit_message(view=self.base_view)

    async def back_callback(self, interaction: discord.Interaction):
        self.base_view.set_view(self.return_to)

        await interaction.response.edit_message(view=self.base_view)


class SendView(ui.View):
    def __init__(self, base_view: BaseView):
        super().__init__()
        self.base_view = base_view
        lc = base_view.locale

        self.channel_button = ui.Button(
            label=_(lc, "embed-creator.send_channel_button"), style=discord.ButtonStyle.green
        )
        self.channel_button.callback = self.channel_callback
        self.add_item(self.channel_button)

        self.webhook_button = ui.Button(
            label=_(lc, "embed-creator.send_webhook_button"), style=discord.ButtonStyle.green
        )
        self.webhook_button.callback = self.webhook_callback
        self.add_item(self.webhook_button)

        self.back_button = ui.Button(label=_(lc, "back"), style=discord.ButtonStyle.gray)
        self.back_button.callback = self.back_callback
        self.add_item(self.back_button)

    async def channel_callback(self, interaction: discord.Interaction):
        guild = interaction.guild

        options = [
            discord.SelectOption(
                label=f"#{channel.name[:99]}",
                description=f"{channel.category.name} | ({channel.id})",
                value=str(channel.id),
            )
            for channel in guild.text_channels
            if channel.permissions_for(guild.me).send_messages
        ]

        async def callback(_interaction: discord.Interaction):
            channel_id = int(self.base_view.get_select_value())

            channel = guild.get_channel(channel_id)
            if channel is None:
                await interaction.response.send_message(
                    _(_interaction.locale, "embed-creator.unknown_channel"), ephemeral=True
                )
                return

            self.base_view.set_view("send")

            await channel.send(content=self.base_view.content, embeds=self.base_view.embeds)
            await _interaction.response.send_message(
                _(_interaction.locale, "embed-creator.message_sent_to", channel=channel), ephemeral=True
            )

        self.base_view.set_select(_(interaction.locale, "embed-creator.select_channel"), options, callback, "send")

        await interaction.response.edit_message(view=self.base_view)

    async def webhook_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.webhook_label"),
            placeholder="https://discord.com/api/webhooks/XXXXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        )

        modal = InputModal(_(interaction.locale, "embed-creator.send_webhook_button"), text_input)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        webhook_url = text_input.value
        try:
            webhook = discord.Webhook.from_url(webhook_url, session=self.base_view.session)
            await webhook.send(
                content=self.base_view.content,
                embeds=self.base_view.embeds,
                username=interaction.user.name,
                avatar_url=interaction.user.avatar,
            )
        except Exception as error:
            error.interaction = modal.interaction
            raise error

        await modal.interaction.response.send_message(
            _(interaction.locale, "embed-creator.webhook_message_confirmation"), ephemeral=True
        )

    async def back_callback(self, interaction: discord.Interaction):
        self.base_view.set_view("message")

        await interaction.response.edit_message(view=self.base_view)


class EmbedView(ui.View):
    if TYPE_CHECKING:
        edit_field_button: ui.Button
        clear_fields_button: ui.Button
        remove_field_button: ui.Button
        add_field_button: ui.Button

    def __init__(self, base_view: BaseView):
        super().__init__()
        self.base_view = base_view
        self.locale = self.base_view.locale

        self.embed: discord.Embed | None = None  # the following are changed often
        self.embed_dict: dict | None = None  # used for default values and reverting changes
        self.embed_original: discord.Embed | None = None  # for resetting
        self.embed_index: int | None = None  # index in self.embeds

        self.what_button = ui.Button(disabled=True)
        self.setup_buttons()

    @property
    def exceeds_chars(self) -> bool:
        count = 0

        for embed in self.base_view.embeds:
            count += len(embed)

        return count > 6000

    def reset_current_embed(self):
        self.embed = discord.Embed.from_dict(self.embed_dict)
        self.base_view.embeds[self.embed_index] = self.embed

    def add_button(self, name: str, style: discord.ButtonStyle = discord.ButtonStyle.gray, row: int | None = None):
        button = ui.Button(label=_(self.locale, f"embed-creator.{name}"), style=style, row=row)
        button.callback = getattr(self, f"{name}_callback")

        setattr(self, f"{name}_button", button)

        self.add_item(button)

    def update_field_buttons(self, embed_dict: dict = None):  # ensures field-related buttons are disabled correctly
        embed_dict = embed_dict or self.embed_dict

        if "fields" in embed_dict and embed_dict["fields"]:
            self.remove_field_button.disabled = False
            self.clear_fields_button.disabled = False
            self.edit_field_button.disabled = False

            if len(embed_dict["fields"]) == 25:  # max fields in embed
                self.add_field_button.disabled = True
            else:
                self.add_field_button.disabled = False
        else:
            self.remove_field_button.disabled = True
            self.clear_fields_button.disabled = True
            self.edit_field_button.disabled = True
            self.add_field_button.disabled = False

    async def show_modal(
        self,
        interaction: discord.Interaction,
        *text_inputs: ui.TextInput,
        method: str = None,
        embed_key: str = None,
    ):
        for text_input in text_inputs:
            old = self.embed_dict.get(embed_key, None)
            if old is not None:
                if hasattr(text_input, "key"):
                    old = old.get(text_input.key, None)

            text_input.default = old

        modal = InputModal(_(interaction.locale, f"embed-creator.{embed_key or method}"), *text_inputs)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        new_values = []
        for text_input in text_inputs:
            new = text_input.value.strip()
            if new:
                if hasattr(text_input, "convert"):
                    try:
                        new = text_input.convert(new)
                    except Exception as error:
                        error.interaction = modal.interaction
                        raise error
                new_values.append(new)
            else:
                new_values.append(None)

        try:
            if method is not None:
                kwargs = {text_input.key: new for text_input, new in zip(text_inputs, new_values)}
                getattr(self.embed, method)(**kwargs)
            else:
                setattr(self.embed, embed_key, new_values[0])
        except errors.ConversionError as err:
            err.interaction = modal.interaction
            self.reset_current_embed()

            raise err

        if self.exceeds_chars:
            await modal.interaction.response.send_message(_(interaction.locale, "embed-creator.max_message_length"))
            return

        try:
            await modal.interaction.response.edit_message(embeds=self.base_view.embeds)
            self.embed_dict = self.embed.to_dict()
        except Exception as error:
            self.reset_current_embed()
            raise error

    def setup_buttons(self):
        self.add_button("title", style=discord.ButtonStyle.blurple)
        self.add_button("url", style=discord.ButtonStyle.blurple)
        self.add_button("description", style=discord.ButtonStyle.blurple)
        self.add_button("color", style=discord.ButtonStyle.blurple)
        self.add_button("timestamp", style=discord.ButtonStyle.blurple)
        self.add_button("set_author", style=discord.ButtonStyle.blurple)
        self.add_button("set_thumbnail", style=discord.ButtonStyle.blurple)
        self.add_button("set_image", style=discord.ButtonStyle.blurple)
        self.add_button("set_footer", style=discord.ButtonStyle.blurple)
        self.add_button("add_field", style=discord.ButtonStyle.blurple, row=2)
        self.add_button("edit_field", style=discord.ButtonStyle.blurple, row=2)
        self.add_button("remove_field", style=discord.ButtonStyle.blurple, row=2)
        self.add_button("clear_fields", style=discord.ButtonStyle.red, row=2)
        self.add_button("import_embed", style=discord.ButtonStyle.green, row=3)
        self.add_button("export_embed", style=discord.ButtonStyle.green, row=3)
        self.add_button("back", style=discord.ButtonStyle.gray, row=4)

    async def title_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.title"),
            placeholder=_(interaction.locale, "embed-creator.title_placeholder"),
            required=False,
            max_length=256,
        )

        await self.show_modal(interaction, text_input, embed_key="title")

    async def url_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.url"),
            placeholder=_(interaction.locale, "embed-creator.url_placeholder"),
            required=False,
        )
        text_input.convert = url_conversion

        await self.show_modal(interaction, text_input, embed_key="url")

    async def description_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.description"),
            placeholder=_(interaction.locale, "embed-creator.description_placeholder"),
            style=discord.TextStyle.long,
            required=False,
            max_length=4000,
        )

        await self.show_modal(interaction, text_input, embed_key="description")

    async def color_callback(self, interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.color"),
            placeholder=_(interaction.locale, "embed-creator.color_placeholder"),
            required=False,
        )

        def convert(inp: str) -> discord.Color | None:
            if not inp:
                return None

            try:
                return discord.Color.from_str(inp)
            except ValueError:
                return None

        text_input.convert = convert

        await self.show_modal(interaction, text_input, embed_key="color")

    async def timestamp_callback(self, interaction):
        text_input = discord.ui.TextInput(
            label=_(interaction.locale, "embed-creator.timestamp"),
            placeholder=_(interaction.locale, "embed-creator.timestamp_placeholder"),
            required=False,
            max_length=10,
        )

        def convert(x: str) -> datetime.datetime | None:
            if x == "now":
                return discord.utils.utcnow()

            try:
                return datetime.datetime.utcfromtimestamp(int(x))
            except ValueError:
                raise errors.ConversionError("embed-creator.timestamp_conversion_error")

        text_input.convert = convert
        await self.show_modal(interaction, text_input, embed_key="timestamp")

    async def set_author_callback(self, interaction: discord.Interaction):
        name_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.set_author"),
            placeholder=_(interaction.locale, "embed-creator.set_author_placeholder"),
            required=False,
            max_length=256,
        )
        name_input.key = "name"

        url_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.url"),
            placeholder=_(interaction.locale, "embed-creator.set_author_url_placeholder"),
            required=False,
        )
        url_input.key = "url"
        url_input.convert = url_conversion

        icon_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.set_author_icon_url"),
            placeholder=_(interaction.locale, "embed-creator.set_author_icon_url_placeholder"),
            required=False,
        )
        icon_input.key = "icon_url"
        icon_input.convert = url_conversion

        text_inputs = [name_input, url_input, icon_input]
        await self.show_modal(interaction, *text_inputs, method="set_author")

    async def set_thumbnail_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.set_thumbnail"),
            placeholder=_(interaction.locale, "embed-creator.set_thumbnail_placeholder"),
            required=False,
        )
        text_input.key = "url"
        text_input.convert = url_conversion

        await self.show_modal(interaction, text_input, method="set_thumbnail")

    async def set_image_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.set_image"),
            placeholder=_(interaction.locale, "embed-creator.set_image_placeholder"),
            required=False,
        )
        text_input.key = "url"
        text_input.covert = url_conversion

        await self.show_modal(interaction, text_input, method="set_image")

    async def set_footer_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.set_footer_text"),
            placeholder=_(interaction.locale, "embed-creator.set_footer_text_placeholder"),
            required=False,
            max_length=2048,
        )
        text_input.key = "text"

        icon_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.set_footer_icon"),
            placeholder=_(interaction.locale, "embed-creator.set_footer_icon_placeholder"),
            required=False,
        )
        icon_input.key = "icon_url"
        icon_input.convert = url_conversion

        text_inputs = [text_input, icon_input]
        await self.show_modal(interaction, *text_inputs, method="set_footer")

    async def add_field_callback(self, interaction: discord.Interaction):
        name_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.field_name_label"),
            placeholder=_(interaction.locale, "embed-creator.field_name_placeholder"),
            max_length=256,
        )
        value_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.field_value_label"),
            placeholder=_(interaction.locale, "embed-creator.field_value_placeholder"),
            style=discord.TextStyle.long,
            max_length=1024,
        )
        inline_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.field_inline_label"),
            placeholder=_(interaction.locale, "embed-creator.field_inline_placeholder"),
            required=False,
            max_length=1,
        )
        index_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.field_index_label"),
            placeholder=_(interaction.locale, "embed-creator.field_index_placeholder"),
            required=False,
            max_length=2,
        )

        modal = InputModal(
            _(interaction.locale, "embed-creator.add_field"), *[name_input, value_input, inline_input, index_input]
        )
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        inline = inline_input.value.strip() == "1"
        embed = discord.Embed.from_dict(copy.deepcopy(self.embed_dict))

        kwargs = {"name": name_input.value, "value": value_input.value, "inline": inline, "index": -1}

        if index_input.value.strip().isnumeric():
            kwargs["index"] = int(index_input.value)

        embed.insert_field_at(**kwargs)

        self.update_field_buttons(embed.to_dict())
        self.base_view.embeds[self.embed_index] = embed

        try:
            await modal.interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)
        except Exception as error:
            self.update_field_buttons()
            self.base_view.embeds[self.embed_index] = self.embed
            raise error
        else:
            self.embed = embed
            self.embed_dict = copy.deepcopy(embed.to_dict())

    async def edit_field_callback(self, interaction: discord.Interaction):
        options = [
            discord.SelectOption(
                label=f"{_(interaction.locale, 'embed-creator.field')} {i + 1}",
                description=field["name"][:100],
                value=str(i),
            )
            for i, field in enumerate(self.embed_dict["fields"])
        ]

        async def callback(_interaction: discord.Interaction):
            index = int(self.base_view.get_select_value())
            field = self.embed_dict["fields"][index]

            name_input = ui.TextInput(
                label=_(interaction.locale, "embed-creator.field_name_label"),
                placeholder=_(interaction.locale, "embed-creator.field_name_placeholder"),
                default=field["name"],
                max_length=256,
            )
            value_input = ui.TextInput(
                label=_(interaction.locale, "embed-creator.field_value_label"),
                placeholder=_(interaction.locale, "embed-creator.field_value_placeholder"),
                style=discord.TextStyle.long,
                default=field["value"],
                max_length=1024,
            )
            inline_input = ui.TextInput(
                label=_(interaction.locale, "embed-creator.field_inline_label"),
                placeholder=_(interaction.locale, "embed-creator.field_inline_placeholder"),
                required=False,
                default=str(int(field["inline"])),
                max_length=1,
            )
            text_inputs = [name_input, value_input, inline_input]

            modal = InputModal(_(interaction.locale, "embed-creator.edit_field"), *text_inputs)
            await _interaction.response.send_modal(modal)

            timed_out = await modal.wait()
            if timed_out:
                return

            inline = inline_input.value.strip() == "1"
            kwargs = {"index": index, "name": name_input.value, "value": value_input.value, "inline": inline}

            embed = discord.Embed.from_dict(copy.deepcopy(self.embed_dict))
            embed.set_field_at(**kwargs)

            if embed == self.embed:  # same field name, value
                await modal.interaction.response.defer()
                return

            self.update_field_buttons(embed.to_dict())
            self.base_view.embeds[self.embed_index] = embed
            self.base_view.set_view("embed")

            try:
                await modal.interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)
            except Exception as error:
                self.update_field_buttons()
                self.base_view.embeds[self.embed_index] = self.embed
                self.base_view.set_view("select")

                raise error
            else:
                self.embed = embed
                self.embed_dict = copy.deepcopy(embed.to_dict())

        self.base_view.set_select(
            _(interaction.locale, "embed-creator.edit_field_placeholder"), options, callback, "embed"
        )
        await interaction.response.edit_message(view=self.base_view)

    async def remove_field_callback(self, interaction: discord.Interaction):
        if len(self.embed.fields) == 1:
            self.embed.remove_field(0)

            self.embed_dict = copy.deepcopy(self.embed.to_dict())

            self.update_field_buttons()
            self.base_view.set_view("embed")

            await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)
            return

        options = [
            discord.SelectOption(
                label=f"{_(interaction.locale, 'embed-creator.field')} {i + 1}",
                description=field["name"][:100],
                value=str(i),
            )
            for i, field in enumerate(self.embed_dict["fields"])
        ]

        async def callback(_interaction: discord.Interaction):
            index = int(self.base_view.get_select_value())

            self.embed.remove_field(index)
            self.embed_dict = copy.deepcopy(self.embed.to_dict())
            self.update_field_buttons()
            self.base_view.set_view("embed")

            await _interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

        self.base_view.set_select(
            _(interaction.locale, "embed-creator.remove_field_placeholder"), options, callback, "embed"
        )
        await interaction.response.edit_message(view=self.base_view)

    async def clear_fields_callback(self, interaction: discord.Interaction):
        self.embed.clear_fields()

        self.embed_dict = self.embed.copy().to_dict()
        self.update_field_buttons()

        await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

    async def import_embed_callback(self, interaction: discord.Interaction):
        async def return_callback(_interaction: discord.Interaction, data):
            try:
                self.embed = discord.Embed.from_dict(data)
            except Exception as error:
                error.interaction = _interaction
                raise error

            self.embed_dict = copy.deepcopy(data)
            self.base_view.embeds[self.embed_index] = self.embed

            self.update_field_buttons()
            self.base_view.set_view("embed")

            await _interaction.response.edit_message(
                content=self.base_view.content, embeds=self.base_view.embeds, view=self.base_view
            )

        self.base_view.set_import(return_callback, "embed")
        self.base_view.set_view("import")

        await interaction.response.edit_message(view=self.base_view)

    async def export_embed_callback(self, interaction: discord.Interaction):
        await self.base_view.export_data(interaction, self.embed_dict)

    async def back_callback(self, interaction: discord.Interaction):
        self.base_view.set_view("message")

        await interaction.response.edit_message(view=self.base_view)


class MessageView(ui.View):
    if TYPE_CHECKING:
        send_button: ui.Button
        export_json_button: ui.Button
        edit_embed_button: ui.Button
        remove_embed_button: ui.Button
        clear_embeds_button: ui.Button
        add_embed_button: ui.Button

    def __init__(self, base_view: BaseView):
        super().__init__()
        self.locale = base_view.locale
        self.base_view = base_view

        self.setup_buttons()

    def add_button(
        self,
        name: str,
        style: discord.ButtonStyle = discord.ButtonStyle.gray,
        row: int | None = None,
        disabled: bool = False,
    ):
        button = ui.Button(label=_(self.locale, f"embed-creator.{name}"), style=style, row=row, disabled=disabled)
        button.callback = getattr(self, f"{name}_callback")

        setattr(self, f"{name}_button", button)

        self.add_item(button)

    def update_action_buttons(self):
        self.send_button.disabled = len(self.base_view.embeds) == 0 and not self.base_view.content
        self.export_json_button.disabled = len(self.base_view.embeds) == 0 and not self.base_view.content

    def update_embed_buttons(self):
        if self.base_view.embeds:
            self.edit_embed_button.disabled = False
            self.remove_embed_button.disabled = False
            self.clear_embeds_button.disabled = False
            if len(self.base_view.embeds) == 10:
                self.add_embed_button.disabled = True
            else:
                self.add_embed_button.disabled = False
        else:
            self.edit_embed_button.disabled = True
            self.remove_embed_button.disabled = True
            self.clear_embeds_button.disabled = True
            self.add_embed_button.disabled = False

    def setup_buttons(self):
        self.add_button("message_content", style=discord.ButtonStyle.blurple)
        self.add_button("add_embed", style=discord.ButtonStyle.blurple)
        self.add_button("edit_embed", style=discord.ButtonStyle.blurple, disabled=True)
        self.add_button("remove_embed", style=discord.ButtonStyle.blurple, disabled=True)
        self.add_button("clear_embeds", style=discord.ButtonStyle.red, disabled=True)
        self.add_button("reset", style=discord.ButtonStyle.red)
        self.add_button("import_data", style=discord.ButtonStyle.green)
        self.add_button("export_json", style=discord.ButtonStyle.green, disabled=True)
        self.add_button("send", style=discord.ButtonStyle.green, disabled=True)
        self.add_button("stop", style=discord.ButtonStyle.red)

    async def message_content_callback(self, interaction: discord.Interaction):
        text_input = ui.TextInput(
            label=_(interaction.locale, "embed-creator.message_content"),
            placeholder=_(interaction.locale, "embed-creator.message_content_placeholder"),
            style=discord.TextStyle.long,
            default=self.base_view.content,
            required=False,
            max_length=2000,
        )

        modal = InputModal(text_input.label, text_input)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        self.base_view.content = text_input.value
        self.update_action_buttons()

        await modal.interaction.response.edit_message(content=text_input.value)

    async def add_embed_callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=_(interaction.locale, "embed-creator.new_embed", index=len(self.base_view.embeds) + 1)
        )
        self.base_view.embeds.append(embed)

        self.update_embed_buttons()
        self.update_action_buttons()

        try:
            await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)
        except ValueError as error:
            error.interaction = interaction

            self.base_view.embeds.pop()
            self.update_embed_buttons()

            raise error

    async def edit_embed_callback(self, interaction: discord.Interaction):
        if len(self.base_view.embeds) == 1:
            self.base_view.set_embed(0)
            self.base_view.set_view("embed")

            await interaction.response.edit_message(view=self.base_view)
            return

        options = [
            discord.SelectOption(
                label=f"Embed {i + 1}",
                description=(
                    self.base_view.embeds[i].title[:100]
                    if self.base_view.embeds[i].title
                    else _(interaction.locale, "embed-creator.no_title")
                ),
                value=str(i),
            )
            for i in range(len(self.base_view.embeds))
        ]

        async def callback(_interaction: discord.Interaction):
            index = int(self.base_view.get_select_value())

            self.base_view.set_embed(index)
            self.base_view.set_view("embed")
            await _interaction.response.edit_message(view=self.base_view)

        self.base_view.set_select(_(interaction.locale, "embed-creator.edit_embed_select"), options, callback)
        await interaction.response.edit_message(view=self.base_view)

    async def remove_embed_callback(self, interaction: discord.Interaction):
        if len(self.base_view.embeds) == 1:
            self.base_view.embeds.pop(0)

            self.update_embed_buttons()
            self.update_action_buttons()

            await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)
            return

        options = [
            discord.SelectOption(
                label=f"Embed {i + 1}",
                description=(
                    self.base_view.embeds[i].title[:100]
                    if self.base_view.embeds[i].title
                    else _(interaction.locale, "embed-creator.no_title")
                ),
                value=str(i),
            )
            for i in range(len(self.base_view.embeds))
        ]

        async def callback(_interaction: discord.Interaction):
            index = int(self.base_view.get_select_value())
            self.base_view.embeds.pop(index)

            self.update_embed_buttons()
            self.update_action_buttons()

            self.base_view.set_view("message")
            await _interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

        self.base_view.set_select(_(interaction.locale, "embed-creator.remove_embed_select"), options, callback)

        await interaction.response.edit_message(view=self.base_view)

    async def clear_embeds_callback(self, interaction: discord.Interaction):
        self.base_view.embeds = []

        self.update_embed_buttons()
        self.update_action_buttons()

        await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

    async def reset_callback(self, interaction: discord.Interaction):
        self.base_view.content = None
        self.base_view.embeds = []

        self.update_embed_buttons()
        self.update_action_buttons()

        await interaction.response.edit_message(
            content=self.base_view.content, embeds=self.base_view.embeds, view=self.base_view
        )

    async def import_data_callback(self, interaction: discord.Interaction):
        async def return_callback(_interaction: discord.Interaction, data: dict):
            content = data.get("content") or None
            embeds = []

            if data.get("embeds"):
                for raw_embed in data["embeds"]:
                    embed = discord.Embed.from_dict(raw_embed)
                    if embed:
                        embeds.append(embed)

            if not content and not embeds:
                await _interaction.response.send_message(_(_interaction.locale, "embed-creator.empty_message_error"))
                return

            self.base_view.content = content
            self.base_view.embeds = embeds

            self.update_embed_buttons()
            self.update_action_buttons()

            self.base_view.set_view("message")

            await _interaction.response.edit_message(
                content=self.base_view.content, embeds=self.base_view.embeds, view=self.base_view
            )

        self.base_view.set_import(return_callback, "message")
        self.base_view.set_view("import")
        await interaction.response.edit_message(view=self.base_view)

    async def export_json_callback(self, interaction: discord.Interaction):
        data = {}

        if self.base_view.content:
            data["content"] = self.base_view.content
        if self.base_view.embeds:
            data["embeds"] = [embed.to_dict() for embed in self.base_view.embeds]

        await self.base_view.export_data(interaction, data)

    async def send_callback(self, interaction: discord.Interaction):
        self.base_view.set_view("send")
        await interaction.response.edit_message(view=self.base_view)

    async def stop_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.delete_original_response()


class BaseView(extensions.PrivateView):
    def __init__(self, interaction: discord.Interaction, session: aiohttp.ClientSession):
        super().__init__(original_interaction=interaction)

        self.locale = interaction.locale
        self.session = session

        self.content: str | None = None
        self.embeds: list[discord.Embed] = []

        self.views = {
            "message": MessageView(self),
            "embed": EmbedView(self),
            "select": SelectView(self, interaction.locale),
            "import": ImportView(self, interaction.locale),
            "send": SendView(self),
        }

        self.set_view("message")

    def set_view(self, key: str):
        self.clear_items()

        for item in self.views[key].children:
            self.add_item(item)

    def set_select(
        self, placeholder: str, options: list[discord.SelectOption], callback: Callable, return_to: str = "message"
    ):
        view = self.views["select"]
        view.return_to = return_to

        view.dynamic_select.placeholder = placeholder
        view.dynamic_select.callback = callback

        view.set_select_options(options)
        self.set_view("select")

    def set_embed(self, index: int):
        embed = self.embeds[index]
        view = self.views["embed"]

        view.embed = embed
        view.embed_dict = copy.deepcopy(embed.to_dict())
        view.embed_original = discord.Embed(title=_(self.locale, "embed-creator.new_embed", index=index)).to_dict()
        view.embed_index = index
        view.what_button.label = f"*Editing Embed {index + 1}"

        view.update_field_buttons()

    def set_import(self, return_callback: Callable, return_to: str) -> None:
        view = self.views["import"]
        view.return_callback = return_callback
        view.return_to = return_to

        if return_to == "message":  # hide import from message button if its not message json
            if not view.has_message_button:
                view.add_item(view.import_message)
                view.has_message_button = True
                view.remove_item(view.back_button)  # move back and stop button position ahead of message button
                view.add_item(view.back_button)
        else:
            if view.has_message_button:
                view.remove_item(view.import_message)
                view.has_message_button = False

    def get_select_value(self) -> str:
        return self.views["select"].dynamic_select.values[0]

    async def export_data(self, interaction: discord.Interaction, data: dict):
        text = json.dumps(data, indent=4)

        if len(text) > 1950:
            file = discord.File(io.BytesIO(text.encode()), filename="embed.json")
            await interaction.response.send_message(file=file, ephemeral=True)
        else:
            await interaction.response.send_message(f"```json\n{text}```", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error, item):
        if isinstance(error, errors.ConversionError):
            await error.interaction.response.send_message(_(interaction.locale, str(error)), ephemeral=True)
            return

        await self._last_interaction.channel.send(error)


class EmbedCreator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed-creator", description="Easy tool to create basic embeds.")
    @app_commands.checks.cooldown(2, 60, key=lambda i: (i.guild_id, i.user.id))
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only
    async def embed_creator(self, interaction: discord.Interaction):
        view = BaseView(interaction, interaction.client.session)  # type: ignore

        await interaction.response.send_message(view=view)


async def setup(bot):
    await bot.add_cog(EmbedCreator(bot))
