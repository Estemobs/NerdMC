import discord
from discord.ext import commands
import json
import os

# Load configuration from JSON file
with open('config.json', 'r') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=config['command_prefix'], intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

def run_bot():
    bot.run(config['token'])

if __name__ == "__main__":
    run_bot()