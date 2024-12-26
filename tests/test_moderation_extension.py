import unittest
from unittest.mock import Mock, patch
import pytest
from extensions.moderation_extension import ModerationExtension

class TestModerationExtension(unittest.TestCase):
    def setUp(self):
        self.bot = Mock()
        self.bot.ext = {}  # Required by interactions.py Extension class
        self.extension = ModerationExtension(self.bot)
        
    @pytest.mark.asyncio
    async def test_warn_user_redis_interaction(self):
        # Setup mock redis instance
        mock_redis_instance = Mock()
        mock_redis_instance.get.return_value = None  # Simulate no warnings yet
        self.extension.warndb.redis = mock_redis_instance
        self.extension.instancedb.redis = mock_redis_instance
        
        # Create mock user and context
        mock_user = Mock()
        mock_user.id = "123456789"
        mock_ctx = Mock()
        mock_ctx.author.id = "987654321"
        mock_ctx.send = Mock()  # Mock the send method
        
        # Mock whitelist check to return True
        self.extension.is_user_whitelisted = Mock(return_value=True)
        
        # Call warn method
        await self.extension.warn(mock_ctx, mock_user, "Test reason")
        
        # Verify Redis interactions
        mock_redis_instance.get.assert_called_with(mock_user.id)
        mock_redis_instance.set.assert_called_with(mock_user.id, 1)  # First warning should set to 1

    @pytest.mark.asyncio
    async def test_warns_command_redis_interaction(self):
        # Setup mock redis instance
        mock_redis_instance = Mock()
        mock_redis_instance.get.return_value = b"2"  # Simulate 2 warnings
        self.extension.warndb.redis = mock_redis_instance
        self.extension.instancedb.redis = mock_redis_instance
        
        # Create mock user and context
        mock_user = Mock()
        mock_user.id = "123456789"
        mock_ctx = Mock()
        mock_ctx.author.id = "987654321"
        mock_ctx.send = Mock()  # Mock the send method
        
        # Mock whitelist check to return True
        self.extension.is_user_whitelisted = Mock(return_value=True)
        
        # Call warns method
        await self.extension.warns(mock_ctx, mock_user)
        
        # Verify Redis interactions
        mock_redis_instance.get.assert_called_with(mock_user.id)

    @pytest.mark.asyncio
    async def test_clearwarns_command_redis_interaction(self):
        # Setup mock redis instance
        mock_redis_instance = Mock()
        self.extension.warndb.redis = mock_redis_instance
        self.extension.instancedb.redis = mock_redis_instance
        
        # Create mock user and context
        mock_user = Mock()
        mock_user.id = "123456789"
        mock_ctx = Mock()
        mock_ctx.author.id = "987654321"
        mock_ctx.send = Mock()  # Mock the send method
        
        # Mock whitelist check to return True
        self.extension.is_user_whitelisted = Mock(return_value=True)
        
        # Call clearwarns method
        await self.extension.clearwarns(mock_ctx, mock_user)
        
        # Verify Redis interactions
        mock_redis_instance.delete.assert_called_with(mock_user.id)