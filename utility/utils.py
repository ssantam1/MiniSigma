import re
import logging
import discord
from utility.config import POINTS_NAME

logger = logging.getLogger("client.utils")

def create_message_embed(message: discord.Message, color: discord.Color) -> discord.Embed:
    """Creates a Discord embed to display an existing message object.

    The embed includes the message content, author, source link, and attachment if present.

    Args:
        message: The message to create an embed from
        color: The color to use for the embed

    Returns:
        A Discord embed containing the formatted message
    """
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

def strip_score(nick: str) -> str:
    """Removes the trailing score and parentheses from a nickname string.

    Args:
        nick: The nickname string that may contain a trailing score in parentheses

    Returns:
        The nickname with any trailing parenthetical score removed
    """
    return re.sub(r"\s*\([^)]*\)$", "", nick)

async def nick_update(member: discord.Member, score: int) -> None:
    """Updates a member's nickname with their new score.

    If the member's nickname already contains a score, it is replaced.
    If the member's nickname does not contain a score, one is appended.
    If the member's nickname is too long, the score is not appended.

    Args:
        member: The member whose nickname should be updated
        score: The new score to append to the member's nickname

    Raises:
        discord.errors.Forbidden: When bot lacks permission to change nicknames
        discord.errors.HTTPException: When the new nickname is too long
    """
    try:
        current_nick: str = member.nick or member.name
    except AttributeError:
        current_nick = member.name
        
    nick_sans_iq: str = strip_score(current_nick)
    new_nick: str = f"{nick_sans_iq} ({score} {POINTS_NAME})"

    try:
        await member.edit(nick=new_nick)
        logger.info(f"Successfully updated {nick_sans_iq}'s nickname to: {new_nick}")
    except discord.errors.Forbidden:
        logger.warning(
            f"Permission denied: Unable to update {nick_sans_iq}'s nickname. "
            f"New score is {score}"
        )
    except discord.errors.HTTPException:
        logger.warning(
            f"Nickname too long: Failed to update {nick_sans_iq}'s nickname. "
            f"New score is {score}"
        )