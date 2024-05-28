import discord
from discord.ext import commands, tasks
from discord import app_commands
from bot import MiniSigma
import os
import logging
import json
import aiohttp
from typing import Literal
from utility.config import *

logger = logging.getLogger("client.xkcd")

AVATAR_URL = None

async def get_xkcd_embed(session: aiohttp.ClientSession, comic_num: int = None) -> discord.Embed:
    ''' Returns embed with XKCD comic. comic_num defaults to latest comic. '''
    comic_num: str = "" if comic_num is None else str(comic_num) + '/'
    embed = discord.Embed(color=EMBED_COLOR)

    try:
        async with session.get(f"https://xkcd.com/{comic_num}info.0.json") as response:
            data = await response.json()
        embed.set_author(name=f"{data['num']} - {data['safe_title']}", icon_url=AVATAR_URL)
        embed.set_image(url=data['img'])
        embed.set_footer(text=data['alt'])

    except Exception as error:
        logger.warning(f"Unable to fetch xkcd embed: {error}")
        embed.set_author(name=f"XKCD Fetch Error", icon_url=AVATAR_URL)
        embed.set_image(url="")
        embed.set_footer(text="Tell @theothermaurice to fix this __NOW__!")

    return embed

class ComicView(discord.ui.View):
    def __init__(self, session: aiohttp.ClientSession, max_num):
        super().__init__(timeout=None)
        self.session = session
        self.max_num = max_num
        self.cur_num = self.max_num

    def is_valid_num(self, num: int) -> bool:
        return True if num > 0 and num <= self.max_num else False

    def update_buttons(self):
        self.left_button.disabled = True if self.cur_num <= 1 else False
        self.right_button.disabled = True if self.cur_num >= self.max_num else False

    @discord.ui.button(label="Back", emoji="⬅️")
    async def left_button(self, interaction: discord.Interaction, _: discord.Button):
        self.cur_num -= 1
        self.update_buttons()
        embed = await get_xkcd_embed(self.session, self.cur_num)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Jump", emoji="#️⃣")
    async def middle_button(self, interaction: discord.Interaction, _: discord.Button):
        await interaction.response.send_modal(PageNumInputModal(self.session, self))

    @discord.ui.button(label="Next", emoji="➡️", disabled=True)
    async def right_button(self, interaction: discord.Interaction, _: discord.Button):
        self.cur_num += 1
        self.update_buttons()
        embed = await get_xkcd_embed(self.session, self.cur_num)
        await interaction.response.edit_message(embed=embed, view=self)

class PageNumInputModal(discord.ui.Modal):
    ''' Modal for the page jump button '''
    def __init__(self, session: aiohttp.ClientSession, view: ComicView):
        super().__init__(title="Page Number Input")
        self.session = session
        self.view = view
    
    number = discord.ui.TextInput(label="Page Number:")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            selection = int(self.number.value)
        except ValueError:
            await interaction.response.send_message('Invalid input! Please enter an integer.', ephemeral=True)
            return

        if not self.view.is_valid_num(selection):
            await interaction.response.send_message(f'Invalid input! Please enter a number between 1 and {self.view.max_num}.', ephemeral=True)
            return

        self.view.cur_num = selection
        self.view.update_buttons()
        await interaction.response.edit_message(embed=await get_xkcd_embed(self.session, selection), view=self.view)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message(f'Oops! @theothermaurice is dumb!\nScreenshot this error and send it to him!\n`{error}`', ephemeral=True)

class XKCD(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.subscribed_channels = set()
        self.latest_comic = 0
        self.session = aiohttp.ClientSession()

        self.load_subscriptions()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.check_for_new_comic.start()

    def load_subscriptions(self):
        try:
            with open("cogs/xkcd.json", "r") as f:
                data: dict = json.load(f)
                self.subscribed_channels = set(data.get("subscribed_channels", []))
                self.latest_comic = data.get("latest_comic", 0)
        except FileNotFoundError:
            logger.warning("No xkcd.json file found. Creating new one.")
            self.save_subscriptions()

    def save_subscriptions(self):
        data = {"subscribed_channels": list(self.subscribed_channels), "latest_comic": self.latest_comic}
        with open("cogs/xkcd.json", "w") as f:
            json.dump(data, f)

    async def get_latest_comic_num(self) -> int:
        try:
            async with self.session.get("https://xkcd.com/info.0.json") as response:
                data = await response.json()
                return data['num']
        except Exception as error:
            logger.warning(f"Failed to get latest comic num: {error}")
            return self.latest_comic

    @tasks.loop(minutes=10, reconnect=True)
    async def check_for_new_comic(self):
        latest_comic_num = await self.get_latest_comic_num()
        if self.latest_comic != latest_comic_num:
            self.latest_comic = latest_comic_num

            self.save_subscriptions()
            embed = await get_xkcd_embed(self.session)

            logger.info(f"New comic found! Posting {self.latest_comic} to subscribed channels...")

            for channel_id in self.subscribed_channels:
                channel = self.client.get_channel(channel_id)
                if channel is not None:
                    await channel.send(content="New XKCD! Use `/xkcd unsubscribe` to stop recieving automatic messages here.", embed=embed, view=ComicView(self.session, self.latest_comic))

    @app_commands.command(name="xkcd", description="Displays XKCD comic")
    @app_commands.describe(subscription_setting="Subscribes or Unsubscribes the current channel from new XKCD comics.")
    async def xkcd(self, interaction: discord.Interaction, subscription_setting: Literal["subscribe", "unsubscribe"] = "none"):
        ''' Root XKCD command '''
        logger.info(f"{interaction.user.name} issued /xkcd {subscription_setting}, ({interaction.channel})")

        if subscription_setting == "subscribe":
            if interaction.channel_id not in self.subscribed_channels:
                self.subscribed_channels.add(interaction.channel_id)
                self.save_subscriptions()
                embed = await get_xkcd_embed(self.session)
                embed.add_field(name="Success!", value="This channel is now subscribed to new XKCD comics!\n\
                    Comics will be posted here within 15 minutes of being made public on xkcd.com.\n\
                    Here is the most recent comic:")
                await interaction.response.send_message(embed=embed, view=ComicView(self.session, self.latest_comic))
            else:
                await interaction.response.send_message(content="Channel already subscribed!", ephemeral=True)

        elif subscription_setting == "unsubscribe":
            if interaction.channel_id in self.subscribed_channels:
                self.subscribed_channels.remove(interaction.channel_id)
                self.save_subscriptions()
                await interaction.response.send_message(content="Channel unsubscribed from new XKCD comics!")
            else:
                await interaction.response.send_message(content="Channel already unsubscribed!", ephemeral=True)

        else:
            await interaction.response.send_message(embed=await get_xkcd_embed(self.session), view=ComicView(self.session, self.latest_comic))

    def cog_unload(self):
        self.check_for_new_comic.cancel()

async def setup(client: MiniSigma):
    global AVATAR_URL
    AVATAR_URL = client.user.display_avatar.url
    await client.add_cog(XKCD(client))