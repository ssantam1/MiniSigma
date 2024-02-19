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

class ListPaginator(discord.ui.View):
    def __init__(self, embed, data):
        super().__init__(timeout=None)
        self.embed: discord.Embed = embed
        self.data = data
        self.current_page = 1
        self.max_page = len(data)/5
        self.update_buttons()

    def update_buttons(self):
        '''Updates the buttons to reflect the current page'''
        if self.current_page <= 1:
            self.first_button.disabled = True
            self.prev_button.disabled = True
        else:
            self.first_button.disabled = False
            self.prev_button.disabled = False

        if self.current_page >= self.max_page:
            self.next_button.disabled = True
            self.last_button.disabled = True
        else:
            self.next_button.disabled = False
            self.last_button.disabled = False

    def update_embed(self):
        '''Updates the embed with the current page of data'''
        page = self.current_page - 1
        start = int(page * 5)
        end = int(start + 5)
        page_data = self.data[start:end]
        self.update_buttons()

        self.embed.clear_fields()
        for (m_id, c_id, g_id, score) in page_data:
            message_url = f"https://discord.com/channels/{g_id}/{c_id}/{m_id}"
            channel_link = f"<#{c_id}>"
            self.embed.add_field(name=f"Score: {score} {channel_link}", value=f"[Jump to message]({message_url})", inline=False)
        return self.embed

    async def send(self, interaction: discord.Interaction):
        self.message = await interaction.response.send_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="", emoji="⏮️", row=0)
    async def first_button(self, interaction: discord.Interaction, _: discord.Button):
        '''Go to the first page of the list'''
        self.current_page = 1
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="", emoji="⬅️", row=0)
    async def prev_button(self, interaction: discord.Interaction, _: discord.Button):
        '''Go to the previous page of the list'''
        self.current_page -= 1
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="", emoji="➡️", row=0)
    async def next_button(self, interaction: discord.Interaction, _: discord.Button):
        '''Go to the next page of the list'''
        self.current_page += 1
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

    @discord.ui.button(label="", emoji="⏭️", row=0)
    async def last_button(self, interaction: discord.Interaction, _: discord.Button):
        '''Go to the last page of the list'''
        self.current_page = self.max_page
        await interaction.response.edit_message(embed=self.update_embed(), view=self)

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
        emojis = self.db.get_emojis(event.guild_id)
        if str(event.emoji) not in emojis:
            return

        channel = self.client.get_channel(event.channel_id)
        message = await channel.fetch_message(event.message_id)

        target: discord.User = message.author
        voter = message.guild.get_member(event.user_id)

        if target.id == voter.id:
            return

        count_change = 1 if event.event_type == "REACTION_ADD" else -1
        if str(event.emoji) == emojis[0]:
            new_user_score = self.db.upvote_user(target.id, count_change, voter.id)
            vote_type = "upvote"
        else:
            new_user_score = self.db.downvote_user(target.id, count_change, voter.id)
            vote_type = "downvote"
        self.db.update_username(target.id, target.name)
        self.db.update_username(voter.id, voter.name)

        await nick_update(target, new_user_score)
        logger.info(f"{target} {event.event_type} {vote_type}: {voter} ({message.channel}), Score: {new_user_score}")

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
            db_list = self.db.fans(target.id, 5)
        else:
            vote = "Downvotes:"
            db_list = self.db.haters(target.id, 5)

        embed = discord.Embed(title=f"{target.nick or target.name}'s {command.capitalize()}:", color=config.EMBED_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)

        names = ""
        scores = ""

        for (id, name, score) in db_list:
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

    @app_commands.command(name="bestof", description="Displays a list of the top 5 posts by a user")
    async def bestof(self, interaction: discord.Interaction, target: discord.Member = None):
        '''Displays a list of the top 5 posts by a user, or the user who issued the command if no target is specified'''
        logger.info(f"{interaction.user.name} issued /bestof {target}, ({interaction.channel})")
        target = interaction.user if target == None else target

        embed = embed = discord.Embed(title=f"{target.nick or target.name}'s Best Posts:", color=config.EMBED_COLOR)
        embed.set_thumbnail(url=target.display_avatar.url)

        view = ListPaginator(embed, self.db.best_of(target.id))
        await view.send(interaction)

    @app_commands.command(name="top_messages", description="Top 5 most popular messages registered by the bot")
    @app_commands.describe(guild_only="Set to true to only display messages from the current server")
    async def top_messages(self, interaction: discord.Interaction, guild_only: bool = False):
        '''Displays the top 5 most popular messages registered by the bot, or the top 5 from the current server if guild_only is set to True'''
        logger.info(f"{interaction.user.name} issued /top_messages, ({interaction.channel})")

        top_messages: list[tuple[str, int, int, int, int]] = self.db.top_messages(interaction.guild_id if guild_only else None)

        embed = discord.Embed(title="Top Messages:", color=config.EMBED_COLOR)
        embed.set_thumbnail(url=self.client.user.display_avatar.url)

        for (author_id, m_id, c_id, g_id, score) in top_messages:
            author_name: str = await self.get_nick_or_name(interaction, author_id)
            message_url = f"https://discord.com/channels/{g_id}/{c_id}/{m_id}"
            embed.add_field(name=f"Score: {score}", value=f"{author_name}\n[Jump to message]({message_url})", inline=False)

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
            display_name = user[1]

            ranks.append(str(i+1))
            usernames.append(display_name)
            scores.append(str(self.db.get_iq(user[0])))

        embed.add_field(name="Rank", value="\n".join(ranks), inline=True)
        embed.add_field(name="Name", value="\n".join(usernames), inline=True)
        embed.add_field(name="Score", value="\n".join(scores), inline=True)
        await interact.response.send_message(embed=embed)

    @commands.command()
    async def manual_save(self, ctx: commands.Context):
        tasklist = []
        users = self.db.list_users()

        for user in users:
            try:
                member = ctx.guild.get_member(user[0])
                iq = user[2] - user[3] + user[4]
                if member is not None:
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

        user: tuple = self.db.get_user(target.id)
        embed.add_field(name="**MiniSigma Stats:**", value="")
        embed.add_field(name="IQ Score:", value=user[2] - user[3] + user[4])
        embed.add_field(name="Upvotes:", value=user[2])
        embed.add_field(name="Downvotes:", value=user[3])
        embed.add_field(name="Biggest Fan:", value=self.db.fans(target.id, 1))
        embed.add_field(name="Biggest Hater:", value=self.db.haters(target.id, 1))

        await interaction.response.send_message(content="**WORK IN PROGRESS, NOT DONE**",embed=embed)

    @app_commands.command(name="guild_onboarding", description="Initializes guild settings")
    async def guild_onboarding(self, interaction: discord.Interaction):
        '''Initializes guild settings in the database, including upvote and downvote emojis. Does not overwrite existing settings'''
        self.db.add_guild(interaction.guild_id)
        emojis = self.db.get_emojis(interaction.guild_id)
        
        await interaction.response.send_message(f"Server settings initialized, upvote emoji: {emojis[0]}, downvote emoji: {emojis[1]}")
        logger.info(f"({interaction.guild.name}) Guild emojis initialized: Upvote - {emojis[0]}, Downvote - {emojis[1]} by {interaction.user.name}")

    @app_commands.command(name="set_emojis", description="Changes the upvote and downvote emojis for the guild")
    async def set_emojis(self, interaction: discord.Interaction, upvote_emoji: str, downvote_emoji: str):
        '''Changes the upvote and downvote emojis for the guild'''
        self.db.set_upvote(interaction.guild_id, upvote_emoji)
        self.db.set_downvote(interaction.guild_id, downvote_emoji)

        await interaction.response.send_message(f"Guild emojis set: Upvote - {upvote_emoji}, Downvote - {downvote_emoji}")
        logger.info(f"({interaction.guild.name}) Guild emojis changed: Upvote - {upvote_emoji}, Downvote - {downvote_emoji} by {interaction.user.name}")

async def setup(client: MiniSigma):
    await client.add_cog(Voting(client))