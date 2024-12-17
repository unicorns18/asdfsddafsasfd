import json
from interactions import Client
from utils import logutils
import interactions
import os

logger = logutils.CustomLogger(__name__)

TOKEN = "MTMxNjYwNjc2NTkwMjg1NjM2NA.GJN7qe.Ue1FT3hdkJQ8aBRqZcF42R-cnHnhBqQVxRx_0U"
DEBUG = True

client = Client(
    # token="MTMxNjYwNjc2NTkwMjg1NjM2NA.GJN7qe.Ue1FT3hdkJQ8aBRqZcF42R-cnHnhBqQVxRx_0U",
    token=TOKEN if not DEBUG else "MTI3MjQ2NjE1NzIyMzQxNTg2Mg.GH41lQ.wTb3JQoWQH9Xi161CABKxYCf9H_9oKUED7iEP0",
    intents=interactions.Intents.ALL,
    activity=interactions.Activity(
        name="mew", type=interactions.ActivityType.PLAYING
    ),
)

@client.listen()
async def on_ready():
    logger.info(f"We have logged in as {client.app.name}")
    logger.info(f"User ID: {client.app.id}")
    logger.info(f"Connected to {len(client.guilds)} guilds")
    logger.info(f"Connected to {client.guilds}")


if __name__ == '__main__':
    extensions = [
        f"extensions.{f[:-3]}"
        for f in os.listdir("extensions")
        if f.endswith(".py") and not f.startswith("_")
    ]
    for extension in extensions:
        try:
            client.load_extension(extension)
            logger.info(f"Loaded extension {extension}")
        except interactions.errors.ExtensionLoadException as e:
            logger.error(f"Failed to load extension {extension}.", exc_info=e)

    client.start()
