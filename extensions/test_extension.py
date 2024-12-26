from interactions import (
    Extension,
    slash_command,
    SlashContext,
    OptionType,
    slash_option
)

class TestExtension(Extension):
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger

    @slash_command(
        name="test",
        description="Base test command with subcommands"
    )
    async def test(self, ctx: SlashContext):
        """Base command - shows help text"""
        await ctx.send("Use one of the subcommands:\n- /test ping - Basic ping test\n- /test echo - Echo back your message")

    @test.subcommand(
        sub_cmd_name="ping",
        sub_cmd_description="Basic ping test"
    )
    async def test_ping(self, ctx: SlashContext):
        """Ping subcommand - tests bot response"""
        await ctx.send("Pong! 🏓")