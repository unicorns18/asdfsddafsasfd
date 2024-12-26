import aiohttp
from interactions import Extension, slash_command, SlashContext, OptionType, slash_option
from typing import Dict
import re
import interactions
from database import RedisDB

class GrokExtension(Extension):
    def __init__(self, bot):
        self.bot = bot
        self.is_enabled = False
        self.target_user_id = 1157027347384512552
        self.GROK_API_URL = "https://api.x.ai/v1/chat/completions"
        self.XAI_API_KEY = "xai-czITW7TJknSkYVomS8ztaHrT5dO7NobmZKWQzBcwYdpJ04nMIDeRVlVpXq3onW6FfMirh9THYSMWzdCW"
        self.SHREK_SYSTEM_PROMPT = """You are Grok, but you've been transformed by a magical potion into Shrek. 
        You must respond to all questions in Shrek's voice and mannerisms, using his catchphrases, 
        and occasionally referencing his swamp, Donkey, or other Shrek characters. 
        Keep your responses witty, slightly grumpy, but wise - just like Shrek would.
        Provide only one or two sentences as response."""
        
        # Whitelist setup
        self.db_whitelist = RedisDB(db=1)
        self.WHITELIST_KEY = "whitelist"
        self.FORCE_OVERRIDE_USER_ID = [
            "686107711829704725", 
            "708812851229229208", 
            "1259678639159644292", 
            "1168346688969252894"
        ]

    async def is_user_whitelisted(self, user_id):
        if str(user_id) in self.FORCE_OVERRIDE_USER_ID:
            return True
        return self.db_whitelist.redis.sismember(self.WHITELIST_KEY, str(user_id))

    def truncate_to_complete_sentence(self, text: str) -> str:
        sentence_endings = list(re.finditer(r'[.!?][\s"\')]?', text))
        if not sentence_endings:
            return text
        last_sentence_end = sentence_endings[0].end()
        return text[:last_sentence_end].strip()

    async def get_grok_response(self, message: str) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.XAI_API_KEY}"
        }
        
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": self.SHREK_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            "model": "grok-2-1212",
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 100
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.GROK_API_URL, json=payload, headers=headers) as response:
                if response.status != 200:
                    return "Donkey, something went wrong with my swamp connection!"
                
                response_data = await response.json()
                try:
                    grok_response = response_data['choices'][0]['message']['content']
                    return self.truncate_to_complete_sentence(grok_response)
                except (KeyError, IndexError):
                    return "Donkey, something went wrong with my response!"

    @slash_command(
        name="grok_toggle",
        description="Toggle Grok responses on/off"
    )
    async def grok_toggle(self, ctx: SlashContext):
        # Check if user is whitelisted
        if not await self.is_user_whitelisted(ctx.author.id):
            await ctx.send("You don't have permission to use this command!", ephemeral=True)
            return

        self.is_enabled = not self.is_enabled
        status = "enabled" if self.is_enabled else "disabled"
        await ctx.send(f"Grok responses are now {status}!", ephemeral=True)

    @interactions.listen()
    async def on_message_create(self, event):
        if not self.is_enabled:
            return
            
        if event.message.author.id != self.target_user_id:
            return
            
        if event.message.author.bot:
            return

        response = await self.get_grok_response(event.message.content)
        await event.message.reply(response)
