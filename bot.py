import json
import discord
import asyncio
import logging
from discord.ext import commands
from utility.database import Database
import config
import os

EXTENSIONS = ["debug", "fun", "voting", "scanner", "xkcd", "jolly"]

class MiniSigma(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.db = Database()
        self.config = config

    async def setup_hook(self):
        for ext in EXTENSIONS:
            try:
                await self.load_extension('cogs.' + ext)
                logger.info(f"Succesfully loaded cogs.{ext}")
            except Exception as e:
                pass
                logger.info(f"Failed to load extension: {e}")

    async def on_ready(self):
        synced = await self.tree.sync()
        logger.info(f"Synced {len(synced)} app commands")
        logger.info(f"{self.user} is now running!")

if __name__ == '__main__':
    logger = logging.getLogger('client')
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("bot.log")
    file_handler.setFormatter(logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{'))

    logging.getLogger().addHandler(file_handler)

    token = os.getenv("DISCORD_BOT_TOKEN")
    MiniSigma().run(token=token, root_logger=True)