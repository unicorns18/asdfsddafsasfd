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

    @test.subcommand(
        sub_cmd_name="echo",
        sub_cmd_description="Echo back your message"
    )
    @slash_option(
        name="message",
        description="The message to echo back",
        required=True,
        opt_type=OptionType.STRING
    )
    async def test_echo(self, ctx: SlashContext, message: str):
        """Echo subcommand - repeats your message"""
        await ctx.send(f"You said: {message}")

    @test.subcommand(
        sub_cmd_name="math",
        sub_cmd_description="Perform basic math operations"
    )
    @slash_option(
        name="operation",
        description="The math operation to perform",
        required=True,
        opt_type=OptionType.STRING,
        choices=[
            "add",
            "subtract",
            "multiply",
            "divide"
        ]
    )
    @slash_option(
        name="number1",
        description="First number",
        required=True,
        opt_type=OptionType.NUMBER
    )
    @slash_option(
        name="number2",
        description="Second number",
        required=True,
        opt_type=OptionType.NUMBER
    )
    async def test_math(self, ctx: SlashContext, operation: str, number1: float, number2: float):
        """Math subcommand - performs basic calculations"""
        result = None
        if operation == "add":
            result = number1 + number2
        elif operation == "subtract":
            result = number1 - number2
        elif operation == "multiply":
            result = number1 * number2
        elif operation == "divide":
            if number2 == 0:
                await ctx.send("Error: Cannot divide by zero!")
                return
            result = number1 / number2

        await ctx.send(f"{number1} {operation} {number2} = {result}")

def setup(bot):
    TestExtension(bot)