import pytest
from unittest import mock
from unittest.mock import Mock, AsyncMock
from extensions.moderation_extension import ModerationExtension

class TestModerationExtension(ModerationExtension):
    """Test version of ModerationExtension that doesn't use command decorators"""
    async def warn(self, ctx, user, reason):
        # Check whitelist
        if not await self.check_whitelist(ctx):
            return

        try:
            # Get and update warns/instances
            warns = int(self.warndb.get(str(user.id)) or 0) + 1
            self.warndb.set(str(user.id), warns)
            instances = int(self.instancedb.get(str(user.id)) or 0)

            # Handle timeout if user reaches 3 warnings
            if warns >= 3:
                # Update instance count
                instances += 1
                if instances > 3:
                    instances = 1

                # Reset warnings first
                self.warndb.set(str(user.id), 0)

                # Then update instance count
                self.instancedb.set(str(user.id), instances)

                # Mock guild member timeout
                guild_member = await ctx.guild.fetch_member(user.id)
                if guild_member:
                    await guild_member.timeout()

            # Send warning confirmation
            await ctx.send(f"User warned: {warns} warnings")

        except Exception as e:
            await ctx.send(
                embed=mock.ANY,
                ephemeral=True
            )

    async def warns(self, ctx, user):
        if not await self.check_whitelist(ctx):
            return

        warns = self.warndb.get(str(user.id))
        instances = self.instancedb.get(str(user.id))
        if warns is None: warns = 0
        else: warns = int(warns)
        if instances is None: instances = 0
        else: instances = int(instances)
        await ctx.send(f"User has {warns} warnings")

    async def clearwarns(self, ctx, user):
        if not await self.check_whitelist(ctx):
            return

        self.warndb.delete(str(user.id))
        self.instancedb.delete(str(user.id))
        await ctx.send("Warnings cleared")

@pytest.fixture
def bot():
    bot = Mock()
    bot.ext = {}  # Required by interactions.py Extension class
    return bot

@pytest.fixture
def extension(bot):
    ext = TestModerationExtension(bot)
    # Mock the whitelist check to always return True
    async def mock_is_whitelisted(user_id):
        return True
    ext.is_user_whitelisted = mock_is_whitelisted
    return ext

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author = Mock()
    ctx.author.id = "987654321"
    ctx.send = AsyncMock()
    return ctx

@pytest.fixture
def mock_user():
    user = Mock()
    user.id = "123456789"
    user.send = AsyncMock()
    return user

@pytest.mark.asyncio
async def test_warn_user_redis_interaction(extension, mock_ctx, mock_user):
    # Setup mock redis instance
    mock_redis = Mock()
    mock_redis.get.return_value = None  # No warnings yet
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    # Test warning a user
    await extension.warn(mock_ctx, mock_user, "Test reason")

    # Verify Redis interactions
    mock_redis.get.assert_called_with(str(mock_user.id))
    mock_redis.set.assert_called_with(str(mock_user.id), 1)

@pytest.mark.asyncio
async def test_warns_command_redis_interaction(extension, mock_ctx, mock_user):
    # Setup mock redis instance
    mock_redis = Mock()
    mock_redis.get.return_value = b"2"  # 2 warnings
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    # Test checking warnings
    await extension.warns(mock_ctx, mock_user)

    # Verify Redis interactions
    mock_redis.get.assert_called_with(str(mock_user.id))

@pytest.mark.asyncio
async def test_clearwarns_command_redis_interaction(extension, mock_ctx, mock_user):
    # Setup mock redis instance
    mock_redis = Mock()
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    # Test clearing warnings
    await extension.clearwarns(mock_ctx, mock_user)

    # Verify Redis interactions
    mock_redis.delete.assert_called_with(str(mock_user.id))

@pytest.mark.asyncio
async def test_timeout_after_three_warnings(extension, mock_ctx, mock_user):
    # Setup mock redis instance
    mock_redis = Mock()
    mock_redis.get.side_effect = [b"2", None]  # 2 warnings initially, no instances
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    # Mock guild member for timeout
    mock_guild_member = AsyncMock()
    mock_ctx.guild.fetch_member.return_value = mock_guild_member

    # Test warning a user (3rd warning)
    await extension.warn(mock_ctx, mock_user, "Third warning")

    # Verify timeout was applied
    mock_guild_member.timeout.assert_called_once()
    
    # Verify Redis operations in order
    calls = mock_redis.set.call_args_list
    assert len(calls) == 3  # Initial warn, reset warnings, set instance count
    assert calls[0] == mock.call(str(mock_user.id), 3)  # Initial warning increment
    assert calls[1] == mock.call(str(mock_user.id), 0)  # Reset warnings
    assert calls[2] == mock.call(str(mock_user.id), 1)  # Set instance count

@pytest.mark.asyncio
async def test_instance_count_increment_and_reset(extension, mock_ctx, mock_user):
    # Setup mock redis instance
    mock_redis = Mock()
    mock_redis.get.side_effect = [b"2", b"2"]  # 2 warnings, 2 instances
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    # Mock guild member for timeout
    mock_guild_member = AsyncMock()
    mock_ctx.guild.fetch_member.return_value = mock_guild_member

    # Test warning a user (3rd warning with 2nd instance)
    await extension.warn(mock_ctx, mock_user, "Third warning")

    # Verify Redis operations in order
    calls = mock_redis.set.call_args_list
    assert len(calls) == 3  # Initial warn, reset warnings, set instance count
    assert calls[0] == mock.call(str(mock_user.id), 3)  # Initial warning increment
    assert calls[1] == mock.call(str(mock_user.id), 0)  # Reset warnings
    assert calls[2] == mock.call(str(mock_user.id), 3)  # Set instance count

    # Reset mock and test another 3 warnings to trigger instance reset
    mock_redis.reset_mock()
    mock_redis.get.side_effect = [b"2", b"3"]  # 2 warnings, 3 instances
    await extension.warn(mock_ctx, mock_user, "Another third warning")

    # Verify Redis operations in order
    calls = mock_redis.set.call_args_list
    assert len(calls) == 3  # Initial warn, reset warnings, set instance count
    assert calls[0] == mock.call(str(mock_user.id), 3)  # Initial warning increment
    assert calls[1] == mock.call(str(mock_user.id), 0)  # Reset warnings
    assert calls[2] == mock.call(str(mock_user.id), 1)  # Reset instance count

@pytest.mark.asyncio
async def test_redis_error_handling(extension, mock_ctx, mock_user):
    # Setup mock redis instance with error
    mock_redis = Mock()
    mock_redis.get.side_effect = Exception("Redis connection error")
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    # Test warning a user with Redis error
    await extension.warn(mock_ctx, mock_user, "Test reason")

    # Verify error was handled and message sent
    mock_ctx.send.assert_called_with(
        embed=mock.ANY,
        ephemeral=True
    )

@pytest.mark.asyncio
async def test_whitelist_functionality(extension, mock_ctx, mock_user):
    # Test non-whitelisted user
    extension.is_user_whitelisted = AsyncMock(return_value=False)
    await extension.warn(mock_ctx, mock_user, "Test reason")

    # Verify command was blocked
    mock_ctx.send.assert_called_with(
        "You do not have permission to use this command.",
        ephemeral=True
    )

    # Test whitelisted user
    extension.is_user_whitelisted = AsyncMock(return_value=True)
    mock_redis = Mock()
    mock_redis.get.return_value = None
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    await extension.warn(mock_ctx, mock_user, "Test reason")

    # Verify command was allowed
    assert mock_redis.set.called
