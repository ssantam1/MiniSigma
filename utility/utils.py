import re
import logging
import discord
from utility.config import POINTS_NAME

logger = logging.getLogger("client.utils")

def create_message_embed(message: discord.Message, color) -> discord.Embed:
    '''Returns an embed for displaying another user's message'''
    embed = discord.Embed(
        description=message.content,
        color=color
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.display_avatar.url
    )
    embed.add_field(
        name="Source",
        value=f"[Jump to message]({message.jump_url})",
        inline=False
    )

    if message.attachments:
        attachment = message.attachments[0]
        if attachment.content_type.startswith("image"):
            embed.set_image(url=attachment.url)
        else:
            embed.add_field(
                name="Attachment",
                value=f"[{attachment.filename}]({attachment.url})",
                inline=False
            )

    embed.set_footer(text=str(message.id))

    return embed

async def nick_update(member: discord.Member, score: int) -> None:
    '''Updates the member's nickname with a new score'''
    try:
        current_nick = member.nick or member.name
    except AttributeError:
        current_nick = member.name
        
    nick_sans_iq: str = re.sub(r"\s*\([^)]*\)$", "", current_nick)
    new_nick = nick_sans_iq + (f" ({score} {POINTS_NAME})")

    try:
        await member.edit(nick=new_nick)
    except discord.errors.Forbidden:
        logger.warning(f"Unable to update {nick_sans_iq}'s nick, new score is {score}")
    except discord.errors.HTTPException:
        logger.error(f"HTTPException updating {nick_sans_iq}'s nick, new score is {score}")