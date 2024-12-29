from interactions import Button, ButtonStyle, ComponentContext, Embed, EmbedField, Extension, Color, OptionType
import interactions
from utils.logutils import CustomLogger

class UtilityExtension(Extension):
    def __init__(self, bot):
        self.bot = bot
        self.logger = CustomLogger("UtilityExtension")
        
        # buyer role id
        self.roleid = 1262853951691296858
        # log to channel = true
        self.logToChannel = True
        # log channel id
        self.logChannel = 1262965364929728564
        self.logger.debug(f"Initialized with roleid={self.roleid}, logToChannel={self.logToChannel}, logChannel={self.logChannel}")
    
    @interactions.slash_command(name="sendrules", description="Send the rules of the server")
    async def send_(self, ctx):
        embed = Embed(title="Rules", description="Here are the rules of the server", color=Color.from_rgb(0, 0, 0),
                      fields=[EmbedField(name=f"Rule {i}", value=rule) for i, rule in enumerate([
                          "Respect my boundaries", "Do not share pictures without my consent",
                          "Respect that I am a university student and am often busy but will always get back to you 🌸",
                          "Always pay me before", "No scammers allowed", "I don't sell to minors",
                          "No hate speech or just generally being an asshole", "Be kind ☆彡"], start=1)])
        await ctx.send(embed=embed, components=[Button(label="✅ Verify", style=ButtonStyle.SUCCESS, custom_id="verify")])
    
    @interactions.component_callback("verify")
    async def verify_callback(self, ctx: ComponentContext):
        self.logger.debug(f"Verify callback triggered by user {ctx.author.id}")
        role = ctx.guild.get_role(self.roleid)
        if role is None:
            error_msg = f"The specified role ID ({self.roleid}) does not exist in the server."
            self.logger.error(error_msg)
            user = await self.bot.fetch_user(968929214281683035)
            embed = Embed(title="DEBUG: Role Not Found", description=error_msg, color=Color.from_rgb(255, 0, 0))
            await user.send(embed=embed)
        elif role not in ctx.author.roles:
            self.logger.info(f"Adding verify role to user {ctx.author.id}")
            await ctx.author.add_role(role)
            await ctx.send(f"✅ {ctx.author.mention}, thank you for verifying! You now have access to the channels. Welcome and enjoy your stay! 😊", ephemeral=True)
            if self.logToChannel:
                log_channel = ctx.guild.get_channel(self.logChannel)
                if log_channel is None:
                    error_msg = f"The specified log channel ID ({self.logChannel}) does not exist in the server."
                    self.logger.error(error_msg)
                    user = await self.bot.fetch_user(968929214281683035)
                    embed = Embed(title="DEBUG: Log Channel Not Found", description=error_msg, color=Color.from_rgb(255, 0, 0))
                    await user.send(embed=embed)
                else:
                    self.logger.debug(f"Sending verification log for user {ctx.author.id}")
                    embed = Embed(title="User Verified", color=Color.random(), fields=[EmbedField(name="User", value=f"{ctx.author.mention} ({ctx.author.id})"), EmbedField(name="Account Created", value=f"<t:{int(ctx.author.created_at.timestamp())}:F>"), EmbedField(name="Joined Server", value=f"<t:{int(ctx.author.joined_at.timestamp())}:F>")], thumbnail=ctx.author.avatar_url, footer=f"User ID: {ctx.author.id}")
                    await log_channel.send(embed=embed)
        else:
            self.logger.debug(f"User {ctx.author.id} attempted to verify but was already verified")
            await ctx.send("You are already verified!", ephemeral=True)

    @interactions.slash_command(name="testconfig", description="Test the configuration values")
    async def test_config(self, ctx):
        server_id = str(ctx.guild.id)
        # TODO: 
        # self.load_config(server_id)
        self.logger.debug(f"Current config - Role ID: {self.roleid}, Log to Channel: {self.logToChannel}, Log Channel: {self.logChannel}")
        await ctx.send(f"Server ID: {server_id}\nRole ID: {self.roleid}\nLog to Channel: {self.logToChannel}\nLog Channel: {self.logChannel}", ephemeral=True)

    @interactions.slash_command(
        name="send_dm",
        description="Send a DM to a user",
    )
    @interactions.slash_option(
        name="user",
        description="The user to send the DM to",
        opt_type=OptionType.USER,
        required=True
    )
    async def send_dm(self, ctx, user: interactions.Member):
        await user.send("Hello!")
