import random
import discord
from discord import app_commands
from discord.ext import commands

from bot import MiniSigma
from enum import Enum
import utility.database as DB

class Rarity(Enum):
    COMMON = 'Common'
    UNCOMMON = 'Uncommon'
    RARE = 'Rare'
    LEGENDARY = 'Legendary'

class Gacha(commands.Cog):
    def __init__(self, client: MiniSigma):
        self.client = client
        self.db: DB.Database = client.db

    def get_rarity(self, id: int) -> str:
        # Use the last two digits of the user's ID to determine the rarity
        level = id % 100
        if level < 60:
            return 'Common'
        elif level < 90:
            return 'Uncommon'
        elif level < 98:
            return 'Rare'
        else:
            return 'Legendary'
        
    def get_color(self, rarity: str) -> discord.Colour:
        '''Get the color for a rarity'''
        colour = {
            'Common': discord.Colour.greyple(),
            'Uncommon': discord.Colour.green(),
            'Rare': discord.Colour.blue(),
            'Legendary': discord.Colour.purple()
        }
        return colour[rarity]
        
    def count_rarities(self, ids: list[int]) -> dict:
        '''Count the number of characters of each rarity in a list of IDs'''
        rarities = {
            'Common': 0,
            'Uncommon': 0,
            'Rare': 0,
            'Legendary': 0
        }
        for id in ids:
            rarity_name = self.get_rarity(id)
            if rarity_name not in rarities:
                rarities[rarity_name] = 0
            rarities[rarity_name] += 1
        return rarities
    
    @commands.command()
    async def count_all_rarities(self, ctx: commands.Context):
        '''Count the number of characters of each rarity for all users'''
        users = self.db.list_users() # Copilot thinks that this should be called get_all_users()
        rarities = self.count_rarities([user[0] for user in users])
        rarity_counts = '\n'.join([f'{rarity}: {count}' for rarity, count in rarities.items()])
        await ctx.send(f'All rarities:\n{rarity_counts}')

    @app_commands.command(name="pull", description="Pull a character from the gacha")
    async def pull(self, interaction: discord.Interaction):
        pulled_card: tuple[int, str, int, int, int] = self.db.pull()
        card_id, card_name, card_atk, card_def, _ = pulled_card
        rarity = self.get_rarity(card_id)

        # API call to get avatar URL (Maybe start storing avatar ID in db to avoid API call?)
        user_on_card = await self.client.fetch_user(card_id)
        card_image = str(user_on_card.display_avatar.url)
        card_image = card_image.replace("?size=1024", "?size=128")

        card_embed = discord.Embed(title=f'{rarity} Character', url="https://cdn.discordapp.com/", color=self.get_color(rarity))
        card_embed.add_field(name='Name', value=card_name, inline=False)
        card_embed.add_field(name='ATK', value=card_atk, inline=True)
        card_embed.add_field(name='DEF', value=card_def, inline=True)
        card_embed.set_image(url=card_image)
        await interaction.response.send_message(embed=card_embed)

async def setup(client: MiniSigma):
    await client.add_cog(Gacha(client))