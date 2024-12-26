from datetime import datetime
import re
from interactions.ext.paginators import Paginator
from interactions import (
    ActionRow,
    Extension,
    Modal,
    ModalContext,
    OptionType,
    ParagraphText,
    ShortText,
    component_callback,
    listen,
    modal_callback,
    slash_command,
    slash_option,
    SlashContext,
    Embed,
    Button,
    ButtonStyle,
    ComponentContext,
)
from database import RedisDB

class ColorConverter:
    @staticmethod
    def from_str(color: str) -> int:
        color = color.replace(' ', '').lower()
        if color.startswith('#'):
            color = color[1:]
            if len(color) == 3:
                color = ''.join(c * 2 for c in color)
            if len(color) == 6:
                return int(color, 16)

        rgb_match = re.match(r'rgb\((\d+),(\d+),(\d+)\)', color)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            return (r << 16) + (g << 8) + b

        colors = {
            'red': 0xFF0000,
            'green': 0x00FF00,
            'blue': 0x0000FF,
            'yellow': 0xFFFF00,
            'purple': 0x800080,
            'pink': 0xFFC0CB,
            'orange': 0xFFA500,
            'black': 0x000000,
            'white': 0xFFFFFF,
            'gray': 0x808080,
            'brown': 0x964B00
        }
        if color in colors:
            return colors[color]
        try:
            return int(color, 16)
        except ValueError:
            raise ValueError(f"Invalid color format: {color}")

