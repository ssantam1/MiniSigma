import discord

def create_message_embed(message: discord.Message, color) -> discord.Embed:
    '''Returns an embed for displaying a message'''
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