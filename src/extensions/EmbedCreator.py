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

from lib import extensions


MESSAGE_REGEX = re.compile(r"\bhttps://(canary.)?discord.com/channels/\d{17,20}/\d{17,20}/\d{17,20}\b")


class InputModal(ui.Modal):
    interaction: discord.Interaction

    def __init__(self, name, *text_inputs):
        super().__init__(title=f"{name} Modal", timeout=300.0)

        for text_input in text_inputs:
            self.add_item(text_input)

    async def on_submit(self, interaction):
        self.interaction = interaction


class ImportView(ui.View):
    if TYPE_CHECKING:
        return_callback: Callable
        return_to: str

    def __init__(self, base_view):
        super().__init__()
        self.base_view = base_view
        self.has_message_button = True

    @ui.button(label="Import JSON", style=discord.ButtonStyle.green)
    async def modal_button(self, interaction: discord.Interaction, button: ui.Button):
        text_input = ui.TextInput(label="JSON Data", placeholder="Paste JSON data here.", style=discord.TextStyle.long)

        modal = InputModal(button.label, text_input)
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

    @ui.button(label="Copy Message from URL", style=discord.ButtonStyle.green)
    async def message_button(self, interaction: discord.Interaction, button):
        text_input = ui.TextInput(
            label="Message Link",
            placeholder="https://discord.com/channels/XXXXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXXXX",
        )

        modal = InputModal("Import Message", text_input)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        try:
            if MESSAGE_REGEX.match(text_input.value) is None:
                await modal.interaction.response.send_message("Invalid message link", ephemeral=True)
                return

            value = text_input.value.split("/")[-3:]
            guild_id, channel_id, message_id = map(int, value)
            guild = interaction.guild

            if interaction.guild_id != guild_id:
                await modal.interaction.response.send_message("Invalid guild id", ephemeral=True)
                return

            channel = guild.get_channel(channel_id)
            if channel is None:
                await modal.interaction.response.send_message("Channel not found", ephemeral=True)

            message = await channel.fetch_message(message_id)

            data = {}
            if message.content:
                data["content"] = message.content
            if message.embeds:
                data["embeds"] = [embed.to_dict() for embed in message.embeds]

        except Exception as error:
            error.interaction = modal.interaction
            raise error

        await self.return_callback(modal.interaction, data)

    @ui.button(label="Back", style=discord.ButtonStyle.blurple)
    async def back_button(self, interaction: discord.Interaction, button):
        self.base_view.set_view(self.return_to)

        await interaction.response.edit_message(view=self.base_view)


class SelectView(ui.View):
    if TYPE_CHECKING:
        return_to: str

    def __init__(self, base_view):
        super().__init__()
        self.base_view = base_view
        self.options_list = []  # list of options in chunks of 25
        self.has_page_buttons = True
        self.page_index = 0

        self.dynamic_select = ui.Select()
        self.what_button = ui.Button(disabled=True)

        self.add_item(self.what_button)
        self.add_item(self.dynamic_select)

    def set_select_options(self, options: list[discord.SelectOption]):
        MAX_OPTIONS = 25  # max options in a select

        if len(options) > 25:
            if not self.has_page_buttons:
                self.add_item(self.left_button)
                self.add_item(self.what_button)
                self.add_item(self.right_button)
                self.has_page_buttons = True

                self.remove_item(self.back_button)
                self.add_item(self.back_button)

            self.options_list = [options[i : i + MAX_OPTIONS] for i in range(0, len(options), MAX_OPTIONS)]
            self.dynamic_select.options = self.options_list[0]
            self.page_index = 0

            self.left_button.disabled = True
            self.right_button.disabled = False
            self.what_button.label = f"Page 1/{len(self.options_list)}"

        else:
            if self.has_page_buttons:
                self.remove_item(self.left_button)
                self.remove_item(self.what_button)
                self.remove_item(self.right_button)
                self.has_page_buttons = False

            self.dynamic_select.options = options

    @ui.button(label="<")
    async def left_button(self, interaction: discord.Interaction, button):
        self.page_index -= 1
        if self.page_index == 0:
            button.disabled = True

        self.right_button.disabled = False
        self.what_button.label = f"Page {self.page_index + 1}/{len(self.options_list)}"
        self.dynamic_select.options = self.options_list[self.page_index]

        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label=">")
    async def right_button(self, interaction: discord.Interaction, button: ui.Button):
        self.page_index += 1
        if self.page_index == len(self.options_list) - 1:
            button.disabled = True

        self.left_button.disabled = False
        self.what_button.label = f"Page {self.page_index + 1}/{len(self.options_list)}"
        self.dynamic_select.options = self.options_list[self.page_index]

        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Back", style=discord.ButtonStyle.blurple)
    async def back_button(self, interaction: discord.Interaction, button):
        self.base_view.set_view(self.return_to)
        await interaction.response.edit_message(view=self.base_view)