class EmbedExtension(Extension):
    FORCE_OVERRIDE_USER_ID = ["686107711829704725", "708812851229229208", "1259678639159644292", "1168346688969252894"]

    def __init__(self, bot):
        self.bot = bot
        self.db = RedisDB(db=122)
        self.db_whitelist = RedisDB(db=1)
        self.embed_limit = 100
    
    async def is_user_whitelisted(self, user_id):
        if str(user_id) in [str(id) for id in self.FORCE_OVERRIDE_USER_ID]: return True
        return self.db_whitelist.redis.sismember(self.WHITELIST_KEY, str(user_id))

    def get_embed_buttons(self, name: str) -> list[ActionRow]:
        row1 = ActionRow(
            Button(
                style=ButtonStyle.PRIMARY,
                label="Basic Info",
                custom_id=f"embed_basic_info:{name}"
            ),
            Button(
                style=ButtonStyle.SUCCESS,
                label="Fields",
                custom_id=f"embed_fields:{name}"
            ),
            Button(
                style=ButtonStyle.SECONDARY,
                label="Images",
                custom_id=f"embed_images:{name}"
            ),
            Button(
                style=ButtonStyle.DANGER,
                label="Author/Footer",
                custom_id=f"embed_author_footer:{name}"
            )
        )
        
        row2 = ActionRow(
            Button(
                style=ButtonStyle.PRIMARY,
                label="Save",
                custom_id=f"embed_save:{name}"
            ),
            Button(
                style=ButtonStyle.SUCCESS,
                label="Finalize",
                custom_id=f"embed_finalize:{name}"
            ),
            Button(
                style=ButtonStyle.SECONDARY,
                label="Register Event",
                custom_id=f"embed_event:{name}"
            )
        )
        
        return [row1, row2]

    def serialize_embed(self, embed: Embed) -> dict:
        data = {
            "title": embed.title,
            "description": embed.description,
            "color": embed.color,
            "url": embed.url,
            "timestamp": embed.timestamp.isoformat() if embed.timestamp else None,
            "fields": [
                {
                    "name": field.name,
                    "value": field.value,
                    "inline": field.inline
                }
                for field in embed.fields
            ],
            "author": {
                "name": embed.author.name if embed.author else None,
                "url": embed.author.url if embed.author else None,
                "icon_url": embed.author.icon_url if embed.author else None
            } if embed.author else None,
            "footer": {
                "text": embed.footer.text if embed.footer else None,
                "icon_url": embed.footer.icon_url if embed.footer else None
            } if embed.footer else None,
            "image": embed.image.url if embed.image else None,
            "thumbnail": embed.thumbnail.url if embed.thumbnail else None,
            "event_config": None
        }
        return data

    def deserialize_embed(self, data: dict) -> Embed:
        embed = Embed(
            title=data.get("title"),
            description=data.get("description"),
            color=data.get("color"),
            url=data.get("url")
        )
        
        if data.get("timestamp"): embed.timestamp = datetime.fromisoformat(data["timestamp"])
        for field in data.get("fields", []): embed.add_field(name=field["name"], value=field["value"], inline=field["inline"])
        if data.get("author"): embed.set_author(name=data["author"].get("name"), url=data["author"].get("url"), icon_url=data["author"].get("icon_url"))
        if data.get("footer"): embed.set_footer(text=data["footer"].get("text"), icon_url=data["footer"].get("icon_url"))
        if data.get("image"): embed.set_image(data["image"])
        if data.get("thumbnail"): embed.set_thumbnail(data["thumbnail"])
        return embed

    def get_embed_key(self, user_id: str, name: str) -> str:
        return f"embed:{user_id}:{name}"

    @slash_command(
        name="embed_create",
        description="Create a new embed (like Mimu's /embed create)."
    )
    @slash_option(
        name="name",
        description="Name for this embed (≤16 chars, no spaces)",
        required=True,
        opt_type=OptionType.STRING
    )
    async def embed_create(self, ctx: SlashContext, name: str):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to create embeds.", ephemeral=True)
            return
        await ctx.defer(ephemeral=False)        
        if len(name) > 16 or " " in name:
            await ctx.send(
                "Embed name must be ≤16 characters and cannot contain spaces!",
                ephemeral=True
            )
            return            
        key = self.get_embed_key(str(ctx.author.id), name)
        existing_embed = await self.db.get(key)
        if existing_embed:
            await ctx.send(
                f"An embed template with the name '{name}' already exists. Please choose a different name.",
                ephemeral=True
            )
            return
        embed = Embed(
            title="Example Embed Title",
            description="This is an example description.\nIt can have multiple lines!\n\nYou can use [links](https://discord.com) and other markdown!",
            color=0xA54962,
        )
        embed.set_image("https://img.freepik.com/premium-photo/cute-anime-girl-wallpaper_776894-106686.jpg")
        embed.set_thumbnail("https://img.freepik.com/premium-photo/cute-anime-girl-wallpaper_776894-106686.jpg")
        embed.set_author(
            name="Example Author",
            url="https://discord.com",
            icon_url="https://img.freepik.com/premium-photo/cute-anime-girl-wallpaper_776894-106686.jpg"
        )
        embed.set_footer(
            text="Example Footer • You can add timestamps too!",
            icon_url="https://img.freepik.com/premium-photo/cute-anime-girl-wallpaper_776894-106686.jpg"
        )
        # embed.timestamp = datetime.now()
        buttons = self.get_embed_buttons(name)
        await ctx.send(
            embed=embed,
            components=buttons
        )
    
    @slash_command(
        name="embed_load",
        description="Load a saved embed template"
    )
    @slash_option(
        name="name",
        description="Name of the saved embed",
        required=True,
        opt_type=OptionType.STRING
    )
    async def embed_load(self, ctx: SlashContext, name: str):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to load embeds.", ephemeral=True)
            return
        await ctx.defer(ephemeral=False)
        key = self.get_embed_key(str(ctx.author.id), name)
        embed_data = await self.db.get(key)
        if not embed_data:
            await ctx.send(f"No saved embed template found with name '{name}'", ephemeral=True)
            return
        embed = self.deserialize_embed(embed_data)
        buttons = self.get_embed_buttons(name)
        await ctx.send(embed=embed, components=buttons)

    @slash_command(
        name="embed_list", 
        description="List all saved embed templates",
    )
    async def embed_list(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to list embeds.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        pattern = f"embed:{ctx.author.id}:*"
        embed_keys = self.db.list_keys(pattern)
        if not embed_keys:
            await ctx.send("No saved embed templates found.", ephemeral=True)
            return
        embeds = []
        for key in embed_keys:
            name = key.split(":")[-1]
            embed_data = await self.db.get(key)
            if embed_data:
                embed = self.deserialize_embed(embed_data)
                embed._template_name = name
                embeds.append(embed)        
        async def load_template(ctx: ComponentContext):
            current_embed = embeds[paginator.page_index]
            embed_name = current_embed._template_name
            key = self.get_embed_key(str(ctx.author.id), embed_name)
            embed_data = await self.db.get(key)
            if embed_data:
                embed = self.deserialize_embed(embed_data)
                await ctx.send(embed=embed, components=self.get_embed_buttons(embed_name))
            else:
                await ctx.send("Could not load embed template.", ephemeral=True)
            return None
        paginator = Paginator.create_from_embeds(
            self.bot,
            *embeds,
            timeout=300
        )
        paginator.show_callback_button = True
        paginator.callback = load_template
        await paginator.send(ctx)

    @slash_command(
        name="embed_flush",
        description="Delete all saved embed templates"
    )
    async def embed_flush(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to flush the embed database.", ephemeral=True)
            return
        pattern = f"embed:{ctx.author.id}:*"
        embed_keys = self.db.list_keys(pattern)
        if not embed_keys:
            await ctx.send("No saved embed templates to flush.", ephemeral=True)
            return
        for key in embed_keys:
            self.db.delete(key)
        await ctx.send(f"Successfully deleted {len(embed_keys)} embed templates.", ephemeral=True)

    @slash_command(
        name="embed_edit",
        description="Edit an existing embed template"
    )
    @slash_option(
        name="name",
        description="Name of the embed to edit",
        required=True,
        opt_type=OptionType.STRING
    )
    async def embed_edit(self, ctx: SlashContext, name: str):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to edit embeds.", ephemeral=True)
            return
        await ctx.defer(ephemeral=False)
        key = self.get_embed_key(str(ctx.author.id), name)
        embed_data = await self.db.get(key)
        if not embed_data:
            await ctx.send(f"No embed template found with name '{name}'", ephemeral=True)
            return
        embed = self.deserialize_embed(embed_data)
        event_info = ""
        if embed_data.get("event_config"):
            event_config = embed_data["event_config"]
            channel_id = event_config.get("channel_id")
            is_finalized = event_config.get("is_finalized", False)
            event_info = (
                f"\n\nℹ️ This embed has an event configuration:\n"
                f"• Type: {event_config.get('event_type')}\n"
                f"• Channel: <#{channel_id}>\n"
                f"• Status: {'Finalized' if is_finalized else 'Not Finalized'}"
            )
        buttons = self.get_embed_buttons(name)
        await ctx.send(
            content=f"Editing embed template '{name}'{event_info}",
            embed=embed,
            components=buttons
        )

    @component_callback(re.compile(r"embed_basic_info:(.+)"))
    async def embed_basic_info(self, ctx: ComponentContext):
        embed_name = ctx.custom_id.split(":")[1]
        print(f"embed_basic_info: {embed_name}")
        message = ctx.message
        embed = message.embeds[0] if message.embeds else None
        current_title = ""
        current_description = ""
        current_color = ""
        if embed:
            current_title = embed.title or ""
            current_description = embed.description or ""
            if embed.color: current_color = f"#{embed.color:06x}"
        modal = Modal(
            ShortText(
                label="Title (type 'remove' to clear)",
                custom_id="title",
                required=False,
                placeholder="Enter or 'remove'",
                value=current_title
            ),
            ParagraphText(
                label="Description (use {newline} for line breaks)",
                custom_id="description",
                required=False,
                placeholder="Description",
                value=current_description.replace("\n", "{newline}")
            ),
            ShortText(
                label="Color (hex or name)",
                custom_id="color",
                required=False,
                placeholder="#ff0000 or red",
                value=current_color
            ),
            title="Edit Basic Info",
            custom_id=f"embed_basic_info_modal:{embed_name}"
        )
        await ctx.send_modal(modal)
    
    @modal_callback(re.compile(r"embed_basic_info_modal:(.+)"))
    async def embed_basic_info_modal(self, ctx: ModalContext):
        embed_name = ctx.custom_id.split(":")[1]
        title = ctx.responses.get("title")
        description = ctx.responses.get("description")
        color = ctx.responses.get("color")
        print(f"embed_basic_info_modal: {embed_name} {title} {description} {color}")
        message = ctx.message
        if not message:
            await ctx.send("Couldn't find the original message.", ephemeral=True)
            return    
        embed = message.embeds[0] if message.embeds else None
        if not embed:
            await ctx.send("Couldn't find the embed.", ephemeral=True)
            return
        if title:
            if title.lower() == 'remove':
                embed.title = None
            else:
                embed.title = title
        if description:
            embed.description = description.replace("{newline}", "\n")
        if color:
            try:
                embed.color = ColorConverter.from_str(color)
            except ValueError as e:
                await ctx.send(str(e), ephemeral=True)
                return
        await ctx.defer(edit_origin=True)
        await message.edit(
            embed=embed,
            components=self.get_embed_buttons(embed_name)
        )
    
    @component_callback(re.compile(r"embed_fields:(.+)"))
    async def embed_fields(self, ctx: ComponentContext):
        embed_name = ctx.custom_id.split(":")[1]
        print(f"embed_fields: {embed_name}")
        modal = Modal(
            ShortText(
                label="Field Title",
                custom_id="field_title",
                required=True,
            ),
            ParagraphText(
                label="Field Value",
                custom_id="field_value",
                required=True,
                placeholder="Enter field content"
            ),
            ShortText(
                label="Inline (true/false)",
                custom_id="field_inline",
                required=False,
                placeholder="true or false"
            ),
            title="Add Field",
            custom_id=f"embed_fields_modal:{embed_name}"
        )
        await ctx.send_modal(modal)
    
    @modal_callback(re.compile(r"embed_fields_modal:(.+)"))
    async def embed_fields_modal(self, ctx: ModalContext):
        embed_name = ctx.custom_id.split(":")[1]
        field_title = ctx.responses.get("field_title")
        field_value = ctx.responses.get("field_value")
        field_inline = ctx.responses.get("field_inline", "false").lower() == "true"
        message = ctx.message
        if not message:
            await ctx.send("Couldn't find the original message.", ephemeral=True)
            return    
        embed = message.embeds[0] if message.embeds else None
        if not embed:
            await ctx.send("Couldn't find the embed.", ephemeral=True)
            return
        try:
            embed.add_field(
                name=field_title,
                value=field_value,
                inline=field_inline
            )
            await ctx.defer(edit_origin=True)
            await message.edit(
                embed=embed,
                components=self.get_embed_buttons(embed_name)
            )
        except ValueError as e:
            await ctx.send(f"Error adding field: {str(e)}", ephemeral=True)

    @component_callback(re.compile(r"embed_images:(.+)"))
    async def embed_images(self, ctx: ComponentContext):
        embed_name = ctx.custom_id.split(":")[1]
        print(f"embed_images: {embed_name}")
        modal = Modal(
            ShortText(
                label="Main Image URL",
                custom_id="main_image",
                required=False,
                placeholder="URL for main image (type 'remove' to clear)"
            ),
            ShortText(
                label="Thumbnail URL",
                custom_id="thumbnail",
                required=False,
                placeholder="URL for thumbnail (type 'remove' to clear)"
            ),
            title="Edit Images",
            custom_id=f"embed_images_modal:{embed_name}"
        )
        await ctx.send_modal(modal)
    
    @component_callback(re.compile(r"embed_event:(.+)"))
    async def embed_event(self, ctx: ComponentContext):
        embed_name = ctx.custom_id.split(":")[1]
        print(f"embed_event: {embed_name}")
        modal = Modal(
            ShortText(
                label="Event Type",
                custom_id="event_type",
                required=True,
                placeholder="Type 'on_join' or 'none'",
                value="none"
            ),
            ShortText(
                label="Channel ID (only for on_join)",
                custom_id="channel_id",
                required=False,
                placeholder="Enter channel ID (leave empty for current channel)"
            ),
            title="Register Event",
            custom_id=f"embed_event_modal:{embed_name}"
        )
        await ctx.send_modal(modal)
    
    @modal_callback(re.compile(r"embed_event_modal:(.+)"))
    async def embed_event_modal(self, ctx: ModalContext):
        embed_name = ctx.custom_id.split(":")[1]
        event_type = ctx.responses.get("event_type").lower()
        channel_id = ctx.responses.get("channel_id")
        if event_type not in ["on_join", "none"]:
            await ctx.send("Invalid event type. Use 'on_join' or 'none'.", ephemeral=True)
            return
        key = self.get_embed_key(str(ctx.author.id), embed_name)
        embed_data = await self.db.get(key)
        if not embed_data:
            message = ctx.message
            if not message or not message.embeds:
                await ctx.send("Couldn't find the embed. Please try again.", ephemeral=True)
                return
            embed = message.embeds[0]
            embed_data = self.serialize_embed(embed)
        if event_type == "none":
            if "event_config" in embed_data: del embed_data["event_config"]
            self.db.set(key, embed_data)
            await ctx.send("Event registration removed. This is now a standard embed.", ephemeral=True)
            return
        try:
            if channel_id:
                channel_id = int(channel_id)
                channel = await ctx.guild.fetch_channel(channel_id)
            else:
                channel = ctx.channel
                channel_id = channel.id
            if not channel:
                raise ValueError("Channel not found")
        except (ValueError, TypeError):
            await ctx.send("Invalid channel ID. Please provide a valid channel ID.", ephemeral=True)
            return
        event_data = {
            "event_type": event_type,
            "channel_id": channel_id,
            "guild_id": ctx.guild_id,
            "is_finalized": False
        }
        embed_data["event_config"] = event_data
        self.db.set(key, embed_data)
        await ctx.send(f"Event registered! This embed will be sent to <#{channel_id}> when new members join.", ephemeral=True)
    
    @modal_callback(re.compile(r"embed_images_modal:(.+)"))
    async def embed_images_modal(self, ctx: ModalContext):
        embed_name = ctx.custom_id.split(":")[1]
        main_image = ctx.responses.get("main_image")
        thumbnail = ctx.responses.get("thumbnail")
        message = ctx.message
        if not message:
            await ctx.send("Couldn't find the original message.", ephemeral=True)
            return    
        embed = message.embeds[0] if message.embeds else None
        if not embed:
            await ctx.send("Couldn't find the embed.", ephemeral=True)
            return
        if main_image:
            if main_image.lower() == 'remove':
                embed.set_image(None)
            else:
                try:
                    embed.set_image(main_image)
                except Exception as e:
                    await ctx.send(f"Error setting main image: {str(e)}", ephemeral=True)
                    return
        if thumbnail:
            if thumbnail.lower() == 'remove':
                embed.thumbnail = None
            else:
                try:
                    embed.set_thumbnail(thumbnail)
                except Exception as e:
                    await ctx.send(f"Error setting thumbnail: {str(e)}", ephemeral=True)
                    return
        
        await ctx.defer(edit_origin=True)
        await message.edit(
            embed=embed,
            components=self.get_embed_buttons(embed_name)
        )
    
    @component_callback(re.compile(r"embed_author_footer:(.+)"))
    async def embed_author_footer(self, ctx: ComponentContext):
        embed_name = ctx.custom_id.split(":")[1]
        print(f"embed_author_footer: {embed_name}")
        modal = Modal(
            ShortText(
                label="Author Name",
                custom_id="author_name",
                required=False,
                placeholder="Author name (type 'remove' to clear)"
            ),
            ShortText(
                label="Author URL",
                custom_id="author_url",
                required=False,
                placeholder="URL for author name to link to"
            ),
            ShortText(
                label="Author Icon URL",
                custom_id="author_icon",
                required=False,
                placeholder="URL for author icon"
            ),
            ShortText(
                label="Footer Text",
                custom_id="footer_text",
                required=False,
                placeholder="Footer text (type 'remove' to clear)"
            ),
            ShortText(
                label="Footer Icon URL",
                custom_id="footer_icon",
                required=False,
                placeholder="URL for footer icon"
            ),
            title="Edit Author/Footer",
            custom_id=f"embed_author_footer_modal:{embed_name}"
        )
        await ctx.send_modal(modal)
    
    @modal_callback(re.compile(r"embed_author_footer_modal:(.+)"))
    async def embed_author_footer_modal(self, ctx: ModalContext):
        embed_name = ctx.custom_id.split(":")[1]
        author_name = ctx.responses.get("author_name")
        author_url = ctx.responses.get("author_url")
        author_icon = ctx.responses.get("author_icon")
        footer_text = ctx.responses.get("footer_text")
        footer_icon = ctx.responses.get("footer_icon")
        message = ctx.message
        if not message:
            await ctx.send("Couldn't find the original message.", ephemeral=True)
            return
        embed = message.embeds[0] if message.embeds else None
        if not embed:
            await ctx.send("Couldn't find the embed.", ephemeral=True)
            return
        if author_name:
            if author_name.lower() == 'remove':
                embed.author = None
            else:
                try:
                    embed.set_author(
                        name=author_name,
                        url=author_url if author_url else None,
                        icon_url=author_icon if author_icon else None
                    )
                except Exception as e:
                    await ctx.send(f"Error setting author: {str(e)}", ephemeral=True)
                    return
        if footer_text:
            if footer_text.lower() == 'remove':
                embed.footer = None
            else:
                try:
                    embed.set_footer(
                        text=footer_text,
                        icon_url=footer_icon if footer_icon else None
                    )
                except Exception as e:
                    await ctx.send(f"Error setting footer: {str(e)}", ephemeral=True)
                    return
        
        await ctx.defer(edit_origin=True)
        await message.edit(
            embed=embed,
            components=self.get_embed_buttons(embed_name)
        )
    
    @component_callback(re.compile(r"embed_finalize:(.+)"))
    async def embed_finalize(self, ctx: ComponentContext):
        embed_name = ctx.custom_id.split(":")[1]
        print(f"embed_finalize: {embed_name}")
        message = ctx.message
        if not message:
            await ctx.send("Couldn't find the original message.", ephemeral=True)
            return
        embed = message.embeds[0] if message.embeds else None
        if not embed:
            await ctx.send("Couldn't find the embed.", ephemeral=True)
            return
        key = self.get_embed_key(str(ctx.author.id), embed_name)
        embed_data = await self.db.get(key)
        if not embed_data:
            embed_data = self.serialize_embed(embed)
        if "event_config" not in embed_data:
            embed_data["event_config"] = None
        if embed_data["event_config"]:
            embed_data["event_config"]["is_finalized"] = True
            finalize_message = "Embed finalized with event configuration!"
        else:
            finalize_message = "Embed finalized!"
        self.db.set(key, embed_data)
        await message.edit(
            embed=embed,
            components=[]
        )
        await ctx.send(finalize_message, ephemeral=True)
    
    @component_callback(re.compile(r"embed_save:(.+)"))
    async def embed_save(self, ctx: ComponentContext):
        embed_name = ctx.custom_id.split(":")[1]
        print(f"embed_save: {embed_name}")
        message = ctx.message
        if not message:
            await ctx.send("Couldn't find the original message.", ephemeral=True)
            return
        embed = message.embeds[0] if message.embeds else None
        if not embed:
            await ctx.send("Couldn't find the embed.", ephemeral=True)
            return
        data = self.serialize_embed(embed)
        key = self.get_embed_key(str(ctx.author.id), embed_name)
        self.db.set(key, data)
        await ctx.send(f"Embed template saved as '{embed_name}'!", ephemeral=True)
    
    @listen("member_add")
    async def on_member_join(self, event):
        guild_id = event.guild.id
        member = event.member
        print(f"Member join event triggered for {member} in guild {guild_id}")
        pattern = "embed:*"
        embed_keys = self.db.list_keys(pattern)
        print(f"Found {len(embed_keys)} total embed keys")
        for key in embed_keys:
            try:
                embed_data = await self.db.get(key)
                if not embed_data:
                    continue
                print(f"Checking embed key: {key}")
                print(f"Event config: {embed_data.get('event_config')}")
                if not embed_data or "event_config" not in embed_data or embed_data["event_config"] is None:
                    continue
                event_config = embed_data["event_config"]
                print(f"Event config details:")
                print(f"- is_finalized: {event_config.get('is_finalized')}")
                print(f"- event_type: {event_config.get('event_type')}")
                print(f"- guild_id: {event_config.get('guild_id')} (current: {guild_id})")
                if (isinstance(event_config, dict) and
                    event_config.get("is_finalized", False) and 
                    event_config.get("event_type") == "on_join" and 
                    str(event_config.get("guild_id")) == str(guild_id)):
                    print(f"Found matching welcome embed! Attempting to send...")
                    embed = self.deserialize_embed(embed_data)
                    channel = await self.bot.fetch_channel(event_config["channel_id"])
                    if channel:
                        await channel.send(
                            content=f"Welcome {member.mention}!",
                            embed=embed
                        )
                        print(f"Successfully sent welcome message to channel {channel.id}")
                    else:
                        print(f"Could not find channel with ID {event_config['channel_id']}")
            except Exception as e:
                print(f"Error processing embed key {key}: {str(e)}")
                continue