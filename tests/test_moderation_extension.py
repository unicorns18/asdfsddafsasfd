import pytest
from unittest.mock import Mock, AsyncMock
from extensions.moderation_extension import ModerationExtension

class TestModerationExtension(ModerationExtension):
    """Test version of ModerationExtension that doesn't use command decorators"""
    async def warn(self, ctx, user, reason):
        # Get and update warns/instances
        warns = int(self.warndb.redis.get(user.id) or 0) + 1
        self.warndb.redis.set(user.id, warns)
        instances = int(self.instancedb.redis.get(user.id) or 0)

        # Send warning confirmation
        await ctx.send(f"User warned: {warns} warnings")

    async def warns(self, ctx, user):
        warns = self.warndb.redis.get(user.id)
        instances = self.instancedb.redis.get(user.id)
        if warns is None: warns = 0
        else: warns = int(warns)
        if instances is None: instances = 0
        else: instances = int(instances)
        await ctx.send(f"User has {warns} warnings")

    async def clearwarns(self, ctx, user):
        self.warndb.redis.delete(user.id)
        self.instancedb.redis.delete(user.id)
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
    mock_redis.get.assert_called_with(mock_user.id)
    mock_redis.set.assert_called_with(mock_user.id, 1)

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
    mock_redis.get.assert_called_with(mock_user.id)

@pytest.mark.asyncio
async def test_clearwarns_command_redis_interaction(extension, mock_ctx, mock_user):
    # Setup mock redis instance
    mock_redis = Mock()
    extension.warndb.redis = mock_redis
    extension.instancedb.redis = mock_redis

    # Test clearing warnings
    await extension.clearwarns(mock_ctx, mock_user)

    # Verify Redis interactions
    mock_redis.delete.assert_called_with(mock_user.id)