class SendView(ui.View):
    def __init__(self, base_view):
        super().__init__()
        self.base_view = base_view

    @ui.button(label="Send to Channel", style=discord.ButtonStyle.green)
    async def channel_button(self, interaction: discord.Interaction, button):
        placeholder = "Select the Channel to send to..."
        guild = interaction.guild

        options = [
            discord.SelectOption(
                label=f"#{channel.name[:99]}",
                description=f"f{channel.category.name} {channel.id}",
                value=str(channel.id),
            )
            for channel in guild.text_channels
            if channel.permissions_for(guild.me).send_messages
        ]

        async def callback(_interaction: discord.Interaction):
            channel_id = int(self.base_view.get_select_value())

            channel = guild.get_channel(channel_id)
            if channel is None:
                await interaction.response.send_message("Could not find channel.")
                return

            await channel.send(content=self.base_view.content, embeds=self.base_view.embeds)

            await _interaction.response.send_message(content=f"Sent message to {channel.mention}!", ephemeral=True)

        self.base_view.set_select(placeholder, options, callback, "send")
        self.base_view.set_view("select")

        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Send to Webhook", style=discord.ButtonStyle.green)
    async def webhook_button(self, interaction, button):
        text_input = ui.TextInput(
            label="Webhook URL",
            placeholder="e.g. https://discord.com/api/webhooks/XXXXXXXXXXXXXXXXXX/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        )

        modal = InputModal(button.label, text_input)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        webhook_url = text_input.value
        try:
            webhook = discord.Webhook.from_url(webhook_url, session=self.base_view.session)
            await webhook.send(content=self.base_view.content, embeds=self.base_view.embeds)
        except Exception as error:
            error.interaction = modal.interaction
            raise error

        await modal.interaction.response.send_message(content="Sent message to a Webhook!", ephemeral=True)

    @ui.button(label="Back", style=discord.ButtonStyle.blurple)
    async def back_button(self, interaction: discord.Interaction, button):
        self.base_view.set_view("message")
        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Stop", style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        await interaction.delete_original_response()


class EmbedView(ui.View):
    def __init__(self, base_view):
        super().__init__()
        self.base_view = base_view

        self.embed: discord.Embed | None = None  # the following are changed often
        self.embed_dict: dict | None = None  # used for default values and reverting changes
        self.embed_original: discord.Embed | None = None  # for resetting
        self.embed_index: int | None = None  # index in self.embeds

        self.what_button = ui.Button(disabled=True)

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

    async def show_modal(self, interaction, button, *text_inputs: ui.TextInput, method: str = None):
        name = button.label.lower()

        # old_values = []
        for text_input in text_inputs:
            old = self.embed_dict.get(name, None)
            if old is not None:
                if hasattr(text_input, "key"):
                    old = old.get(text_input.key, None)

            text_input.default = old

        modal = InputModal(button.label, *text_inputs)
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
                setattr(self.embed, name, new_values[0])

            await modal.interaction.response.edit_message(embeds=self.base_view.embeds)
            self.embed_dict = self.embed.to_dict()
        except Exception as error:
            self.embed = discord.Embed.from_dict(self.embed_dict)
            self.base_view.embeds[self.embed_index] = self.embed
            raise error

    @ui.button(label="Title", style=discord.ButtonStyle.blurple)
    async def title_button(self, interaction: discord.Interaction, button: ui.Button):
        text_input = ui.TextInput(
            label=button.label, placeholder="The title of the embed.", required=False, max_length=256
        )

        await self.show_modal(interaction, button, text_input)

    @ui.button(label="URL", style=discord.ButtonStyle.blurple)
    async def url_button(self, interaction: discord.Interaction, button: ui.Button):
        text_input = ui.TextInput(label=button.label, placeholder="The URL of the embed.", required=False)

        await self.show_modal(interaction, button, text_input)

    @ui.button(label="Description", style=discord.ButtonStyle.blurple)
    async def description_button(self, interaction, button):
        text_input = ui.TextInput(
            label=button.label,
            placeholder="The description of the embed.",
            style=discord.TextStyle.long,
            required=False,
            max_length=4096,
        )

        await self.show_modal(interaction, button, text_input)

    @ui.button(label="Color", style=discord.ButtonStyle.blurple)
    async def color_button(self, interaction, button):
        text_input = ui.TextInput(label=button.label, placeholder='A hex string like "#ffab12".', required=False)
        text_input.convert = lambda x: int(x.lstrip("#"), base=16) if x else None

        await self.show_modal(interaction, button, text_input)

    @discord.ui.button(label="Timestamp", style=discord.ButtonStyle.blurple)
    async def timestamp_button(self, interaction, button):
        text_input = discord.ui.TextInput(
            label=button.label, placeholder='A unix timestamp or a number like "1659876635".', required=False
        )

        def convert(x: str) -> datetime.datetime:
            if x == "now":
                return discord.utils.utcnow()

            try:
                return datetime.datetime.fromtimestamp(int(x), datetime.timezone.utc)
            except ValueError:
                return datetime.datetime.strptime(x, "%Y-%m-%dT%H:%M:%S%z")

        text_input.convert = convert
        await self.show_modal(interaction, button, text_input)

    @ui.button(label="Author", style=discord.ButtonStyle.blurple)
    async def author_button(self, interaction, button):
        name_input = ui.TextInput(label="Name", placeholder="The name of the author.", required=False)
        name_input.key = "name"

        url_input = ui.TextInput(label="URL", placeholder="The URL for the author.", required=False)
        url_input.key = "url"

        icon_input = ui.TextInput(label="Icon URL", placeholder="The URL for the author icon.", required=False)
        icon_input.key = "icon_url"

        text_inputs = [name_input, url_input, icon_input]
        await self.show_modal(interaction, button, *text_inputs, method="set_author")

    @ui.button(label="Thumbnail", style=discord.ButtonStyle.blurple)
    async def thumbnail_button(self, interaction, button):
        text_input = ui.TextInput(label=button.label, placeholder="The source URL for the thumbnail.", required=False)
        text_input.key = "url"

        await self.show_modal(interaction, button, text_input, method="set_thumbnail")

    @ui.button(label="Image", style=discord.ButtonStyle.blurple)
    async def image_button(self, interaction, button):
        text_input = ui.TextInput(label=button.label, placeholder="The source URL for the image.", required=False)
        text_input.key = "url"

        await self.show_modal(interaction, button, text_input, method="set_image")

    @ui.button(label="Footer", style=discord.ButtonStyle.blurple)
    async def footer_button(self, interaction: discord.Interaction, button: ui.Button):
        text_input = ui.TextInput(label="Text", placeholder="The footer text.", required=False, max_length=2048)
        text_input.key = "text"

        icon_input = ui.TextInput(label="Icon URL", placeholder="The URL of the footer icon.", required=False)
        icon_input.key = "icon_url"

        text_inputs = [text_input, icon_input]
        await self.show_modal(interaction, button, *text_inputs, method="set_footer")

    @ui.button(label="Add Field", style=discord.ButtonStyle.blurple)
    async def add_field_button(self, interaction, button):
        name_input = ui.TextInput(label="Field Name", placeholder="The name of the field.", max_length=256)
        value_input = ui.TextInput(
            label="Field Value", placeholder="The value of the field.", style=discord.TextStyle.long, max_length=1024
        )
        inline_input = ui.TextInput(
            label="Field Inline", placeholder='Type "1" for inline, otherwise not inline.', required=False, max_length=1
        )
        index_input = ui.TextInput(
            label="Field Index",
            placeholder="Insert before field (n+1), default at the end.",
            required=False,
            max_length=2,
        )

        modal = InputModal(button.label, *[name_input, value_input, inline_input, index_input])
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

    @ui.button(label="Edit Field", style=discord.ButtonStyle.blurple)
    async def edit_field_button(self, interaction, button):
        placeholder = "Select the Field to edit..."

        options = [
            discord.SelectOption(label=f"Field {i + 1}", description=field["name"][:100], value=str(i))
            for i, field in enumerate(self.embed_dict["fields"])
        ]

        async def callback(_interaction: discord.Interaction):
            index = int(self.base_view.get_select_value())
            field = self.embed_dict["fields"][index]

            name_input = ui.TextInput(
                label="Field Name", placeholder="The name of the field.", default=field["name"], max_length=1024
            )
            value_input = ui.TextInput(
                label="Field Value",
                placeholder="The value of the field.",
                style=discord.TextStyle.long,
                default=field["value"],
            )
            inline_input = ui.TextInput(
                label="Field Inline (Optional)",
                placeholder='Type "1" for inline, otherwise not inline.',
                required=False,
                default=str(int(field["inline"])),
                max_length=1,
            )
            text_inputs = [name_input, value_input, inline_input]

            modal = InputModal(button.label, *text_inputs)
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

        self.base_view.set_select(placeholder, options, callback, "embed")
        self.base_view.set_view("select")
        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Remove Field", style=discord.ButtonStyle.blurple)
    async def remove_field_button(self, interaction: discord.Interaction, button):
        if len(self.embed.fields) == 1:
            self.embed.remove_field(0)

            self.embed_dict = copy.deepcopy(self.embed.to_dict())

            self.update_field_buttons()
            self.base_view.set_view("embed")

            await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)
            return

        placeholder = "Select the Field to remove..."
        options = [
            discord.SelectOption(label=f"Field {i + 1}", description=field["name"][:100], value=str(i))
            for i, field in enumerate(self.embed_dict["fields"])
        ]

        async def callback(_interaction: discord.Interaction):
            index = int(self.base_view.get_select_value())

            self.embed.remove_field(index)
            self.embed_dict = copy.deepcopy(self.embed.to_dict())
            self.update_field_buttons()
            self.base_view.set_view("embed")

            await _interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

        self.base_view.set_select(placeholder, options, callback, "embed")
        self.base_view.set_view("select")
        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Clear Fields", style=discord.ButtonStyle.red)
    async def clear_fields_button(self, interaction: discord.Interaction, button):
        self.embed.clear_fields()

        self.embed_dict = self.embed.copy().to_dict()
        self.update_field_buttons()

        await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

    @ui.button(label="Reset", style=discord.ButtonStyle.red)
    async def reset_button(self, interaction: discord.Interaction, button):
        self.embed = discord.Embed.from_dict(self.embed_original.copy())

        self.base_view.embeds[self.embed_index] = self.embed
        self.embed_dict = copy.deepcopy(self.embed_original)
        self.update_field_buttons()
        await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

    @ui.button(label="Import Embed", style=discord.ButtonStyle.green, row=3)
    async def import_button(self, interaction: discord.Interaction, button):
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

    @ui.button(label="Export Embed", style=discord.ButtonStyle.green, row=3)
    async def export_button(self, interaction: discord.Embed, button):
        await self.base_view.export_data(interaction, self.embed_dict)

    @ui.button(label="Back", style=discord.ButtonStyle.blurple, row=4)
    async def back_button(self, interaction: discord.Interaction, button):
        self.base_view.set_view("message")

        await interaction.response.edit_message(view=self.base_view)


