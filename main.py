import discord
from discord.ext import commands
import json
import os
import subprocess
import asyncio
import traceback
import re

config_path = os.environ.get('NERDMC_CONFIG', 'config.json')
REQUIRED_SETTINGS = ('token', 'command_prefix')


def load_config(path):
    if not os.path.exists(path):
        raise SystemExit(
            f"Configuration introuvable : {path}. Copiez config.json.example vers config.json."
        )
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Configuration invalide ({path}) : {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Configuration invalide ({path}) : un objet JSON est attendu.")
    missing = [key for key in REQUIRED_SETTINGS if not data.get(key)]
    if missing:
        raise SystemExit(f"Configuration invalide ({path}) : champs manquants {', '.join(missing)}.")
    if not isinstance(data['command_prefix'], str) or not data['command_prefix'].strip():
        raise SystemExit(f"Configuration invalide ({path}) : command_prefix doit être une chaîne non vide.")
    return data


config = load_config(config_path)

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
        
        # Arrêtez la lecture des messages Minecraft
        global stop_reading
        stop_reading = True
        
        # Fermez le processus qui lit les logs de Minecraft
        if hasattr(bot, 'minecraft_log_process') and bot.minecraft_log_process:
            print("Arrêt du processus de lecture des logs Minecraft...")
            bot.minecraft_log_process.terminate()
            # Wait for the process to terminate (optional, but we can wait a bit)
            try:
                # Wait for the process to terminate with a timeout
                await asyncio.wait_for(asyncio.to_thread(bot.minecraft_log_process.wait), timeout=5.0)
            except asyncio.TimeoutError:
                print("Timeout waiting for process to terminate, killing it.")
                bot.minecraft_log_process.kill()
            except Exception as e:
                print(f"Error while waiting for process to terminate: {e}")
        
        # Envoyez un message de confirmation
        await ctx.send("La commande a été désactivée. L'envoi des messages Minecraft vers Discord est maintenant désactivé et l'envoi de messages Discord vers Minecraft s'est arrêté.")
    else:
        await ctx.send("La commande n'était pas activée.")

@bot.command()
async def status(ctx):
    channel_id = getattr(bot, 'minecraft_channel_id', None)
    process = getattr(bot, 'minecraft_log_process', None)
    process_running = process is not None and process.poll() is None
    embed = discord.Embed(
        title="NerdMC — état",
        color=discord.Color.green() if channel_id else discord.Color.orange(),
    )
    embed.add_field(
        name="Relais Discord → Minecraft",
        value=f"<#{channel_id}>" if channel_id else "désactivé",
        inline=False,
    )
    embed.add_field(name="Lecture des logs", value="active" if process_running else "inactive", inline=True)
    embed.add_field(name="Fichier de log", value=f"`{minecraft_log_path}`", inline=True)
    embed.add_field(name="Session tmux", value=f"`{minecraft_tmux_session}`", inline=True)
    embed.add_field(name="sudo", value="oui" if use_sudo else "non", inline=True)
    await ctx.send(embed=embed)


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
                subprocess.run(
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