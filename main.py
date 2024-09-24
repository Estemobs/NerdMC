import discord
from discord.ext import commands
import json
import os
import subprocess
import threading
import asyncio
import traceback

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
async def send_to_minecraft(ctx, *, message):
    print(f"Commande appelée dans le channel {ctx.channel.name}")
    
    # Exécuter la commande pour envoyer le message à Minecraft
    command = ['sudo','tmux', 'send-keys', '-t', 'minecraft', f"say {message}",'C-j']
    print(f"Commande à exécuter : {' '.join(command)}")
    
    try:
        result = subprocess.run(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            capture_output=False,
            check=True
        )
        
        print(f"Message envoyé avec succès : {message}")
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'envoi du message : {e}")
        print("Erreur détaillée :")
        print(e.stderr)
    except Exception as e:
        print(f"Une erreur s'est produite : {e}")
        print("Erreur détaillée :")
        import traceback
        traceback.print_exc()


def run_bot():
    bot.run(config['token'])

if __name__ == "__main__":
    run_bot()


    