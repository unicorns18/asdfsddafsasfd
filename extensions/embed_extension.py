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
        if not color:
            return 0x000000
            
        color = color.replace(' ', '').lower()
        if color.startswith('#'):
            color = color[1:]
        
        if len(color) == 3:
            color = ''.join(c * 2 for c in color)
        if len(color) == 6:
            try:
                return int(color, 16)
            except ValueError:
                pass

        rgb_match = re.match(r'rgb\((\d+),(\d+),(\d+)\)', color)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            if all(0 <= x <= 255 for x in (r, g, b)):
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
        self.WHITELIST_KEY = "whitelisted_users"
    
    async def get(self, key):
        """Get a value from Redis and parse it as JSON."""
        try:
            value = self.db.redis.get(key)
            if value:
                import json
                return json.loads(value.decode('utf-8'))
            return None
        except Exception as e:
            print(f"Error getting key {key} from Redis: {e}")
            return None

    def set(self, key, value):
        """Set a value in Redis after converting it to JSON."""
        try:
            import json
            self.db.redis.set(key, json.dumps(value))
        except Exception as e:
            print(f"Error setting key {key} in Redis: {e}")

    def list_keys(self, pattern):
        """List all keys matching the given pattern."""
        try:
            return [key.decode('utf-8') for key in self.db.redis.scan_iter(pattern)]
        except Exception as e:
            print(f"Error listing keys with pattern {pattern}: {e}")
            return []

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
        if not isinstance(data, dict):
            raise ValueError("Embed data must be a dictionary")
            
        try:
            embed = Embed(
                title=data.get("title"),
                description=data.get("description"),
                color=data.get("color"),
                url=data.get("url")
            )
            
            if data.get("timestamp"):
                try:
                    embed.timestamp = datetime.fromisoformat(data["timestamp"])
                except ValueError:
                    pass
                    
            for field in data.get("fields", []):
                if isinstance(field, dict):
                    embed.add_field(
                        name=str(field.get("name", "")),
                        value=str(field.get("value", "")),
                        inline=bool(field.get("inline", False))
                    )
                    
            if isinstance(data.get("author"), dict):
                embed.set_author(
                    name=str(data["author"].get("name", "")),
                    url=data["author"].get("url"),
                    icon_url=data["author"].get("icon_url")
                )
                
            if isinstance(data.get("footer"), dict):
                embed.set_footer(
                    text=str(data["footer"].get("text", "")),
                    icon_url=data["footer"].get("icon_url")
                )
                
            if data.get("image"):
                embed.set_image(str(data["image"]))
                
            if data.get("thumbnail"):
                embed.set_thumbnail(str(data["thumbnail"]))
                
            return embed
        except Exception as e:
            raise ValueError(f"Failed to deserialize embed: {str(e)}")

    def get_embed_key(self, user_id: str, name: str) -> str:
        return f"embed:{user_id}:{name}"

    @slash_command(
        name="embed",
        description="Manage embed templates"
    )
    async def embed(self, ctx: SlashContext):
        """Base command for embed management"""
        await ctx.send("Please use one of the subcommands:\n- /embed create - Create a new embed\n- /embed load - Load a saved embed\n- /embed list - List all saved embeds\n- /embed edit - Edit an existing embed\n- /embed flush - Delete all saved embeds")

    @embed.subcommand(
        sub_cmd_name="create",
        sub_cmd_description="Create a new embed template"
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
        existing_embed = await self.get(key)
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
        buttons = self.get_embed_buttons(name)
        await ctx.send(
            embed=embed,
            components=buttons
        )

    @embed.subcommand(
        sub_cmd_name="load",
        sub_cmd_description="Load a saved embed template"
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
        embed_data = await self.get(key)
        if not embed_data:
            await ctx.send(f"No saved embed template found with name '{name}'", ephemeral=True)
            return
        embed = self.deserialize_embed(embed_data)
        buttons = self.get_embed_buttons(name)
        await ctx.send(embed=embed, components=buttons)

    @embed.subcommand(
        sub_cmd_name="list",
        sub_cmd_description="List all saved embed templates"
    )
    async def embed_list(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to list embeds.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        pattern = f"embed:{ctx.author.id}:*"
        embed_keys = self.list_keys(pattern)
        if not embed_keys:
            await ctx.send("No saved embed templates found.", ephemeral=True)
            return
        embeds = []
        for key in embed_keys:
            name = key.split(":")[-1]
            embed_data = await self.get(key)
            if embed_data:
                embed = self.deserialize_embed(embed_data)
                embed._template_name = name
                embeds.append(embed)        
        paginator = Paginator.create_from_embeds(
            self.bot,
            *embeds,
            timeout=300
        )
        
        async def load_template(ctx: ComponentContext):
            try:
                current_embed = embeds[paginator.page_index]
                embed_name = getattr(current_embed, '_template_name', None)
                if not embed_name:
                    await ctx.send("Could not determine template name.", ephemeral=True)
                    return None
                    
                key = self.get_embed_key(str(ctx.author.id), embed_name)
                embed_data = await self.get(key)
                if embed_data:
                    embed = self.deserialize_embed(embed_data)
                    await ctx.send(embed=embed, components=self.get_embed_buttons(embed_name))
                else:
                    await ctx.send("Could not load embed template.", ephemeral=True)
            except Exception as e:
                await ctx.send(f"Error loading template: {str(e)}", ephemeral=True)
            return None
            
        paginator.show_callback_button = True
        paginator.callback = load_template
        await paginator.send(ctx)

    @embed.subcommand(
        sub_cmd_name="flush",
        sub_cmd_description="Delete all saved embed templates"
    )
    async def embed_flush(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to flush the embed database.", ephemeral=True)
            return
        pattern = f"embed:{ctx.author.id}:*"
        embed_keys = self.list_keys(pattern)
        if not embed_keys:
            await ctx.send("No saved embed templates to flush.", ephemeral=True)
            return
        for key in embed_keys:
            self.db.redis.delete(key)
        await ctx.send(f"Successfully deleted {len(embed_keys)} embed templates.", ephemeral=True)

    @embed.subcommand(
        sub_cmd_name="edit",
        sub_cmd_description="Edit an existing embed template"
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
        embed_data = await self.get(key)
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

    # Keep all the existing component_callback and modal_callback methods...
    # They don't need to change as they work with the buttons

def setup(bot):
    return EmbedExtension(bot)