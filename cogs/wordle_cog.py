import discord
from discord import app_commands
from discord.ext import commands
from dotenv import dotenv_values
from operator import itemgetter
import os
from pymongo import MongoClient
from re import sub
import traceback

from bson.objectid import ObjectId
from pymongo import ASCENDING
from pymongo import DESCENDING

config = dict(dotenv_values(".env"))


def isAdmin():
    def predicate(interaction: discord.Interaction):
        admins = eval(config["ADMINS"])
        return interaction.user.id in admins

    return app_commands.check(predicate)


class Wordle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        client = MongoClient("127.0.0.1:27017")
        self.db = client.wordlebot
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
        results = self.wordle_collection.find({"Mode": "score", "Server": interaction.guild.id})
        leaderboard = []
        for member in results:
            document = {}
            document["average"] = member["Total"] / member["Count"]
            document["Author"] = member["Author"]
            leaderboard.append(document)
        leaderboard = sorted(leaderboard, key=itemgetter("average"), reverse=True)
        for member in leaderboard:
            user = await interaction.guild.fetch_member(member["Author"])
            name = f"{user.display_name} ({user.name}#{user.discriminator})"
            average_score = member["average"]
            embed.add_field(name=name, value="{:.2f}".format(average_score), inline=False)
        return await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="stats",
        description="The stats for you (or another user) in this server",
    )
    async def stats(self, interaction: discord.Interaction, user: discord.User = None) -> None:
        if not user:
            user = interaction.user
        dailys = self.wordle_collection.find(
            {"Mode": "daily", "Server": interaction.guild.id, "Author": user.id}
        ).sort("Number", ASCENDING)
        total_guesses = 0
        times_played = 0
        current_streak = 0
        longest_streak = 0
        previous_wordle = 0
        for result in dailys:
            if current_streak == 0:
                previous_wordle = result["Number"] - 1
            total_guesses += 7 - result["Score"]
            times_played += 1
            if result["Number"] == previous_wordle + 1:
                current_streak += 1
            else:
                current_streak = 1
            if current_streak > longest_streak:
                longest_streak = current_streak
            previous_wordle = result["Number"]
        average_guesses = total_guesses / times_played
        embed = discord.Embed(title=f"{user.display_name}'s Stats!", color=interaction.user.color)
        embed.add_field(name="Average Attempts", value="{:.2f}".format(average_guesses))
        embed.add_field(name="Submitted Games", value=times_played)
        embed.add_field(name="Current Streak", value=current_streak)
        embed.add_field(name="Longest Streak", value=longest_streak)
        return await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="game-stats",
        description="The stats for a specific daily game in this server",
    )
    async def gamestats(self, interaction: discord.Interaction, game_number: int) -> None:
        guesses = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}
        cursor = self.wordle_collection.find({"Mode": "daily", "Number": game_number})
        total = 0
        for items in cursor:
            guess = 7 - items["Score"]
            if guess in guesses:
                guesses[guess] += 1
                total += 1
        if total == 0:
            return await interaction.response.send_message(
                f"No games submitted for game {game_number}"
            )
        for guess in guesses:
            guesses[guess] /= total
        guesses["X"] = guesses[7]
        guesses.pop(7)
        embed = discord.Embed(title=f"Stats for Wordle {game_number}", color=interaction.user.color)

        stat_string = ""
        for key in guesses:
            if key == "X":
                emoji = "🟨 "
            else:
                emoji = "🟩 "
            percent = guesses[key] * 100
            stat_string += (
                f"`{key}`: " + int(percent / 10) * emoji + "{:.2f}".format(percent) + "%\n"
            )

        embed.add_field(name=stat_string, value="\u200b")
        embed.add_field(name="Total Submitted", value=total, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="list", description="An admin command to list last 10 submissions to wordle"
    )
    @isAdmin()
    async def list10(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Wordle Submissions!", color=interaction.user.color)
        results = (
            self.wordle_collection.find({"Mode": "daily", "Server": interaction.guild.id})
            .sort("_id", DESCENDING)
            .limit(10)
        )
        for member in results:
            field = {
                "Author": "<@%s>" % member["Author"],
                "Number": member["Number"],
                "Score": member["Score"],
                "id": str(member["_id"]),
            }
            embed.add_field(name="Submission", value=field, inline=False)
        return await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="list-all", description="An admin command to list all submissions to wordle"
    )
    @isAdmin()
    async def listall(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Wordle Submissions!", color=interaction.user.color)
        results = self.wordle_collection.find(
            {"Mode": "daily", "Server": interaction.guild.id}
        ).sort("_id", DESCENDING)
        for member in results:
            field = {
                "Author": "<@%s>" % member["Author"],
                "Number": member["Number"],
                "Score": member["Score"],
                "id": str(member["_id"]),
            }
            embed.add_field(name="Submission", value=field, inline=False)
        return await interaction.response.send_message(embed=embed)

    @app_commands.command(name="delete", description="An admin command to delete an entry")
    @isAdmin()
    async def delete(self, interaction: discord.Interaction, objectid: str):
        deleted_document = self.wordle_collection.find_one_and_delete({"_id": ObjectId(objectid)})
        user = "<@" + str(deleted_document["Author"]) + ">"
        wordle_number = deleted_document["Number"]
        member = interaction.guild.get_member(int(deleted_document["Author"]))
        self.recalculate_helper(interaction, member)
        return await interaction.response.send_message(
            f"Deleted {user}'s Wordle number {wordle_number}"
        )

    @list10.error
    async def error(self, interaction: discord.Interaction, error):
        if isinstance(error, discord.app_commands.errors.CheckFailure):
            return await interaction.response.send_message(
                "You don't have the permissions to run this command"
            )

    @app_commands.command(
        name="recalculate",
        description="Recalculate the scores for a single user or everyone in the server",
    )
    async def recalculate(self, interaction: discord.Interaction, user: discord.Member = None):
        self.recalculate_helper(interaction, user)
        return await interaction.response.send_message("Recalculated!")

    def recalculate_helper(self, interaction, user=None):
        users = []
        if user:
            users.append(user.id)
        else:
            users = self.wordle_collection.distinct("Author", {"Mode": "daily", "Server": interaction.guild.id})
        total = 0
        count = 0
        for user in users:
            results = self.wordle_collection.find(
                {"Mode": "daily", "Author": user},
                {"Score": 1, "_id": 0},
            )
            for result in results:
                count += 1
                total += result["Score"]
            guilds = interaction.guild.get_member(user).mutual_guilds
            guild_ids = []
            for guild in guilds:
                guild_ids.append(guild.id)
            self.wordle_collection.find_one_and_update(
                {"Mode": "score", "Author": user},
                {"$set": {"Count": count, "Total": total, "Server": guild_ids}},
                upsert=True,
            )
        return

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
            await message.add_reaction("🇼")

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
                "Author": message.author.id,
            }
        )
        if exists != None:
            return None

        guilds = message.author.mutual_guilds
        guild_ids = []
        for guild in guilds:
            guild_ids.append(guild.id)

        return {
            "Mode": "daily",
            "Number": wordle_number,
            "Server": guild_ids,
            "Author": message.author.id,
            "Score": score,
            "Submission": submission,
            "Raw_Message": message.content,
        }


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Wordle(bot))
