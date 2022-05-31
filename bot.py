# bot.py
import os
import discord
import logging
import asyncio
from discord.ext import commands
from dotenv import dotenv_values

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

config = dict(dotenv_values(".env"))
TOKEN = config["DISCORD_TOKEN"]
PREFIX = config["PREFIX"]


class WordleBot(commands.Bot):
    def __init__(self, *, intents: discord.Intents, command_prefix):
        super().__init__(intents=intents, command_prefix=command_prefix)

    async def setup_hook(self):
        await bot.load_extension("cogs.wordle_cog")


intents = discord.Intents.all()
intents.members = True

bot = WordleBot(intents=intents, command_prefix=PREFIX)


@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))
    await bot.change_presence(activity=discord.Activity(name="Wordling", type=5))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You're missing permissions to do that :neutral_face:", delete_after=5
        )


if __name__ == "__main__":
    asyncio.run(bot.start(TOKEN))
