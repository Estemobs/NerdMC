"""Discord bot for the NerdMC bridge."""

from __future__ import annotations

import discord
from discord.ext import commands

from .bridge import MinecraftBridge, RateLimitError
from .rcon_client import RconError


class NerdMCBot(commands.Bot):
    """Discord bot that bridges chat between Discord and Minecraft.

    Commands
    --------
    ``!enable``  (admin only)
        Activate the bridge in the current channel.
    ``!disable``  (admin only)
        Deactivate the bridge.
    """

    def __init__(self, config: dict) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=config["discord"].get("command_prefix", "!"),
            intents=intents,
        )
        self.config = config
        self._bridge = MinecraftBridge(config, self._on_minecraft_chat)
        # channel_id may be pre-configured or set at runtime via !enable
        self._channel_id: int | None = config["discord"].get("channel_id")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def setup_hook(self) -> None:
        """Called once after login; register commands."""
        self._register_commands()

    async def on_ready(self) -> None:
        print(f"[NerdMC] Logged in as {self.user}")
        await self.change_presence(
            activity=discord.Game(name="Minecraft Bridge")
        )
        # Auto-start if a channel is already configured
        if self._channel_id is not None:
            self._bridge.start()
            print(f"[NerdMC] Bridge auto-started for channel {self._channel_id}")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self._bridge.is_active and self._channel_id == message.channel.id:
            username = str(message.author.display_name)
            try:
                await self._bridge.send_to_minecraft(username, message.content)
            except RateLimitError as exc:
                await message.channel.send(f"⚠️ {exc}")
            except RconError as exc:
                print(f"[NerdMC] RCON error: {exc}")
                await message.channel.send(
                    "⚠️ Could not send message to Minecraft (RCON error)."
                )
        await self.process_commands(message)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _register_commands(self) -> None:
        @self.command(name="enable")
        async def enable(ctx: commands.Context) -> None:
            """Activate the Discord⇄Minecraft bridge in this channel."""
            await self._handle_enable(ctx)

        @self.command(name="disable")
        async def disable(ctx: commands.Context) -> None:
            """Deactivate the Discord⇄Minecraft bridge."""
            await self._handle_disable(ctx)

        @self.command(name="status")
        async def status(ctx: commands.Context) -> None:
            """Show the current bridge status."""
            await self._handle_status(ctx)

    async def _handle_enable(self, ctx: commands.Context) -> None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Vous n'avez pas les permissions nécessaires.")
            return
        if self._bridge.is_active:
            await ctx.send("ℹ️ Le bridge est déjà actif.")
            return
        self._channel_id = ctx.channel.id
        self._bridge.start()
        await ctx.send(
            "✅ Bridge activé dans ce canal. "
            "Les messages Minecraft apparaîtront ici et vos messages "
            "seront envoyés au serveur."
        )

    async def _handle_disable(self, ctx: commands.Context) -> None:
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Vous n'avez pas les permissions nécessaires.")
            return
        if not self._bridge.is_active:
            await ctx.send("ℹ️ Le bridge n'était pas actif.")
            return
        self._bridge.stop()
        await ctx.send("🛑 Bridge désactivé.")

    async def _handle_status(self, ctx: commands.Context) -> None:
        state = "✅ actif" if self._bridge.is_active else "🛑 inactif"
        channel_info = (
            f"<#{self._channel_id}>" if self._channel_id else "non configuré"
        )
        await ctx.send(
            f"**NerdMC Bridge** – état : {state}\nCanal : {channel_info}"
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _on_minecraft_chat(self, username: str, message: str) -> None:
        """Send an in-game chat message to the configured Discord channel."""
        if self._channel_id is None:
            return
        channel = self.get_channel(self._channel_id)
        if channel is None:
            return
        await channel.send(f"🎮 **{username}**: {message}")
