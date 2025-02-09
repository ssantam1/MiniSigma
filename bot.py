import discord
import logging
from discord.ext import commands
from utility.database import Database
from config import TOKEN, EXTENSIONS
import os
import colorama
import json

colorama.init()
logger = logging.getLogger("client")

class MiniSigma(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.db = Database()

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
    file_handler = logging.FileHandler("bot.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', '%Y-%m-%d %H:%M:%S', style='{'))

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

    MiniSigma().run(token=TOKEN, log_handler=logging.StreamHandler(), log_formatter=discord.utils._ColourFormatter(), root_logger=True)