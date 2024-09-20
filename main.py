import discord
from discord.ext import commands
import json
import os
import subprocess
import threading

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
async def minecraft_logs(ctx):
    await ctx.send("Activation des logs Minecraft...")
    
    async def log_to_discord():
        while True:
            try:
                process = subprocess.Popen(['tmux', 'capture-pane', '-S-', '-P', '-f', 'cat'],
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                output, error = process.communicate()
                
                if error:
                    print(f"Erreur lors de la capture de la console Minecraft : {error}")
                    continue
                
                lines = output.decode().split('\n')
                for line in lines:
                    if line.strip():  # Ignore les lignes vides
                        await ctx.send(line.strip())
            
            except Exception as e:
                print(f"Erreur lors de la lecture des logs Minecraft : {e}")

    thread = threading.Thread(target=log_to_discord)
    thread.daemon = True
    thread.start()

@bot.command()
async def enable_minecraft_channel(ctx):
    await ctx.send("Activation du canal Minecraft...")
    global minecraft_channel
    minecraft_channel = ctx.channel.id
    
    async def log_to_discord():
        while True:
            try:
                process = subprocess.Popen(['tmux', 'capture-pane', '-S-', '-P', '-f', 'cat'],
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE)
                output, error = process.communicate()
                
                if error:
                    print(f"Erreur lors de la capture de la console Minecraft : {error}")
                    continue
                
                lines = output.decode().split('\n')
                for line in lines:
                    if line.strip():  # Ignore les lignes vides
                        player_name = line.split('|')[1]
                        message = line.split('|')[2].strip()
                        formatted_message = f"[D] /say {player_name} {message}"
                        await ctx.send(formatted_message)
            
            except Exception as e:
                print(f"Erreur lors de la lecture des logs Minecraft : {e}")

    thread = threading.Thread(target=log_to_discord)
    thread.daemon = True
    thread.start()

@bot.command()
async def disable_minecraft_channel(ctx):
    await ctx.send("Désactivation du canal Minecraft...")
    global minecraft_channel
    minecraft_channel = None
    await ctx.send("Canal Minecraft désactivé.")
    
    # Arrêter le thread en cours s'il existe
    if hasattr(ctx.bot, 'log_thread'):
        ctx.bot.log_thread.join(timeout=5)
        delattr(ctx.bot, 'log_thread')



def run_bot():
    bot.run(config['token'])

if __name__ == "__main__":
    run_bot()


    