import random
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp

from bot import MiniSigma
from enum import Enum
import PIL
import io
import utility.database as DB

class Rarity(Enum):
    COMMON = ('Common', discord.Colour.greyple())
    UNCOMMON = ('Uncommon', discord.Colour.green())
    RARE = ('Rare', discord.Colour.blue())
    LEGENDARY = ('Legendary', discord.Colour.purple())

    def __init__(self, label, color):
        self.label = label
        self.color = color

class Gacha(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db: DB.Database = client.db

    def get_rarity(self, id: int) -> Rarity:
        # Use the last two digits of the user's ID to determine the rarity
        level = id % 100
        if level < 60:
            return Rarity.COMMON
        elif level < 90:
            return Rarity.UNCOMMON
        elif level < 98:
            return Rarity.RARE
        else:
            return Rarity.LEGENDARY
        
    def count_rarities(self, ids: list[int]) -> dict:
        '''Count the number of characters of each rarity in a list of IDs'''
        rarities = {
            'Common': 0,
            'Uncommon': 0,
            'Rare': 0,
            'Legendary': 0
        }
        for id in ids:
            rarity = self.get_rarity(id)
            rarities[rarity.label] += 1
        return rarities
    
    @commands.command()
    async def count_all_rarities(self, ctx: commands.Context):
        '''Count the number of characters of each rarity for all users'''
        users = self.db.list_users() # Copilot thinks that this should be called get_all_users()
        rarities = self.count_rarities([user[0] for user in users])
        rarity_counts = '\n'.join([f'{rarity}: {count}' for rarity, count in rarities.items()])
        await ctx.send(f'All rarities:\n{rarity_counts}')

    async def get_manual_url(self, user_id: int) -> str:
        user = await self.client.fetch_user(user_id)
        avatar_url = user.display_avatar.url
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as response:
                avatar_bytes = await response.read()

        avatar_file = io.BytesIO(avatar_bytes)

        avatar_image = PIL.Image.open(avatar_file)
        avatar_image = avatar_image.resize((128, 128))
        avatar_file = io.BytesIO()
        avatar_image.save(avatar_file, format='PNG')
        avatar_file.seek(0)

        channel = self.client.get_channel(1183931783742492772) # Replace with the ID of the channel
        message = await channel.send(file=discord.File(avatar_file, 'avatar.png'))
        return message.attachments[0].url

    @app_commands.command(name="pull", description="Pull a character from the gacha")
    async def pull(self, interaction: discord.Interaction):
        pulled_card: tuple[int, str, int, int, int] = self.db.pull()
        card_id, card_name, card_atk, card_def, _ = pulled_card
        rarity = self.get_rarity(card_id)

        # API call to get avatar URL (Maybe start storing avatar ID in db to avoid API call?)
        user_on_card = await self.client.fetch_user(card_id)
        card_image = str(user_on_card.display_avatar.with_size(256))

        card_embed = discord.Embed(title=f"__**{card_name}**__", color=rarity.color)
        card_embed.set_author(name=f'[{rarity.label.upper()}]')

        card_embed.add_field(name='ATK', value=card_atk, inline=True)
        card_embed.add_field(name='DEF', value=card_def, inline=True)
        card_embed.set_thumbnail(url=card_image)

        await interaction.response.send_message(embed=card_embed)

async def setup(client: MiniSigma):
    await client.add_cog(Gacha(client))