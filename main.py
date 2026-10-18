import discord
from discord.ext import commands
import json
import os
import subprocess
import asyncio
import traceback
import re
import sys

config_path = os.environ.get('NERDMC_CONFIG', 'config.json')

def load_config():
    """Load and validate configuration"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"ERREUR: Fichier de configuration '{config_path}' introuvable.")
        print("Veuillez copier config.json.example vers config.json et le remplir.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERREUR: Le fichier de configuration '{config_path}' contient un JSON invalide: {e}")
        sys.exit(1)
    
    # Validate required fields
    required_fields = ['token', 'command_prefix']
    for field in required_fields:
        if field not in config or not config[field]:
            print(f"ERREUR: Champ requis '{field}' manquant ou vide dans la configuration.")
            sys.exit(1)
    
    # Set defaults for optional fields
    config.setdefault('minecraft_log_path', '/home/minecraft/logs/latest.log')
    config.setdefault('minecraft_tmux_session', 'minecraft')
    config.setdefault('use_sudo', True)
    
    return config

config = load_config()

intents = discord.Intents.default()
intents.message_content = True
stop_reading = False

minecraft_log_path = config['minecraft_log_path']
minecraft_tmux_session = config['minecraft_tmux_session']
use_sudo = config['use_sudo']

bot = commands.Bot(command_prefix=config['command_prefix'], intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} a été connecté à Discord !')
    game = discord.Game(name="mc.forezaaaa.fr")
    await bot.change_presence(activity=game)
    
    # Log configuration info (without sensitive data)
    print(f"Configuration chargée:")
    print(f"  - Préfixe de commande: {config['command_prefix']}")
    print(f"  - Chemin du log Minecraft: {minecraft_log_path}")
    print(f"  - Session tmux Minecraft: {minecraft_tmux_session}")
    print(f"  - Utilisation de sudo: {use_sudo}")

@bot.command()
async def status(ctx):
    """Affiche l'état actuel du bot"""
    embed = discord.Embed(title="État du bot NerdMC", color=0x00ff00 if hasattr(bot, 'minecraft_channel_id') and bot.minecraft_channel_id else 0xff0000)
    
    # Minecraft channel status
    if hasattr(bot, 'minecraft_channel_id') and bot.minecraft_channel_id:
        channel = bot.get_channel(bot.minecraft_channel_id)
        channel_name = channel.name if channel else f"ID: {bot.minecraft_channel_id}"
        embed.add_field(name="Canal Minecraft", value=f"Actif ({channel_name})", inline=False)
    else:
        embed.add_field(name="Canal Minecraft", value="Inactif", inline=False)
    
    # Log reading status
    if hasattr(bot, 'read_task') and bot.read_task and not bot.read_task.done():
        embed.add_field(name="Lecture des logs", value="Active", inline=False)
    else:
        embed.add_field(name="Lecture des logs", value="Inactif", inline=False)
    
    # Process status
    if hasattr(bot, 'minecraft_log_process') and bot.minecraft_log_process:
        if bot.minecraft_log_process.poll() is None:
            embed.add_field(name="Processus de lecture", value="En cours d'exécution", inline=False)
        else:
            embed.add_field(name="Processus de lecture", value=f"Terminé (code: {bot.minecraft_log_process.poll()}")
    else:
        embed.add_field(name="Processus de lecture", value="Non démarré", inline=False)
    
    # Configuration info
    embed.add_field(name="Configuration", value=f"Prefix: `{config['command_prefix']}`\nLog path: `{minecraft_log_path}`\nTMUX session: `{minecraft_tmux_session}`\nUse sudo: `{use_sudo}`", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def enable(ctx):
    """Active le relais entre Minecraft et Discord"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
        return
    
    # Cancel any existing reading task
    global stop_reading
    stop_reading = True
    # Give a moment for any existing task to notice the flag change
    await asyncio.sleep(0.05)
    
    bot.minecraft_channel_id = ctx.channel.id
    await ctx.send("Commande active. Envoi actif des messages discord vers Minecraft...")
    await ctx.send("Envoi actif des messages Minecraft vers Discord...")
    
    stop_reading = False
    
    # Validate that the log file exists
    if not os.path.exists(minecraft_log_path):
        await ctx.send(f"ATTENTION: Le fichier de log Minecraft '{minecraft_log_path}' n'existe pas encore.")
        print(f"Warning: Log file {minecraft_log_path} does not exist yet")
    
    # Capture les messages Minecraft
    cmd = ['sudo', 'tail', '-f', minecraft_log_path] if use_sudo else ['tail', '-f', minecraft_log_path]
    try:
        bot.minecraft_log_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            bufsize=1,
            universal_newlines=True,
            text=True
        )
    except Exception as e:
        await ctx.send(f"Erreur lors du démarrage du processus de lecture des logs: {e}")
        print(f"Failed to start log process: {e}")
        # Reset channel ID since we failed to start
        bot.minecraft_channel_id = None
        return
    
    # Fonction pour lire les lignes du processus
    async def read_process():
        try:
            while not stop_reading:
                try:
                    line = await asyncio.to_thread(bot.minecraft_log_process.stdout.readline)
                    if not line:
                        # End of file or process terminated
                        break
                    line = line.strip()
                    if line:
                        match = re.search(r'<([^>]+)> (.+)', line)
                        if match:
                            username, message = match.groups()
                            await ctx.send(f"{username}: {message}")
                except (ValueError, OSError) as e:
                    # Handle specific I/O errors
                    if not stop_reading:  # Only log if we're still supposed to be reading
                        print(f"I/O error in read_process: {e}")
                    break
                except Exception as e:
                    # Unexpected error
                    print(f"Unexpected error in read_process: {e}")
                    traceback.print_exc()
                    break
        finally:
            # Cleanup: ensure process is terminated
            if hasattr(bot, 'minecraft_log_process') and bot.minecraft_log_process:
                try:
                    bot.minecraft_log_process.terminate()
                    bot.minecraft_log_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    bot.minecraft_log_process.kill()
                except Exception as e:
                    print(f"Error cleaning up log process: {e}")
    
    # Lancez la lecture des messages Minecraft dans un thread
    bot.read_task = asyncio.create_task(read_process())

@bot.command()
async def disable(ctx):
    """Désactive le relais entre Minecraft et Discord"""
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
        return
    
    # Arrêtez l'envoi de messages Discord vers Minecraft
    if hasattr(bot, 'minecraft_channel_id') and bot.minecraft_channel_id:
        bot.minecraft_channel_id = None
        
        # Arrêtez la lecture des messages Minecraft
        global stop_reading
        stop_reading = True
        
        # Attendez que la tâche de lecture se termine
        if hasattr(bot, 'read_task') and bot.read_task:
            try:
                await asyncio.wait_for(bot.read_task, timeout=5.0)
            except asyncio.TimeoutError:
                print("Read task did not finish in time, cancelling")
                bot.read_task.cancel()
                try:
                    await bot.read_task
                except asyncio.CancelledError:
                    pass
            except Exception as e:
                print(f"Error waiting for read task: {e}")
        
        # Fermez le processus qui lit les logs de Minecraft
        if hasattr(bot, 'minecraft_log_process') and bot.minecraft_log_process:
            print("Arrêt du processus de lecture des logs Minecraft...")
            try:
                bot.minecraft_log_process.terminate()
                # Wait for process to terminate gracefully
                try:
                    await asyncio.wait_for(asyncio.to_thread(bot.minecraft_log_process.wait), timeout=5.0)
                except asyncio.TimeoutError:
                    print("Process did not terminate in time, killing")
                    bot.minecraft_log_process.kill()
                    try:
                        bot.minecraft_log_process.wait(timeout=2)
                    except:
                        pass
            except Exception as e:
                print(f"Error terminating log process: {e}")
        
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
                result = subprocess.run(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    capture_output=True,
                    check=False  # We'll handle the return code ourselves
                )
                if result.returncode == 0:
                    print(f"Message envoyé avec succès dans Minecraft : {message.content}")
                else:
                    print(f"Erreur lors de l'envoi du message dans Minecraft (code {result.returncode}): {result.stderr}")
            except subprocess.SubprocessError as e:
                print(f"Subprocess error lors de l'envoi du message dans Minecraft : {e}")
            except Exception as e:
                print(f"Une erreur inattendue s'est produite : {e}")
                traceback.print_exc()
    
    await bot.process_commands(message)

def run_bot():
    bot.run(config['token'])

if __name__ == "__main__":
    run_bot()