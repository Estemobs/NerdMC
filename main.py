import discord
from discord.ext import commands
import json
import os
import subprocess
import asyncio
import atexit
import logging
import shutil
import signal
import re

config_path = os.environ.get('NERDMC_CONFIG', 'config.json')
REQUIRED_SETTINGS = ('token', 'command_prefix')
CHAT_RE = re.compile(r'<([^>]+)> (.+)')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('nerdmc')


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

minecraft_log_path = config.get('minecraft_log_path', '/home/minecraft/logs/latest.log')
minecraft_tmux_session = config.get('minecraft_tmux_session', 'minecraft')
use_sudo = config.get('use_sudo', True)

bot = commands.Bot(command_prefix=config['command_prefix'], intents=intents)

if shutil.which('tmux') is None:
    log.warning("tmux introuvable dans le PATH : l'envoi Discord → Minecraft ne fonctionnera pas.")


def _terminate(proc):
    """Tue le groupe de processus : sudo lance tail dans un sous-processus."""
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except ProcessLookupError:
        pass


async def _stop_relay():
    bot.minecraft_channel_id = None
    proc = getattr(bot, 'minecraft_log_process', None)
    bot.minecraft_log_process = None
    task = getattr(bot, 'read_task', None)
    bot.read_task = None

    if proc is not None and proc.poll() is None:
        _terminate(proc)
        try:
            await asyncio.wait_for(asyncio.to_thread(proc.wait), timeout=5.0)
        except asyncio.TimeoutError:
            log.warning("Le processus tail ne s'arrête pas, kill forcé.")
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
    if task is not None:
        task.cancel()


async def _read_log(channel, proc):
    try:
        while True:
            line = await asyncio.to_thread(proc.stdout.readline)
            if not line:
                break
            match = CHAT_RE.search(line.strip())
            if match:
                username, message = match.groups()
                await channel.send(f"{username}: {message}")
    except asyncio.CancelledError:
        pass
    except Exception:
        log.exception("Erreur dans la lecture des logs Minecraft")


def _cleanup():
    _terminate(getattr(bot, 'minecraft_log_process', None))


atexit.register(_cleanup)


@bot.event
async def on_ready():
    log.info("%s has connected to Discord!", bot.user)
    game = discord.Game(name="mc.forezaaaa.fr")
    await bot.change_presence(activity=game)


@bot.command()
async def enable(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
        return

    await _stop_relay()
    cmd = ['sudo', 'tail', '-F', minecraft_log_path] if use_sudo else ['tail', '-F', minecraft_log_path]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        text=True,
        start_new_session=True,
    )
    bot.minecraft_log_process = proc
    bot.minecraft_channel_id = ctx.channel.id
    bot.read_task = asyncio.create_task(_read_log(ctx.channel, proc))
    await ctx.send("Relais actif : Minecraft → Discord et Discord → Minecraft dans ce canal.")


@bot.command()
async def disable(ctx):
    if not ctx.author.guild_permissions.administrator:
        await ctx.send("Vous n'avez pas les permissions nécessaires pour exécuter cette commande.")
        return

    if getattr(bot, 'minecraft_channel_id', None):
        await _stop_relay()
        await ctx.send("Relais désactivé.")
    else:
        await ctx.send("Le relais n'était pas activé.")


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

    channel_id = getattr(bot, 'minecraft_channel_id', None)
    if channel_id and message.channel.id == channel_id:
        username = str(message.author)
        cmd = ['sudo', 'tmux', 'send-keys', '-t', minecraft_tmux_session, f"say {username}: {message.content}", 'C-j'] if use_sudo else ['tmux', 'send-keys', '-t', minecraft_tmux_session, f"say {username}: {message.content}", 'C-j']
        try:
            await asyncio.to_thread(
                subprocess.run,
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            log.info("Message envoyé dans Minecraft : %s", message.content)
        except subprocess.CalledProcessError as e:
            log.error("Erreur lors de l'envoi du message dans Minecraft : %s\n%s", e, e.stderr)
        except Exception:
            log.exception("Erreur lors de l'envoi du message dans Minecraft")

    await bot.process_commands(message)


def run_bot():
    bot.run(config['token'])


if __name__ == "__main__":
    run_bot()
