import os
import discord
import traceback
from re import sub
from pymongo import DESCENDING
from pymongo import MongoClient
from discord import app_commands
from discord.ext import commands


class Wordle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        client = MongoClient("127.0.0.1:27017")
        self.db = client.homiebot
        self.wordle_collection = self.db["wordle"]
        print("Registered wordle cog")

    @commands.command(name="sync")
    async def sync(self, ctx: commands.Context) -> None:
        try:
            guild = ctx.guild
            ctx.bot.tree.copy_global_to(guild=guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            await ctx.send("Synced!")
        except:
            traceback.print_exc()

    @app_commands.command(
        name="leaderboard",
        description="The leaderboard for wordle scores (from 0 to 6) in this server",
    )
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(title="Wordle Leaderboard!", color=interaction.user.color)
        results = self.wordle_collection.find(
            {"Mode": "score", "Server": interaction.guild.id}
        ).sort("Total", DESCENDING)
        for member in results:
            user = await interaction.guild.fetch_member(member["Author"])
            name = f"{user.display_name} ({user.name}#{user.discriminator})"
            average_score = member["Total"] / member["Count"]
            embed.add_field(name=name, value=average_score, inline=False)
        return await interaction.response.send_message(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        content = os.linesep.join([s for s in message.content.splitlines() if s])
        content_lines = content.split("\n")
        if content_lines[0].startswith("Wordle"):
            document = self.analysis(message, content_lines)
            if document == None:
                return await message.channel.send(
                    "You have already submitted a wordle entry today. Please try again tomorrow"
                )
            self.wordle_collection.insert_one(document)
            self.wordle_collection.find_one_and_update(
                {"Mode": "score", "Server": document["Server"], "Author": document["Author"]},
                {"$inc": {"Count": 1, "Total": document["Score"]}},
                upsert=True,
            )

    def analysis(self, message, content_lines):
        attempts = len(content_lines[1:])
        wordle_number = int(content_lines[0].split(" ")[1])
        success = False
        if attempts == 6:
            if content_lines[-1] == "🟩🟩🟩🟩🟩" or content_lines[-1] == "🟧🟧🟧🟧🟧":
                success = True
        else:
            success = True
        if not success:
            attempts = 7
        score = 7 - attempts  # 1st try 6pts, 2nd 5pts, etc, did not get it 0pts

        submission = ",".join(content_lines[1:])
        # correct letter and position
        submission = sub("🟩", "*", submission)
        submission = sub("🟧", "*", submission)

        # correct letter incorrect position
        submission = sub("🟨", "/", submission)
        submission = sub("🟦", "/", submission)

        # incorrect
        submission = sub("⬛", "X", submission)
        submission = sub("⬜", "X", submission)

        exists = self.wordle_collection.find_one(
            {
                "Mode": "daily",
                "Number": wordle_number,
                "Server": message.guild.id,
                "Author": message.author.id,
            }
        )
        if exists != None:
            return None

        return {
            "Mode": "daily",
            "Number": wordle_number,
            "Server": message.guild.id,
            "Author": message.author.id,
            "Score": score,
            "Submission": submission,
        }


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Wordle(bot))
