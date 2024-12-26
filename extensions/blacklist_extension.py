from hashlib import sha256
import os
import re
import tempfile
import aiohttp
from interactions import ComponentContext, Extension, Modal, OptionType, ShortText, SlashContext, Embed, EmbedField, EmbedFooter, Color, component_callback, modal_callback
from interactions.ext.paginators import Paginator
from database import RedisDB
import aiohttp
from datetime import datetime
import interactions
from drive import Drive


class BlacklistExtension(Extension):
    WHITELIST_KEY = "whitelisted_users"
    FORCE_OVERRIDE_USER_ID = ["686107711829704725", "708812851229229208", "1259678639159644292", "1168346688969252894"]
    BLACKLIST_CHANNEL_PATTERN = re.compile(r".*blacklist*.", re.IGNORECASE)
    
    def __init__(self, bot):
        self.bot = bot
        self.drive = Drive()
        self.db_blacklist = RedisDB(db=0)
        self.db_whitelist = RedisDB(db=1)
        self.db_servers = RedisDB(db=2)
        
    async def is_user_whitelisted(self, user_id):
        if str(user_id) in [str(id) for id in self.FORCE_OVERRIDE_USER_ID]: return True
        return self.db_whitelist.redis.sismember(self.WHITELIST_KEY, str(user_id))
        
    @interactions.slash_command(name="whitelist", description="Whitelist a user")
    @interactions.slash_option(
        name="user",
        description="The user to whitelist",
        required=True,
        opt_type=OptionType.USER
    )
    async def whitelist_user(self, ctx: SlashContext, user: OptionType.USER):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not authorized to modify the whitelist.", ephemeral=True)
            return
        self.db_whitelist.redis.sadd(self.WHITELIST_KEY, str(user.id))
        await ctx.send(f"User <@{user.id}> has been added to the whitelist.", ephemeral=True)

    @interactions.slash_command(name="unwhitelist", description="Unwhitelist a user")
    @interactions.slash_option(
        name="user",
        description="The user to unwhitelist",
        required=True,
        opt_type=OptionType.USER
    )
    async def unwhitelist_user(self, ctx: SlashContext, user: OptionType.USER):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not authorized to modify the whitelist.", ephemeral=True)
            return
        if not self.db_whitelist.redis.sismember(self.WHITELIST_KEY, str(user.id)):
            await ctx.send(f"User <@{user.id}> is not whitelisted.", ephemeral=True)
        else:
            self.db_whitelist.redis.srem(self.WHITELIST_KEY, str(user.id))
            await ctx.send(f"User <@{user.id}> has been removed from the whitelist.", ephemeral=True)

    @interactions.slash_command(name="search", description="Search for a blacklisted user")
    @interactions.slash_option(
        name="pattern",
        description="Pattern to search for in the blacklist",
        required=True,
        opt_type=OptionType.STRING
    )
    async def search_blacklist(self, ctx: SlashContext, pattern: str):        
        matched_data = self.db_blacklist.search_users(pattern)
        
        if not matched_data:
            await ctx.send(f"No blacklisted user found with the pattern `{pattern}`", ephemeral=True)
            return
        
        embeds = []
        for index, (user_id, user_info) in enumerate(matched_data):
            username = user_info["username"]
            reason = user_info["reason"]
            proof_link = user_info["proof_link"]
            embed = Embed(
                title=username,
                description="Here's some detailed information about the user:",
                color=Color.random(),
                fields=[
                    EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                    EmbedField(name="📜 Reason", value=reason, inline=False),
                    EmbedField(name="🔗 Proof Link", value=f"[Click Here]({proof_link})", inline=False),
                ],
                footer=EmbedFooter(text=f"Blacklist System | Result {index + 1} of {len(matched_data)}"),
                timestamp=datetime.now().isoformat()
            )
            embeds.append(embed)
        paginator = Paginator.create_from_embeds(self.bot, *embeds)
        await paginator.send(ctx, ephemeral=True)

    @interactions.slash_command(name="list-whitelist", description="List all whitelisted users")
    async def list_whitelist(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        whitelisted_ids = self.db_whitelist.redis.smembers(self.WHITELIST_KEY)
        if not whitelisted_ids:
            await ctx.send("There are no whitelisted users.", ephemeral=True)
            return

        # Prepare user mentions
        whitelisted_users = [f"<@{user_id.decode('utf-8')}>" for user_id in whitelisted_ids]

        # Handle potential message length limitations
        MAX_EMBED_FIELD_VALUE_LEN = 1024
        description_chunks = [whitelisted_users[i:i + MAX_EMBED_FIELD_VALUE_LEN] for i in range(0, len(whitelisted_users), MAX_EMBED_FIELD_VALUE_LEN)]
        for chunk in description_chunks:
            embed = Embed(
                title="Whitelisted Users",
                description="Here's a list of all whitelisted users:",
                color=Color.random(),
                fields=[
                    EmbedField(name="Users", value="\n".join(chunk) or "No users to display.", inline=False)
                ],
                footer=EmbedFooter(text="Whitelist System"),
                timestamp=datetime.now().isoformat()
            )
            await ctx.send(embed=embed)
        
    @interactions.slash_command(name="list", description="List all blacklisted users")
    async def list_blacklist(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        keys_values = self.db_blacklist.list_all_users_info()
        if not keys_values:
            await ctx.send("There are no blacklisted users.", ephemeral=True)
            return
        
        embeds = []
        for index, (user_id, user_info) in enumerate(keys_values.items()):
            username = user_info.get("username", "N/A")
            reason = user_info.get("reason", "N/A")
            proof_link = user_info.get("proof_link", "N/A")
            folder_id = user_info.get("folder_id", "N/A")

            embed = Embed(
                title=f"{username}",
                description="Here's some detailed information about the user:",
                color=Color.random(),
                fields=[
                    EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                    EmbedField(name="📜 Reason", value=f"*{reason}*", inline=False),
                    EmbedField(name="🔗 Proof Link", value=f"[Click Here]({proof_link})", inline=False),
                    EmbedField(name="Folder ID", value=f"`{folder_id}`", inline=True),
                ],
                footer=EmbedFooter(text=f"Blacklist System | Page {index + 1} of {len(keys_values)}"),
                timestamp=datetime.now().isoformat()
            )
            embeds.append(embed)
        
        paginator = Paginator.create_from_embeds(self.bot, *embeds)
        await paginator.send(ctx, ephemeral=True)
    
    @interactions.slash_command(name="blacklist", description="Blacklist a user")
    @interactions.slash_option(
        name="user",
        description="User to blacklist",
        required=True,
        opt_type=OptionType.USER,
    )
    @interactions.slash_option(
        name="reason",
        description="Reason for blacklisting",
        required=True,
        opt_type=OptionType.STRING,
    )
    @interactions.slash_option(
        name="msn",
        description="MSN or not?",
        required=True,
        opt_type=OptionType.BOOLEAN,
    )
    @interactions.slash_option(
        name="aliases",
        description="User's aliases (separate with commas)",
        required=True,
        opt_type=OptionType.STRING,
    )
    @interactions.slash_option(
        name="file1",
        description="Image to blacklist",
        required=True,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file2",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file3",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file4",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    @interactions.slash_option(
        name="file5",
        description="Image to blacklist",
        required=False,
        opt_type=OptionType.ATTACHMENT,
    )
    async def blacklist(self, ctx: SlashContext, user: interactions.User, reason: str, msn: bool, aliases: str = None, file1: interactions.Attachment=None, file2: interactions.Attachment=None, file3: interactions.Attachment=None, file4: interactions.Attachment=None, file5: interactions.Attachment=None):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)
        folder_id = self.drive.create_folder(f"blacklist-{user.username}")
        folder_link = f"https://drive.google.com/drive/folders/{folder_id}"

        files = [file1, file2, file3, file4, file5]
        files = [file for file in files if file is not None]

        async with aiohttp.ClientSession() as session:
            for image in files:
                async with session.get(image.url) as resp:
                    if resp.status != 200 or resp.content_type not in ["image/png", "image/jpeg", "image/gif"]:
                        print(f"Failed to download image or invalid content type for {image.url}")
                        continue
                    fd, path = tempfile.mkstemp(suffix=".png")
                    try:
                        with os.fdopen(fd, 'wb') as tmp:
                            tmp.write(await resp.read())
                        self.drive.upload_file(path, folder_id)
                    finally:
                        os.unlink(path)

        # Create basic embed fields
        embed_fields = [
            EmbedField(name="User ID", value=str(user.id), inline=True),
            EmbedField(name="Reason", value=reason, inline=False),
            EmbedField(name="Requested by", value=str(ctx.author.id), inline=True),
            EmbedField(name="Proof Link", value=folder_link, inline=False),
            EmbedField(name="MSN", value=str(msn), inline=True),
        ]

        # If aliases exist, add them to embed
        if aliases:
            alias_list = [alias.strip() for alias in aliases.split(',')]
            alias_ids = [alias for alias in alias_list if alias.isdigit()]
            if alias_ids:
                embed_fields.append(EmbedField(name="Aliases", value=",".join(alias_ids), inline=False))

        embed = Embed(
            title=f"Blacklist Request for {user.username}",
            description="This blacklist request requires approval.",
            color=Color.random(),
            fields=embed_fields
        )

        # Create just the first action row with view buttons
        view_images_link_button = interactions.Button(
            style=interactions.ButtonStyle.LINK,
            label="View Images",
            url=folder_link
        )
        
        view_images_direct_button = interactions.Button(
            style=interactions.ButtonStyle.SECONDARY,
            label="View Images Direct",
            custom_id="view_images_direct"
        )
        
        action_row1 = interactions.ActionRow()
        action_row1.components.extend([view_images_link_button, view_images_direct_button])

        alias_ids_str = ",".join(alias_ids) if aliases and alias_ids else ""
    
        approve_button = interactions.Button(
            style=interactions.ButtonStyle.SUCCESS,
            label="Approve",
            custom_id=f"approve_blacklist:{user.id}"
        )

        reject_button = interactions.Button(
            style=interactions.ButtonStyle.DANGER,
            label="Reject",
            custom_id=f"reject_blacklist:{user.id}"
        )
        
        action_row2 = interactions.ActionRow()
        action_row2.components.extend([approve_button, reject_button])

        try:
            guild = await self.bot.fetch_guild(1260696412962951288)
            channels = await guild.fetch_channels()
            approval_channel = next((channel for channel in channels if channel.id == 1318420510916477118), None)
            
            if approval_channel is None:
                await ctx.send("Could not find the approval channel!", ephemeral=True)
                return

            # Try sending with just the first action row
            await approval_channel.send(embed=embed, components=[action_row1, action_row2])
            await ctx.send("Blacklist request has been submitted for approval!", ephemeral=True)
            
        except Exception as e:
            await ctx.send(f"Failed to send approval message: {str(e)}", ephemeral=True)
            print(f"Error details: {e}")
            return
    
    @component_callback(re.compile(r"approve_blacklist:.*"))
    async def approve_blacklist(self, ctx):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        user_id = ctx.custom_id.split(":")[1]
        proof_link = None
        reason = None
        username = None
        folder_id = None
        msn_check = False
        for field in ctx.message.embeds[0].fields:
            print(f"Field: {field.name} - {field.value}")
            if field.name == "Proof Link":
                proof_link = str(field.value)
                folder_id = proof_link.split('/')[-1] if proof_link else ""
            elif field.name == "Reason":
                reason = str(field.value)
            elif field.name == "User ID":
                user_id = str(field.value).strip("`")
            elif field.name == "MSN":
                msn_check = field.value.lower() == "true"
        if not all([user_id, reason, proof_link]):
            await ctx.send("Missing required information from embed!", ephemeral=True)
            return
        username = f"user_{user_id}"
        try:
            self.db_blacklist.set_user(
                user_id=str(user_id),
                username=str(username),
                reason=str(reason),
                proof_link=str(proof_link),
                folder_id=str(folder_id)
            )
            original_embed = ctx.message.embeds[0]
            approved_embed = Embed(
                title=original_embed.title,
                description="✅ This blacklist request has been approved.",
                color=Color.random(),
                fields=original_embed.fields
            )
            approved_embed.add_field(
                name="Approved By",
                value=f"{ctx.author.username} ({ctx.author.id})",
                inline=False
            )
            disabled_components = []
            for action_row in ctx.message.components:
                new_row = interactions.ActionRow()
                for component in action_row.components:
                    if isinstance(component, interactions.Button):
                        if component.style != interactions.ButtonStyle.LINK:
                            component.disabled = True
                    new_row.components.append(component)
                disabled_components.append(new_row)
            await ctx.message.edit(embed=approved_embed, components=disabled_components)
            await ctx.send("Blacklist has been approved!", ephemeral=True)

            # Create notification embed
            if not msn_check:
                blacklist_notification_embed = Embed(
                    title=f"{username} has been blacklisted!",
                    description="Here's some detailed information about the blacklist:",
                    color=Color.random(),
                    fields=[
                        EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                        EmbedField(name="📜 Reason", value=f"*{reason}*", inline=False),
                        EmbedField(name="🔗 Proof Link", value=f"[Click Here]({proof_link})", inline=False),
                    ],
                    footer=EmbedFooter(text="Blacklist System"),
                    timestamp=datetime.now().isoformat()
                )
                view_images_link_button = interactions.Button(
                    style=interactions.ButtonStyle.LINK,
                    label="View Images",
                    url=proof_link
                )
                view_images_direct_button = interactions.Button(
                    style=interactions.ButtonStyle.SECONDARY,
                    label="View Images Direct",
                    custom_id="view_images_direct"
                )
                notification_row = interactions.ActionRow()
                notification_row.components.extend([view_images_link_button, view_images_direct_button])

            # Always perform bans
            keys_values = self.db_blacklist.list_all_users_info()
            current_sync_hash = sha256(str(keys_values).encode('utf-8')).hexdigest()
            successful_bans = 0
            failed_bans = 0
            ban_errors = []
            for guild in self.bot.guilds:
                try:
                    if not guild.me.guild_permissions.BAN_MEMBERS:
                        print(f"Missing ban permissions in guild: {guild.name} ({guild.id})")
                        ban_errors.append(f"Missing permissions in {guild.name}")
                        failed_bans += 1
                        continue
                    await guild.ban(int(user_id), reason=f"Blacklisted: {reason}")
                    self.db_servers.set_last_sync_details(str(guild.id), current_sync_hash)
                    successful_bans += 1
                    print(f"Successfully banned user {user_id} in guild: {guild.name} ({guild.id})")
                    
                    # Only send notification if not MSN
                    if not msn_check:
                        blacklist_channel = next(
                            (channel for channel in guild.channels 
                            if self.BLACKLIST_CHANNEL_PATTERN.match(channel.name) 
                            or channel.name in ["blacklist", "blacklists"]), 
                            None
                        )
                        if blacklist_channel:
                            await blacklist_channel.send(
                                embed=blacklist_notification_embed, 
                                components=[notification_row]
                            )
                except Exception as e:
                    print(f"Failed to ban in guild {guild.name} ({guild.id}): {e}")
                    ban_errors.append(f"Failed in {guild.name}: {str(e)}")
                    failed_bans += 1
            total_guilds = len(self.bot.guilds)
            ban_status = f"Ban Results:\n✅ Successful: {successful_bans}/{total_guilds} guilds"
            if failed_bans > 0:
                ban_status += f"\n❌ Failed: {failed_bans} guilds"
                if ban_errors:
                    ban_status += "\nErrors:\n" + "\n".join(ban_errors[:5])
                    if len(ban_errors) > 5:
                        ban_status += f"\n...and {len(ban_errors) - 5} more"
            await ctx.send(ban_status, ephemeral=True)

        except Exception as e:
            await ctx.send(f"Error processing blacklist: {str(e)}", ephemeral=True)
            print(f"Error details: {e}")

    @component_callback(re.compile(r"reject_blacklist:.*"))
    async def reject_blacklist(self, ctx):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        user_id = ctx.custom_id.split(":")[1]
        modal = Modal(
            ShortText(
                label="Rejection Reason",
                custom_id="rejection_reason",
                placeholder="Enter the reason for rejection",
                max_length=1000,
            ),
            title="Reject Blacklist",
            custom_id=f"reject_blacklist_modal:{user_id}"
        )
        await ctx.send_modal(modal)

    @modal_callback(re.compile(r"reject_blacklist_modal:.*"))
    async def handle_reject_blacklist(self, ctx):
        rejection_reason = ctx.responses["rejection_reason"]
        original_embed = ctx.message.embeds[0]
        rejected_embed = Embed(
            title=original_embed.title,
            description="❌ This blacklist request has been rejected.",
            color=Color.random(),
            fields=original_embed.fields
        )
        rejected_embed.add_field(
            name="Rejected By",
            value=f"{ctx.author.username} ({ctx.author.id})",
            inline=False
        )
        rejected_embed.add_field(
            name="Rejection Reason",
            value=rejection_reason,
            inline=False
        )
        disabled_components = []
        for action_row in ctx.message.components:
            new_row = interactions.ActionRow()
            for component in action_row.components:
                if isinstance(component, interactions.Button):
                    if component.style != interactions.ButtonStyle.LINK:
                        component.disabled = True
                new_row.components.append(component)
            disabled_components.append(new_row)
        await ctx.message.edit(embed=rejected_embed, components=disabled_components)
        await ctx.send("Blacklist has been rejected!", ephemeral=True)
    
    @interactions.component_callback("view_images_direct")
    async def view_images_direct_clicked(self, ctx: interactions.ComponentContext):
        if not ctx.message.embeds[0].fields[2].value:
            await ctx.send("No images found in the folder.", ephemeral=True)
            return
        folder_id = ctx.message.embeds[0].fields[2].value
        folder_id = folder_id.split("/")[-1].rstrip(")")
        await ctx.send("Processing images...", ephemeral=True)
        image_files = self.drive.list_files(folder_id, images_only=True)
        if not image_files:
            await ctx.send("No images found in the folder.", ephemeral=True)
            return
        image_files = image_files[:10]
        if len(image_files) == 1:
            direct_url = self.drive.get_direct_image_url(image_files[0]['id'])
            embed = Embed(
                title="Blacklist Image",
                color=Color.random(),
                footer=EmbedFooter(text="Blacklist System"),
                timestamp=datetime.now().isoformat()
            )
            embed.set_image(url=direct_url)
            await ctx.send(embed=embed, ephemeral=True)
        else:
            embeds = []
            for index, image_file in enumerate(image_files):
                direct_url = self.drive.get_direct_image_url(image_file['id'])
                embed = Embed(
                    title=f"Blacklist Image {index + 1}/{len(image_files)}",
                    color=Color.random(),
                    footer=EmbedFooter(text=f"Blacklist System | Image {index + 1} of {len(image_files)}"),
                    timestamp=datetime.now().isoformat()
                )
                embed.set_image(url=direct_url)
                embeds.append(embed)
            paginator = Paginator.create_from_embeds(self.bot, *embeds)
            await paginator.send(ctx, ephemeral=True)
        
    @interactions.slash_command(name="unblacklist", description="Unblacklist a user")
    @interactions.slash_option(
        name="user",
        description="User to unblacklist",
        required=True,
        opt_type=OptionType.USER,
    )
    async def unblacklist(self, ctx: SlashContext, user: interactions.User):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        if not self.db_blacklist.exists(str(user.id)):
            await ctx.send(f"User <@{user.id}> is not blacklisted.", ephemeral=True)
        else:
            self.db_blacklist.delete_user(str(user.id))
            await ctx.send(f"User <@{user.id}> has been removed from the blacklist.", ephemeral=True)
        for guild in self.bot.guilds:
            try:
                await guild.unban(user)
            except Exception as e:
                print(f"Failed to unban user {user} in guild {guild.name}: {e}")
    
    @interactions.slash_command(name="sync", description="Sync new users from target server")
    async def sync_users(self, ctx: SlashContext):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You are not whitelisted!", ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:9191/stats') as resp:
                    if resp.status != 200:
                        await ctx.send("Failed to fetch stats from the scraper API", ephemeral=True)
                        return
                    stats = await resp.json()
                    
                if stats['new_members'] == 0:
                    await ctx.send("No new members found to process", ephemeral=True)
                    return
                    
                async with session.get('http://localhost:9191/members/new') as resp:
                    if resp.status != 200:
                        await ctx.send("Failed to fetch new members from the scraper API", ephemeral=True)
                        return
                    data = await resp.json()
                    new_members = data['new_member_ids']

            keys_values = self.db_blacklist.list_all_users_info()
            current_sync_hash = sha256(str(keys_values).encode('utf-8')).hexdigest()
            
            ban_results = {
                "success": 0,
                "failed": 0,
                "errors": []
            }

            await ctx.send(f"Found {len(new_members)} new users. Processing...", ephemeral=True)

            for user_id in new_members:
                try:
                    # Check if user is already in database
                    if self.db_blacklist.exists(str(user_id)):
                        continue
                        
                    user = await self.bot.fetch_user(int(user_id))
                    
                    # Create folder in Google Drive
                    folder_id = self.drive.create_folder(f"blacklist-{user.username}")
                    folder_link = f"https://drive.google.com/drive/folders/{folder_id}"
                    
                    # Add user to database
                    self.db_blacklist.set_user(
                        user_id=str(user_id),
                        username=str(user.username),
                        reason="Member of target server",
                        proof_link=folder_link,
                        folder_id=folder_id
                    )
                    
                    # Create embed for this user
                    embed = Embed(
                        title=f"{user.username}",
                        description="Here's some detailed information about the user:",
                        color=Color.random(),
                        fields=[
                            EmbedField(name="User ID", value=f"`{user_id}`", inline=True),
                            EmbedField(name="Created", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True),
                            EmbedField(name="📜 Reason", value="Member of target server", inline=False),
                            EmbedField(name="🔗 Proof Link", value=f"[Click Here]({folder_link})", inline=False)
                        ],
                        footer=EmbedFooter(text="Blacklist System"),
                        timestamp=datetime.now().isoformat()
                    )

                    # Ban user from all guilds and send embed to blacklist channels
                    for guild in self.bot.guilds:
                        try:
                            if not guild.me.guild_permissions.BAN_MEMBERS:
                                ban_results["failed"] += 1
                                ban_results["errors"].append(f"Missing permissions in {guild.name}")
                                continue
                                
                            await guild.ban(int(user_id), reason="Blacklisted: Target server member")
                            self.db_servers.set_last_sync_details(str(guild.id), current_sync_hash)
                            ban_results["success"] += 1
                            
                            # Send embed to blacklist channel
                            blacklist_channel = next(
                                (channel for channel in guild.channels 
                                if self.BLACKLIST_CHANNEL_PATTERN.match(channel.name) 
                                or channel.name in ["blacklist", "blacklists"]), 
                                None
                            )
                            if blacklist_channel:
                                await blacklist_channel.send(embed=embed)
                                
                        except Exception as e:
                            ban_results["failed"] += 1
                            ban_results["errors"].append(f"Failed in {guild.name}: {str(e)}")
                    
                except Exception as e:
                    print(f"Error processing user {user_id}: {e}")
                    continue

            # Send final summary
            total_guilds = len(self.bot.guilds)
            error_report = ""
            if ban_results["errors"]:
                unique_errors = list(set(ban_results["errors"]))[:5]
                error_report = "\n\nBan Errors:\n" + "\n".join(unique_errors)
                if len(ban_results["errors"]) > 5:
                    error_report += f"\n...and {len(ban_results['errors']) - 5} more errors"

            await ctx.send(
                f"Sync complete!\n"
                f"✅ Successfully banned in {ban_results['success']}/{total_guilds * len(new_members)} attempts\n"
                f"❌ Failed in {ban_results['failed']} attempts"
                f"{error_report}",
                ephemeral=True
            )

        except Exception as e:
            print(f"Error in sync command: {e}")
            await ctx.send(f"An error occurred while syncing: {str(e)}", ephemeral=True)