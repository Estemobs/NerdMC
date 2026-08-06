import discord
from discord.ext import commands
import json
import os
import subprocess
import asyncio
import traceback
import re

config_path = os.environ.get('NERDMC_CONFIG', 'config.json')
with open(config_path, 'r') as f:
    config = json.load(f)

intents = discord.Intents.default()
intents.message_content = True
stop_reading = False

minecraft_log_path = config.get('minecraft_log_path', '/home/minecraft/logs/latest.log')
minecraft_tmux_session = config.get('minecraft_tmux_session', 'minecraft')
use_sudo = config.get('use_sudo', True)

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
    if hasattr(bot, 'minecraft_channel_id') and bot.minecraft_channel_id:
        await ctx.send("La commande est déjà activée.")
        return
    bot.minecraft_channel_id = ctx.channel.id
    await ctx.send("Commande active. Envoi actif des messages discord vers Minecraft...")
    await ctx.send("Envoi actif des messages Minecraft vers Discord...")
    
    global stop_reading
    if stop_reading:
        stop_reading = False
        
    # Capture les messages Minecraft
    cmd = ['sudo', 'tail', '-f', minecraft_log_path] if use_sudo else ['tail', '-f', minecraft_log_path]
    bot.minecraft_log_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        text=True
    )
    
    # Fonction pour lire les lignes du processus
    async def read_process():
        try:
            while not stop_reading:
                line = await asyncio.to_thread(bot.minecraft_log_process.stdout.readline)
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
  
@bot.command()
async def disable(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
        return
    
    # Arrêtez l'envoi de messages Discord vers Minecraft
    if hasattr(bot, 'minecraft_channel_id') and bot.minecraft_channel_id:
        bot.minecraft_channel_id = None
        
        # Fermez le processus qui lit les logs de Minecraft
        if hasattr(bot, 'minecraft_log_process') and bot.minecraft_log_process:
            print("Arrêt du processus de lecture des logs Minecraft...")
            try:
                bot.minecraft_log_process.terminate()
            except ProcessLookupError:
                pass
        
        # Arrêtez la lecture des messages Minecraft
        stop_reading = True
        
        # Attendre que la tâche se termine
        await asyncio.sleep(0.1)
        
        # Envoyez un message de confirmation
        await ctx.send("La commande a été désactivée. L'envoi des messages Minecraft vers Discord est maintenant désactivé et l'envoi de messages Discord vers Minecraft s'est arrêté.")
    else:
        await ctx.send("La commande n'était pas activée.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if hasattr(bot, 'minecraft_channel_id') and bot.minecraft_channel_id:
        if message.channel.id == bot.minecraft_channel_id:
            username = str(message.author)
            print(f"Traitement message du canal {message.channel.id} (comparaison avec {bot.minecraft_channel_id})")
            cmd = ['sudo', 'tmux', 'send-keys', '-t', minecraft_tmux_session, f"say {username}: {message.content}", 'C-j'] if use_sudo else ['tmux', 'send-keys', '-t', minecraft_tmux_session, f"say {username}: {message.content}", 'C-j']
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    cmd,
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