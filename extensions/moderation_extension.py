import datetime
from interactions import Button, ButtonStyle, Embed, EmbedField, Extension, Color, OptionType
import interactions
from redis import Redis

class ModerationExtension(Extension):
    def __init__(self, bot):
        self.bot = bot
        self.warndb = Redis(db=4)
        self.instancedb = Redis(db=5)
        self.db_whitelist = Redis(db=1)
        self.FORCE_OVERRIDE_USER_ID = ["686107711829704725", "708812851229229208", "1259678639159644292", "1168346688969252894"]
        self.WHITELIST_KEY = "warn_whitelist"
        self.TIMEOUT_FIRST_INSTANCE = datetime.timedelta(minutes=5)
        self.TIMEOUT_SECOND_INSTANCE = datetime.timedelta(hours=1)
        self.TIMEOUT_THIRD_INSTANCE = datetime.timedelta(days=1)

    async def is_user_whitelisted(self, user_id):
        if str(user_id) in self.FORCE_OVERRIDE_USER_ID:
            return True
        return self.db_whitelist.sismember(self.WHITELIST_KEY, str(user_id))

    async def check_whitelist(self, ctx):
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return False
        return True

    @interactions.slash_command(
        name="warn",
        description="Warn a user"
    )
    @interactions.slash_option(
        name="user",
        description="The user to warn",
        required=True,
        opt_type=OptionType.USER
    )
    @interactions.slash_option(
        name="reason",
        description="The reason for the warning",
        required=True,
        opt_type=OptionType.STRING
    )
    async def warn(self, ctx, user, reason):
        # Check permissions
        if not await self.check_whitelist(ctx):
            return

        # Get and update warns/instances
        warns = int(self.warndb.get(user.id) or 0) + 1
        self.warndb.set(user.id, warns)
        instances = int(self.instancedb.get(user.id) or 0)

        # Calculate timeout info based on instances
        next_timeout = "5 minutes" if instances == 0 else "1 hour" if instances == 1 else "1 day"

        # Send warning DM to user
        dm_embed = Embed(
            title="You Have Been Warned",
            color=Color.from_rgb(255, 0, 0),
            description=f"**Reason:** {reason}"
        )
        dm_embed.set_author(name=ctx.author.username, icon_url=ctx.author.avatar_url)
        dm_embed.add_field(name="Current Warning Count", value=f"{warns}/3")
        
        warnings_until_timeout = 3 - warns
        if warnings_until_timeout > 0:
            dm_embed.add_field(
                name="Time Until Timeout",
                value=f"In {warnings_until_timeout} warning{'s' if warnings_until_timeout != 1 else ''}, "
                    f"you'll be timed out for {next_timeout}."
            )

        try:
            await user.send(embed=dm_embed)
        except:
            pass

        # Handle timeout if user reaches 3 warnings
        if warns == 3:
            # Update instance count
            instances += 1
            if instances > 3:
                instances = 1
            self.instancedb.set(user.id, instances)

            # Set timeout duration based on instance
            if instances == 1:
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + self.TIMEOUT_FIRST_INSTANCE
                timeout_str = "5 minutes"
            elif instances == 2:
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + self.TIMEOUT_SECOND_INSTANCE
                timeout_str = "1 hour"
            elif instances == 3:
                timeout_until = datetime.datetime.now(datetime.timezone.utc) + self.TIMEOUT_THIRD_INSTANCE
                timeout_str = "1 day"
                self.instancedb.set(user.id, 0)

            # Attempt to timeout the user in the current guild
            timeout_success = False
            try:
                guild_member = await ctx.guild.fetch_member(user.id)
                if guild_member:
                    await guild_member.timeout(
                        communication_disabled_until=timeout_until,
                        reason=f"Warned by {ctx.author.display_name}: {reason}"
                    )
                    timeout_success = True
                else:
                    await ctx.send(
                        embed=Embed(
                            title="Error",
                            color=Color.from_rgb(255, 0, 0),
                            description="Could not find the member in this server."
                        ),
                        ephemeral=True
                    )
            except interactions.client.errors.Forbidden:
                await ctx.send(
                    embed=Embed(
                        title="Error",
                        color=Color.from_rgb(255, 0, 0),
                        description="I don't have permission to timeout this user. Please check my role permissions."
                    ),
                    ephemeral=True
                )
            except Exception as e:
                await ctx.send(
                    embed=Embed(
                        title="Error",
                        color=Color.from_rgb(255, 0, 0),
                        description=f"An error occurred while trying to timeout the user: {str(e)}"
                    ),
                    ephemeral=True
                )

            # Reset warnings
            self.warndb.set(user.id, 0)

            # Send timeout notifications if successful
            if timeout_success:
                # Send channel notification
                timeout_embed = Embed(
                    title="User Timed Out",
                    color=Color.from_rgb(255, 0, 0),
                    description=f"{user.mention} has been timed out for {timeout_str} due to reaching 3 warnings."
                )
                if instances == 3:
                    timeout_embed.description += "\nAll warnings and instances have been reset."
                await ctx.send(embed=timeout_embed, ephemeral=True)

                # Send DM notification
                try:
                    timeout_dm_embed = Embed(
                        title="You Have Been Timed Out",
                        color=Color.from_rgb(255, 0, 0),
                        description=f"You have been timed out for {timeout_str} due to reaching 3 warnings in {ctx.guild.name}."
                    )
                    if instances == 3:
                        timeout_dm_embed.description += "\nAll your warnings and instances have been reset."
                    timeout_dm_embed.set_author(name=ctx.author.username, icon_url=ctx.author.avatar_url)
                    await user.send(embed=timeout_dm_embed)
                except:
                    pass

        # Send warning confirmation
        warn_embed = Embed(
            title="User Warned",
            color=Color.from_rgb(255, 0, 0),
            description=f"{user.mention} has been warned for: {reason}"
        )
        warn_embed.add_field(name="Current Warn Count", value=f"{warns}")
        warn_embed.add_field(name="Current Warning Instance", value=f"{instances}")
        warn_embed.set_footer(text="At 3 warnings, the user will be timed out.")
        await ctx.send(embed=warn_embed, ephemeral=True)
    
    @interactions.slash_command(
        name="warns",
        description="Check the number of warns a user has"
    )
    @interactions.slash_option(
        name="user",
        description="The user to check",
        required=True,
        opt_type=OptionType.USER
    )
    async def warns(self, ctx, user):
        if not await self.check_whitelist(ctx):
            return
        warns = self.warndb.get(user.id)
        instances = self.instancedb.get(user.id)
        if warns is None: warns = 0
        else: warns = int(warns)
        if instances is None: instances = 0
        else: instances = int(instances)
        warn_embed = Embed(
            title=f"Warning Information for {user.display_name}",
            color=Color.random()
        )
        warn_embed.add_field(name="Current Warn Count", value=f"{warns}")
        warn_embed.add_field(name="Total Warning Instances", value=f"{instances}")
        await ctx.send(embed=warn_embed, ephemeral=True)
    
    @interactions.slash_command(
        name="clearwarns",
        description="Clear the warns of a user"
    )
    @interactions.slash_option(
        name="user",
        description="The user to clear warns for",
        required=True,
        opt_type=OptionType.USER
    )
    async def clearwarns(self, ctx, user):
        if not await self.check_whitelist(ctx):
            return
        self.warndb.delete(user.id)
        self.instancedb.delete(user.id)
        clear_embed = Embed(
            title="Warnings Cleared",
            color=Color.random(),
            description=f"All warnings have been cleared for {user.mention}."
        )
        await ctx.send(embed=clear_embed, ephemeral=True)
    
    ### end warn command stuff ###