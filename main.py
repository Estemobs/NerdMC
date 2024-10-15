import discord
from discord.ext import commands
import json
import os
import subprocess
import threading
import asyncio
import traceback
import re 

# Load configuration from JSON file
with open('config.json', 'r') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=config['command_prefix'], intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    game = discord.Game(name="mc.forezaaaa.fr")
    await bot.change_presence(activity=game)

@bot.command()
async def enable(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
        return
    bot.minecraft_channel_id = ctx.channel.id
    await ctx.send("Commande active. Envoi actif des messages discord vers Minecraft...")
    await ctx.send("Envoi actif des messages Minecraft vers Discord...")
    
    # Capture les messages Minecraft
    process = subprocess.Popen(
        ['sudo', 'tail', '-f', '/home/minecraft/logs/latest.log'],
        stdout=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        text=True
    )
    
    # Fonction pour lire les lignes du processus
    async def read_process():
        try:
            while True:
                line = await asyncio.to_thread(process.stdout.readline)
                if not line:
                    break
                
                match = re.search(r'<([^>]+)> (.+)', line.strip())
                if match:
                    username, message = match.groups()
                    await ctx.send(f"{username}: {message}")
        
        except Exception as e:
            print(f"Erreur dans read_process: {e}")
        
    # Lancez la lecture des messages Minecraft dans un thread
    asyncio.create_task(read_process())

    # Variable globale pour savoir si la commande est active
    bot.rewrite_active = True
    

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if hasattr(bot, 'rewrite_active') and bot.rewrite_active:
        print(f"Traitement message du canal {message.channel.id} (comparaison avec {bot.minecraft_channel_id})")
        username = str(message.author)
        command = ['sudo', 'tmux', 'send-keys', '-t', 'minecraft', f"say {username}: {message.content}", 'C-j']
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
            print(f"Message envoyé avec succès dans Minecraft : {message.content}")
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'envoi du message dans Minecraft : {e}")
            print("Erreur détaillée :")
            print(e.stderr)
        except Exception as e:
            print(f"Une erreur s'est produite : {e}")
            print("Erreur détaillée :")
            traceback.print_exc()
    
    await bot.process_commands(message)

        

def run_bot():
    bot.run(config['token'])

if __name__ == "__main__":
    run_bot()