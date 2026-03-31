"""
NerdMC – Discord ↔ Minecraft chat bridge
-----------------------------------------
Minecraft → Discord : tails the server log file and forwards chat messages.
Discord  → Minecraft : sends messages via RCON (universal) or tmux (fallback).

All settings live in config.json (see config.json.example).
"""

import asyncio
import json
import logging
import os
import re
import subprocess
import sys
from typing import Optional

import discord
from discord.ext import commands

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nerdmc")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config: dict = json.load(f)
except FileNotFoundError:
    log.error("config.json not found. Copy config.json.example and fill in your values.")
    sys.exit(1)

REQUIRED_KEYS = ("token", "channel_id", "minecraft_log")
missing = [k for k in REQUIRED_KEYS if not config.get(k)]
if missing:
    log.error("Missing required config keys: %s", ", ".join(missing))
    sys.exit(1)

TOKEN: str = config["token"]
CHANNEL_ID: int = int(config["channel_id"])
LOG_PATH: str = config["minecraft_log"]
PREFIX: str = config.get("command_prefix", "!")
SERVER_NAME: str = config.get("server_name", "Minecraft")
BRIDGE_METHOD: str = config.get("bridge_method", "rcon").lower()  # "rcon" or "tmux"

# Validate that LOG_PATH is an absolute path to avoid unintended locations
if not os.path.isabs(LOG_PATH):
    log.error("minecraft_log must be an absolute path (e.g. /home/minecraft/logs/latest.log).")
    sys.exit(1)

RCON_HOST: str = config.get("rcon", {}).get("host", "localhost")
RCON_PORT: int = int(config.get("rcon", {}).get("port", 25575))
RCON_PASSWORD: str = config.get("rcon", {}).get("password", "")

TMUX_SESSION: str = config.get("tmux", {}).get("session", "minecraft")

# Regex that matches vanilla / Paper / Spigot / Fabric chat lines
# e.g. [12:34:56] [Server thread/INFO]: <PlayerName> Hello world
CHAT_REGEX = re.compile(r"<([^>]+)>\s+(.+)")

# ---------------------------------------------------------------------------
# RCON helper (optional import)
# ---------------------------------------------------------------------------
_rcon_available = False
if BRIDGE_METHOD == "rcon":
    try:
        import mcrcon  # type: ignore
        _rcon_available = True
    except ImportError:
        log.warning(
            "mcrcon not installed (pip install mcrcon). "
            "Falling back to tmux method."
        )
        BRIDGE_METHOD = "tmux"


def _sanitize(text: str) -> str:
    """Strip characters that could inject Minecraft commands or break RCON/tmux."""
    # Remove newlines to prevent command injection via multi-line input
    return text.replace("\n", " ").replace("\r", " ").replace("\x00", "")


def send_to_minecraft(username: str, content: str) -> bool:
    """Forward a Discord message to Minecraft. Returns True on success."""
    safe_username = _sanitize(username)
    safe_content = _sanitize(content)
    text = f"[Discord] {safe_username}: {safe_content}"
    if BRIDGE_METHOD == "rcon" and _rcon_available:
        try:
            with mcrcon.MCRcon(RCON_HOST, RCON_PASSWORD, RCON_PORT) as mcr:
                mcr.command(f"say {text}")
            return True
        except Exception as exc:
            log.error("RCON error: %s", exc)
            return False
    else:
        # tmux fallback
        try:
            subprocess.run(
                ["tmux", "send-keys", "-t", TMUX_SESSION, f"say {text}", "Enter"],
                check=True,
                capture_output=True,
                text=True,
            )
            return True
        except subprocess.CalledProcessError as exc:
            log.error("tmux error: %s\n%s", exc, exc.stderr)
            return False


# ---------------------------------------------------------------------------
# Discord bot
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Bridge state
_bridge_active: bool = False
_log_task: Optional[asyncio.Task] = None


async def _tail_log() -> None:
    """Continuously read the Minecraft log and post chat lines to Discord."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        log.error("Channel %s not found. Check channel_id in config.json.", CHANNEL_ID)
        return

    log.info("Starting log tail: %s", LOG_PATH)
    try:
        process = await asyncio.create_subprocess_exec(
            "tail", "-n", "0", "-f", LOG_PATH,
            stdout=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        log.error("'tail' command not found.")
        return
    except Exception as exc:
        log.error("Failed to start log tail: %s", exc)
        return

    try:
        while _bridge_active:
            line_bytes = await process.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace").rstrip()
            match = CHAT_REGEX.search(line)
            if match:
                username, message = match.groups()
                await channel.send(f"**{username}**: {message}")
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("Error reading log: %s", exc)
    finally:
        process.kill()
        log.info("Log tail stopped.")


def _start_bridge() -> None:
    global _bridge_active, _log_task
    _bridge_active = True
    _log_task = asyncio.ensure_future(_tail_log())


def _stop_bridge() -> None:
    global _bridge_active, _log_task
    _bridge_active = False
    if _log_task and not _log_task.done():
        _log_task.cancel()
    _log_task = None


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------
@bot.event
async def on_ready() -> None:
    log.info("Logged in as %s (ID: %s)", bot.user, bot.user.id)
    await bot.change_presence(activity=discord.Game(name=SERVER_NAME))
    if CHANNEL_ID:
        _start_bridge()
        log.info("Bridge started automatically for channel %s.", CHANNEL_ID)


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if _bridge_active and message.channel.id == CHANNEL_ID:
        username = message.author.display_name
        success = await asyncio.to_thread(send_to_minecraft, username, message.content)
        if not success:
            log.warning("Failed to forward message to Minecraft.")
    await bot.process_commands(message)


# ---------------------------------------------------------------------------
# Commands (admin only)
# ---------------------------------------------------------------------------
def _is_admin(ctx: commands.Context) -> bool:
    return ctx.author.guild_permissions.administrator


@bot.command(name="bridge_enable", help="Start the Discord ↔ Minecraft chat bridge.")
async def bridge_enable(ctx: commands.Context) -> None:
    if not _is_admin(ctx):
        await ctx.send("❌ Administrator permission required.")
        return
    if _bridge_active:
        await ctx.send("ℹ️ Bridge is already active.")
        return
    _start_bridge()
    await ctx.send(f"✅ Chat bridge enabled on <#{CHANNEL_ID}>.")


@bot.command(name="bridge_disable", help="Stop the Discord ↔ Minecraft chat bridge.")
async def bridge_disable(ctx: commands.Context) -> None:
    if not _is_admin(ctx):
        await ctx.send("❌ Administrator permission required.")
        return
    if not _bridge_active:
        await ctx.send("ℹ️ Bridge is not active.")
        return
    _stop_bridge()
    await ctx.send("🛑 Chat bridge disabled.")


@bot.command(name="bridge_status", help="Show the current bridge status.")
async def bridge_status(ctx: commands.Context) -> None:
    status = "✅ Active" if _bridge_active else "🛑 Inactive"
    method = BRIDGE_METHOD.upper()
    await ctx.send(
        f"**NerdMC Bridge Status**\n"
        f"• Status : {status}\n"
        f"• Channel: <#{CHANNEL_ID}>\n"
        f"• Method : {method}\n"
        f"• Server : {SERVER_NAME}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    bot.run(TOKEN)