import re
import logging
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import utility.database as DB
import config
from bot import MiniSigma

def nick_without_iq(raw_nick: str) -> str:
        '''Removes iq score from the end of nickname strings'''
        nick_sans_iq: str = re.sub(r"\s*\([^)]*\)$", "", raw_nick)
        return nick_sans_iq

async def nick_update(member: discord.Member, iq_score: int) -> None:
        '''Update a member's nick with a new score'''
        try:
            current_nick = member.nick or member.name
        except AttributeError:
            current_nick = member.name
            
        nick_sans_iq = nick_without_iq(current_nick)
        new_nick = nick_sans_iq + (f" ({iq_score} IQ)")
        try:
            await member.edit(nick=new_nick)
        except discord.errors.Forbidden:
            print(f"Unable to update {nick_sans_iq}'s nick, new score is {iq_score}")

logger = logging.getLogger("client")

class Voting(commands.Cog):
    '''Cog that implements voting with reactions'''

    def __init__(self, client: MiniSigma):
        self.client = client
        self.db: DB.Database = client.db

    async def get_nick_or_name(self, interaction: discord.Interaction, id: int) -> str:
        try:
            member = interaction.guild.get_member(id) or await interaction.guild.fetch_member(id)
            return member.name
        except:
            try:
                user = await self.client.fetch_user(id)
                return user.name
            except:
                return "[Deleted User]"
    
    async def process_reaction(self, event: discord.RawReactionActionEvent) -> None:
        emojis = self.db.get_emojis(event.guild_id) or self.db.add_guild(event.guild_id)
        if str(event.emoji) not in emojis:
            return

        channel = self.client.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id) # API Call number 1, +150ms
        target: discord.User = message.author
        voter_id = event.user_id

        if target.id == voter_id:
            return

        count_change = 1 if event.event_type == "REACTION_ADD" else -1
        if str(event.emoji) == emojis[0]:
            new_user_score = self.db.upvote_user(target.id, count_change, voter_id)
            vote_type = "upvote"
        else:
            new_user_score = self.db.downvote_user(target.id, count_change, voter_id)
            vote_type = "downvote"
        self.db.update_username(target.id, target.name)

        await nick_update(target, new_user_score) # API Call number 2, +150ms
        # Total about 350ms after two API calls and database access
        log_string = f"{target.name} {event.event_type} {vote_type}: {message.guild.get_member(voter_id)} ({message.channel}), Score: {new_user_score}" 
        logger.info(log_string)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, RawReactionActionEvent: discord.RawReactionActionEvent):
        await self.process_reaction(RawReactionActionEvent)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, RawReactionActionEvent: discord.RawReactionActionEvent):
        await self.process_reaction(RawReactionActionEvent)

    async def user_sentiment(self, interaction: discord.Interaction, target: discord.Member) -> discord.Embed:
        '''Returns an embed with a list of target's fans or haters, based on context commmand'''
        target = interaction.user if target == None else target
    
        command = interaction.command.name
        if command == "fans":
            vote = "Upvotes:"
            db_list = self.db.fans(target.id, 256)
        else:
            vote = "Downvotes:"
            db_list = self.db.haters(target.id, 256)

        embed = discord.Embed(title=f"{target.nick or target.name}'s {command.capitalize()}:", color=config.EMBED_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)

        names = ""
        scores = ""

        for id, score in db_list:
            name = await self.get_nick_or_name(interaction, id)
            names += f"{name}\n"
            scores += f'{score}\n'

        embed.add_field(name="User:", value=names)
        embed.add_field(name=vote, value=scores)
        return embed

    @app_commands.command(name="fans", description="Displays the users who have upvoted you the most")
    @app_commands.describe(target="The server member you would like to check the fans of")
    async def fans(self, interaction: discord.Interaction, target: discord.Member = None):
        logger.info(f"{interaction.user.name} issued /fans {target}, ({interaction.channel})")
        embed = await self.user_sentiment(interaction, target)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="haters", description="Displays the users who have downvoted you the most")
    @app_commands.describe(target="The server member you would like to check the haters of")
    async def haters(self, interaction: discord.Interaction, target: discord.Member = None):
        logger.info(f"{interaction.user.name} issued /haters {target}, ({interaction.channel})")
        embed = await self.user_sentiment(interaction, target)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Displays top n scoring individuals")
    @app_commands.describe(num="Number of users to display; Defaults to 5")
    async def leaderboard(self, interact: discord.Interaction, num: int = 5):
        logger.info(f"{interact.user.name} issued /leaderboard {num}, ({interact.channel})")
        top = self.db.leaderboard(num)

        embed = discord.Embed(color=config.EMBED_COLOR)
        embed.set_author(name=f"{interact.guild.name} Leaderboard", icon_url=self.client.user.display_avatar.url)

        ranks: list[str] = []
        usernames: list[str] = []
        scores: list[str] = []

        for i in range(len(top)):
            user = top[i]
            id = user[0]
            display_name = await self.get_nick_or_name(interact, id)
            display_name = nick_without_iq(display_name)

            ranks.append(str(i+1))
            usernames.append(display_name)
            scores.append(str(self.db.get_iq(id)))

        embed.add_field(name="Rank", value="\n".join(ranks), inline=True)
        embed.add_field(name="Name", value="\n".join(usernames), inline=True)
        embed.add_field(name="Score", value="\n".join(scores), inline=True)
        await interact.response.send_message(embed=embed)

    @commands.command()
    async def manual_save(self, ctx: commands.Context):
        '''Gods least suboptimal nickname iteration'''
        tasklist = []
        users = self.db.list_users()

        for user in users:
            try:
                member = ctx.guild.get_member(user(0))
                iq = user[2] - user[3] + user[4]
                if member is not None:
                    print(f"Appending {type(member)}: {member}, {type(iq)}: iq")
                    tasklist.append(nick_update(member, iq))
            except:
                print(f"Couldn't fetch {user(1)}'s member object, skipping...")
        
        try:
            asyncio.gather(*tasklist)
        except Exception as e:
            print(f"An error occurred during batch update: {e}")
    
        await ctx.send("Saved!")

    @app_commands.command(name="userinfo", description="Provides statistics and info about a user")
    async def userinfo(self, interaction: discord.Interaction, target: discord.Member):
        logger.info(f"{interaction.user.name} issued /userinfo {target}, ({interaction.channel})")
        target = interaction.user if target == None else target

        embed = discord.Embed(color=config.EMBED_COLOR)
        embed.set_author(name=f"{target.nick or target.name}'s User Info:", icon_url=target.avatar.url)

        embed.add_field(name="Username:", value=target.name)
        embed.add_field(name="ID:", value=target.id)
        embed.add_field(name="Creation Date:", value=target.created_at)
        embed.add_field(name="MiniSigma Guilds:", value="\n".join([guild.name for guild in target.mutual_guilds]))
        embed.add_field(name="Highest Role:", value=target.top_role)

        user: tuple = self.db.get_user(target)
        embed.add_field(name="**MiniSigma Stats:**", value="")
        embed.add_field(name="IQ Score:", value=user[2] - user[3] + user[4])
        embed.add_field(name="Upvotes:", value=user[2])
        embed.add_field(name="Downvotes:", value=user[3])
        embed.add_field(name="Biggest Fan:", value=self.db.fans(target.id, 1))
        embed.add_field(name="Biggest Hater:", value=self.db.haters(target.id, 1))

        await interaction.response.send_message(content="**WORK IN PROGRESS, NOT DONE**",embed=embed)

    @app_commands.command(name="guild_onboarding", description="Initializes guild settings")
    async def guild_onboarding(self, interaction: discord.Interaction):
        self.db.add_guild(interaction.guild_id)
        emojis = self.db.get_emojis(interaction.guild_id)
        await interaction.response.send_message(f"Server settings initialized, upvote emoji: {emojis[0]}, downvote emoji: {emojis[1]}")

    @app_commands.command(name="set_upvote", description="Changes the upvote emoji for the guild")
    async def set_upvote(self, interaction: discord.Interaction, emoji: str):
        self.db.set_upvote(interaction.guild_id, emoji)
        await interaction.response.send_message(f"Guild upvote emoji set: {emoji}")
        logger.info(f"({interaction.guild.name}) Guild upvote emoji changed to {emoji} by {interaction.user.name}")
        
    @app_commands.command(name="set_downvote", description="Changes the downvote emoji for the guild")
    async def set_downvote(self, interaction: discord.Interaction, emoji: str):
        self.db.set_downvote(interaction.guild_id, emoji)
        await interaction.response.send_message(f"Guild downvote emoji set: {emoji}")
        logger.info(f"({interaction.guild.name}) Guild downvote emoji changed to {emoji} by {interaction.user.name}")

async def setup(client: MiniSigma):
    await client.add_cog(Voting(client))