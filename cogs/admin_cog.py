import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
import traceback

config = dict(dotenv_values(".env"))


def isAdmin():
    def predicate(interaction: discord.Interaction):
        admins = eval(config["ADMINS"])
        return interaction.user.id in admins

    return app_commands.check(predicate)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Registered admin cog")

    @app_commands.command(
        name="reset-role",
        description="Remove a role from everyone in the server",
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if (interaction.user.guild_permissions == discord.Permissions(manage_roles=True)):
            await interaction.response.defer()
            members = role.members
            skipped_members = []
            for member in members:
                try:
                    await member.remove_roles(role)
                except:
                    skipped_members.append(member.mention)
                    traceback.print_exc()
            response_message = ""
            if len(skipped_members) > 0:
                response_message = (
                    f"Skipped the following members: {', '.join(skipped_members)}"
                )
            else:
                response_message = ("Done!")
            return await interaction.followup.send(response_message, ephemeral=True)
        else:
            return await interaction.response.send_message("You don't have permission to do that!", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
