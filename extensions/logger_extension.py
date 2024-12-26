import re
from interactions import Button, ButtonStyle, ComponentContext, Embed, EmbedField, Extension, Color, ChannelType, EmbedFooter
import interactions
from datetime import datetime
from interactions.ext.paginators import Paginator

class LoggerExtension(Extension):
    LOG_SERVER_ID = 1319494539785932833
    
    # Mapping of guild IDs to their respective logging category IDs
    GUILD_CATEGORIES = {
        "1260696412962951288": 1319499457766887476,  # Cosmic Chaos
        "1315723547401912421": 1319499541904490546,   # Calico Cafe,
        "1316274417445371958": 1320943537327571027 # hi
    }
    
    def __init__(self, bot):
        self.bot = bot
        self.log_channels = {}  # Cache for logging channels
        self.attachment_cache = {}  # Cache for attachment data

    def clean_name(self, name):
        return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')

    async def get_or_create_log_channel(self, guild_id, channel_name, channel_id):
        # Create unique key for channel cache
        cache_key = f"{guild_id}-{channel_id}"
        
        # Check cache first
        if cache_key in self.log_channels:
            return self.log_channels[cache_key]
        
        # Get the category ID for this guild
        category_id = self.GUILD_CATEGORIES.get(str(guild_id))
        if not category_id:
            return None
            
        # Clean the channel name for creation
        clean_channel_name = self.clean_name(channel_name).lower()
        log_channel_name = f"{clean_channel_name}-{channel_id}"
        
        # Look for existing channel
        log_server = await self.bot.fetch_guild(self.LOG_SERVER_ID)
        channels = await log_server.fetch_channels()
        existing_channel = next(
            (channel for channel in channels 
             if channel.name.lower() == log_channel_name.lower() and 
             channel.type == ChannelType.GUILD_TEXT and
             channel.parent_id == category_id),
            None
        )
        
        if existing_channel:
            self.log_channels[cache_key] = existing_channel
            return existing_channel
            
        # Create new channel under the specified category
        try:
            new_channel = await self.bot.http.create_guild_channel(
                guild_id=self.LOG_SERVER_ID,
                name=log_channel_name,
                channel_type=ChannelType.GUILD_TEXT.value,
                parent_id=category_id,
                topic=f"Logs for #{channel_name} ({channel_id})",
                reason=f"Created for logging #{channel_name}"
            )
            
            # Convert the response to a channel object
            channel = await self.bot.fetch_channel(new_channel["id"])
            self.log_channels[cache_key] = channel
            return channel
            
        except Exception as e:
            print(f"Failed to create log channel: {e}")
            return None

    @interactions.listen()
    async def on_message_create(self, event):
        message = event.message
        guild_id = str(message._guild_id)
        
        # If this is in the logging server and is a reply to a bot message
        if str(message._guild_id) == str(self.LOG_SERVER_ID):
            # Check if the message author is the authorized user
            if message.author.id not in [686107711829704725, 1259678639159644292, 1308235105084510209]:
                return
                
            if message._referenced_message_id:
                referenced_message = await message.channel.fetch_message(message._referenced_message_id)
                if referenced_message.author.id == self.bot.user.id:
                    try:
                        # Get the original embed to extract channel and author info
                        original_embed = referenced_message.embeds[0]
                        # Find the channel ID and author ID from the embed fields
                        channel_field = next((field for field in original_embed.fields if field.name == "Channel"), None)
                        author_field = next((field for field in original_embed.fields if field.name == "Author"), None)
                        
                        if channel_field and author_field:
                            # Extract channel ID and author ID
                            channel_id = channel_field.value.split('`')[1]
                            author_id = author_field.value.split('`')[1]
                            
                            try:
                                original_channel = await self.bot.fetch_channel(channel_id)
                                if original_channel:
                                    # Send the mention message
                                    mention_msg = f"<@{author_id}> {message.content}"
                                    await original_channel.send(mention_msg)
                                    
                                    # Add a reaction to confirm the reply was sent
                                    await message.add_reaction("✅")
                            except Exception as e:
                                print(f"Failed to send reply to original channel: {e}")
                                await message.add_reaction("❌")
                    except Exception as e:
                        print(f"Failed to process reply: {e}")
            return

        # Skip if message is from the logging server or not from a monitored guild
        if guild_id not in self.GUILD_CATEGORIES:
            return
                
        # Get channel details
        channel_id = str(message._channel_id)
        channel_name = self.clean_name(message.channel.name)
        author_id = str(message.author.id)
        
        # Server logging
        try:
            log_channel = await self.get_or_create_log_channel(
                guild_id=guild_id,
                channel_name=channel_name,
                channel_id=channel_id
            )
            
            if log_channel:
                # Create embed
                embed = Embed(
                    title=f"Message in #{channel_name}",
                    description=message.content if message.content else "*No text content*",
                    color=Color.random(),
                    timestamp=datetime.now().isoformat(),
                    fields=[
                        EmbedField(name="Author", value=f"{message.author.username} (`{author_id}`)", inline=True),
                        EmbedField(name="Channel", value=f"<#{channel_id}> (`{channel_id}`)", inline=True),
                    ]
                )
                
                # Add author avatar
                if message.author.avatar_url:
                    embed.set_author(name=message.author.username, icon_url=message.author.avatar_url)
                
                # Initialize components list
                components = []
                
                # Handle attachments
                if message.attachments:
                    # Set the first image as the embed image
                    first_attachment = message.attachments[0]
                    if first_attachment.content_type and "image" in first_attachment.content_type:
                        embed.set_image(url=first_attachment.url)
                    
                    # List all attachments in a field
                    attachment_list = []
                    for idx, attachment in enumerate(message.attachments, 1):
                        attachment_list.append(f"{idx}. [{attachment.filename}]({attachment.url})")
                    
                    if attachment_list:
                        embed.add_field(
                            name="Attachments",
                            value="\n".join(attachment_list),
                            inline=False
                        )

                    # Add View Images button if there are multiple image attachments
                    image_attachments = [att for att in message.attachments if att.content_type and "image" in att.content_type]
                    if len(image_attachments) > 1:
                        cache_key = str(message.id)
                        self.attachment_cache[cache_key] = [
                            {"url": att.url, "filename": att.filename}
                            for att in image_attachments
                        ]
                        view_images_button = Button(
                            style=ButtonStyle.SECONDARY,
                            label="View Images",
                            custom_id=f"view_log_images:{cache_key}"
                        )
                        components.append(view_images_button)
                
                await log_channel.send(embed=embed, components=components if components else None)
                
        except Exception as e:
            print(f"Failed to log to server: {e}")
            import traceback
            traceback.print_exc()

    @interactions.component_callback(re.compile(r"view_log_images:(\d+)"))
    async def view_log_images(self, ctx: ComponentContext):
        cache_key = ctx.custom_id.split(":")[1]
        
        if cache_key not in self.attachment_cache:
            await ctx.send("Could not find the image attachments.", ephemeral=True)
            return
            
        attachments = self.attachment_cache[cache_key]
        if not attachments:
            await ctx.send("No image attachments found.", ephemeral=True)
            return
            
        embeds = []
        for idx, attachment in enumerate(attachments, 1):
            embed = Embed(
                title=f"Image {idx}/{len(attachments)}",
                color=Color.random(),
                footer=EmbedFooter(text=f"Attachment: {attachment['filename']}"),
                timestamp=datetime.now().isoformat()
            )
            embed.set_image(url=attachment['url'])
            embeds.append(embed)
            
        paginator = Paginator.create_from_embeds(self.bot, *embeds)
        await paginator.send(ctx, ephemeral=True)
        
        # Clean up cache after sending
        del self.attachment_cache[cache_key]