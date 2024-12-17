import re
from interactions import Button, ButtonStyle, ComponentContext, Embed, EmbedField, Extension, Color
import interactions
import os
import json
from datetime import datetime

class LoggerExtension(Extension):
    def __init__(self, bot):
        self.bot = bot
        self.base_path = "~/ServerLogs"
    
    def clean_name(self, name):
        # Remove special characters and spaces, replace with underscores
        return re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')
    
    def ensure_directory(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            
    def load_messages(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []
    
    def save_messages(self, file_path, messages):
        with open(file_path, 'w') as f:
            json.dump(messages, f, indent=4)
    
    @interactions.listen()
    async def on_message_create(self, event):
        message = event.message
        
        # Get IDs and names
        channel_id = str(message._channel_id)
        channel_name = self.clean_name(message.channel.name)
        
        guild_id = str(message._guild_id)
        try:
            guild_name = self.clean_name(message.guild.name)
        except AttributeError:
            guild_name = "None"
        
        author_id = str(message.author.id)
        author_name = self.clean_name(message.author.username)
        
        # Create descriptive directory names
        guild_dir = f"{guild_id}_{guild_name}"
        channel_dir = f"{channel_id}_{channel_name}"
        author_dir = f"{author_id}_{author_name}"
        
        # Create path
        path = os.path.expanduser(f"{self.base_path}/{guild_dir}/{channel_dir}/{author_dir}")
        self.ensure_directory(path)
        
        # Message file path
        message_file = f"{path}/messages.json"
        
        # Load existing messages
        messages = self.load_messages(message_file)
        
        # Create new message entry
        new_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "content": message.content,
            "message_id": str(message.id)
        }
        
        # Append new message
        messages.append(new_message)
        
        # Save updated messages
        self.save_messages(message_file, messages)
        
        print(f"Logged message from {author_name} ({author_id}) in {channel_name} ({channel_id}) on {guild_name} ({guild_id})")