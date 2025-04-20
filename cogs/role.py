import discord
from discord import app_commands
from discord.ext import commands

import logging

logger = logging.getLogger("client.role")

class RoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role):
        super().__init__(label=role.name, style=discord.ButtonStyle.primary)
        self.role = role
        self.custom_id = f"rolebutton_{role.id}"

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        if self.role in member.roles:
            await member.remove_roles(self.role)
            await interaction.response.send_message(f"Removed {self.role.mention} role.", ephemeral=True)
        else:
            await member.add_roles(self.role)
            await interaction.response.send_message(f"Added {self.role.mention} role.", ephemeral=True)

class RoleCog(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        # Should probably be using db to store roles with buttons
        # but for now, we just add buttons for all roles in all guilds
        for guild in self.client.guilds:
            view = discord.ui.View(timeout=None)
            for role in guild.roles:
                view.add_item(RoleButton(role))
            self.client.add_view(view)

        logger.info("Role Cog is ready.")

    @app_commands.command(name="rolebutton", description="Creates a button for users to get a role")
    @app_commands.describe(role="The role that the button gives to users")
    @app_commands.guild_only()
    async def rolebutton(self, interaction: discord.Interaction, role: discord.Role):
        # Check if the interaction is in a guild (server) context
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.",
                ephemeral=True
            )
            return

        # We can now safely access the user as a member of the guild
        member: discord.Member = interaction.user
        
        # Check if the user has the required permissions
        if not member.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "You do not have permission to create role buttons.",
                ephemeral=True
            )
            return
        
        # Check if the role is higher than the bot's highest role
        if role >= interaction.guild.me.top_role:
            await interaction.response.send_message(
                "I cannot assign roles that are higher than or equal to my highest role.",
                ephemeral=True
            )
            return

        # Check if the role is higher than the user's highest role
        if role >= member.top_role:
            await interaction.response.send_message(
                "You cannot create a button for a role that is higher than your top role.",
                ephemeral=True
            )
            return

        # Create view with our button
        view = discord.ui.View(timeout=None)
        view.add_item(RoleButton(role))

        # Send the message with the button
        await interaction.response.send_message(
            f"Click the button to get the {role.mention} role:",
            view=view
        )

async def setup(client: commands.Bot):
    await client.add_cog(RoleCog(client))