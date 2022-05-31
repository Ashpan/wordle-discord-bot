# bot.py
import os, discord, datetime, sys, asyncio, logging
from discord.ext import commands
from dotenv import load_dotenv

logger = logging.getLogger("discord")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.getenv("PREFIX")
intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or(PREFIX),
    intents=intents,
    chunk_guilds_at_startup=True,
    message_commands=True,
)

@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))
    await bot.change_presence(
        activity=discord.Activity(name="Wordling", type=5)
    )


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "You're missing permissions to do that :neutral_face:", delete_after=5
        )


bot.load_extension("cogs.wordle_cog")
bot.run(TOKEN)