class MessageView(ui.View):
    def __init__(self, base_view: BaseView):
        super().__init__()
        self.base_view = base_view

    def update_action_buttons(self):
        self.send_button.disabled = len(self.base_view.embeds) == 0 and not self.base_view.content
        self.export_button.disabled = len(self.base_view.embeds) == 0 and not self.base_view.content

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

    @ui.button(label="Content", style=discord.ButtonStyle.blurple)
    async def content_button(self, interaction, button):
        text_input = ui.TextInput(
            label=button.label,
            placeholder="The actual contents of the message.",
            style=discord.TextStyle.long,
            default=self.base_view.content,
            required=False,
            max_length=2000,
        )

        modal = InputModal(button.label, text_input)
        await interaction.response.send_modal(modal)

        timed_out = await modal.wait()
        if timed_out:
            return

        self.base_view.content = text_input.value
        self.update_action_buttons()

        await modal.interaction.response.edit_message(content=text_input.value)

    @ui.button(label="Add Embed", style=discord.ButtonStyle.blurple)
    async def add_embed_button(self, interaction: discord.Interaction, button):
        embed = discord.Embed(title=f"New embed {len(self.base_view.embeds) + 1}")
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

    @ui.button(label="Edit Embed", style=discord.ButtonStyle.blurple, disabled=True)
    async def edit_embed_button(self, interaction: discord.Interaction, button):
        if len(self.base_view.embeds) == 1:
            self.base_view.set_embed(0)
            self.base_view.set_view("embed")

            await interaction.response.edit_message(view=self.base_view)
            return

        placeholder = "Select the Embed to edit..."

        options = [
            discord.SelectOption(
                label=f"Embed {i + 1}",
                description=(self.base_view.embeds[i].title[:100] if self.base_view.embeds[i].title else "(no title)"),
                value=str(i),
            )
            for i in range(len(self.base_view.embeds))
        ]

        async def callback(_interaction: discord.Interaction):
            index = int(self.base_view.get_select_value())

            self.base_view.set_embed(index)
            self.base_view.set_view("embed")
            await _interaction.response.edit_message(view=self.base_view)

        self.base_view.set_select(placeholder, options, callback)
        self.base_view.set_view("select")
        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Remove Embed", style=discord.ButtonStyle.blurple, disabled=True)
    async def remove_embed_button(self, interaction: discord.Interaction, button):
        if len(self.base_view.embeds) == 1:
            self.base_view.embeds.pop(0)

            self.update_embed_buttons()
            self.update_action_buttons()

            await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)
            return

        placeholder = "Select the Embed to remove..."
        options = [
            discord.SelectOption(
                label=f"Embed {i + 1}",
                description=(self.base_view.embeds[i].title[:100] if self.base_view.embeds[i].title else "(no title)"),
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

        self.base_view.set_select(placeholder, options, callback)
        self.base_view.set_view("select")

        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Clear Embeds", style=discord.ButtonStyle.red, disabled=True)
    async def clear_embeds_button(self, interaction, button):
        self.base_view.embeds = []

        self.update_embed_buttons()
        self.update_action_buttons()

        await interaction.response.edit_message(embeds=self.base_view.embeds, view=self.base_view)

    @ui.button(label="Reset", style=discord.ButtonStyle.red)
    async def reset_button(self, interaction: discord.Interaction, button):
        self.base_view.content = None
        self.base_view.embeds = []

        self.update_embed_buttons()
        self.update_action_buttons()

        await interaction.response.edit_message(
            content=self.base_view.content, embeds=self.base_view.embeds, view=self.base_view
        )

    @ui.button(label="Import Data [2]", style=discord.ButtonStyle.green)
    async def import_button(self, interaction: discord.Interaction, button):
        async def return_callback(_interaction: discord.Interaction, data):
            if "content" in data and data["content"]:
                self.base_view.content = data["content"]
            else:
                self.base_view.content = None

            if "embeds" in data and data["embeds"]:
                self.base_view.embeds = [discord.Embed.from_dict(embed) for embed in data["embeds"]]
            else:
                self.base_view.embeds = None

            self.update_embed_buttons()
            self.update_action_buttons()

            self.base_view.set_view("message")

            await _interaction.response.edit_message(
                content=self.base_view.content, embeds=self.base_view.embeds, view=self.base_view
            )

        self.base_view.set_import(return_callback, "message")
        self.base_view.set_view("import")
        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Export JSON", style=discord.ButtonStyle.green, disabled=True)
    async def export_button(self, interaction: discord.Interaction, button):
        data = {}

        if self.base_view.content:
            data["content"] = self.base_view.content
        if self.base_view.embeds:
            data["embeds"] = [embed.to_dict() for embed in self.base_view.embeds]

        await self.base_view.export_data(interaction, data)

    @ui.button(label="Send [3]", style=discord.ButtonStyle.green, disabled=True)
    async def send_button(self, interaction: discord.Interaction, button):
        self.base_view.set_view("send")
        await interaction.response.edit_message(view=self.base_view)

    @ui.button(label="Stop", style=discord.ButtonStyle.red)
    async def stop_button(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        await interaction.delete_original_response()


class BaseView(extensions.PrivateView):
    def __init__(self, interaction: discord.Interaction):
        super().__init__(original_interaction=interaction)

        self.content: str | None = None
        self.embeds: list[discord.Embed] = []

        self.views = {
            "message": MessageView(self),
            "embed": EmbedView(self),
            "select": SelectView(self),
            "import": ImportView(self),
            "send": SendView(self),
        }

        self.set_view("message")

    def set_view(self, key: str):
        self.clear_items()

        for item in self.views[key].children:
            self.add_item(item)

    def set_select(
        self, placeholder: str, options: list[discord.SelectOption], callback: Callable, return_to: str = None
    ):
        view = self.views["select"]
        view.return_to = return_to or "message"

        select = view.dynamic_select
        select.placeholder = placeholder
        select.callback = callback

        view.set_select_options(options)

    def set_embed(self, index: int):
        embed = self.embeds[index]
        view = self.views["embed"]

        view.embed = embed
        view.embed_dict = copy.deepcopy(embed.to_dict())
        view.embed_original = discord.Embed(title=f"New embed {index + 1}").to_dict()
        view.embed_index = index
        view.what_button.label = f"*Editing Embed {index + 1}"

        view.update_field_buttons()

    def set_import(self, return_callback: Callable, return_to: str) -> None:
        view = self.views["import"]
        view.return_callback = return_callback
        view.return_to = return_to

        if return_to == "message":  # hide import from message button if its not message json
            if not view.has_message_button:
                view.add_item(view.message_button)
                view.has_message_button = True
                view.remove_item(view.back_button)  # move back and stop button position ahead of message button
                view.add_item(view.back_button)
        else:
            if view.has_message_button:
                view.remove_item(view.message_button)
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

    async def on_error(self, interaction, error, item):
        print(error)

        await self._last_interaction.channel.send(error)


class MessageMaker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embed-creator")
    async def embed_creator(self, interaction: discord.Interaction):
        view = BaseView(interaction)

        await interaction.response.send_message(view=view)
        await view.wait()


async def setup(bot):
    await bot.add_cog(MessageMaker(bot))
