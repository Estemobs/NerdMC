"""Bridge service that links a Minecraft server to a Discord channel."""

from __future__ import annotations

from collections import deque
from time import monotonic
from typing import Callable, Awaitable

from .log_reader import LogReader
from .rcon_client import RconClient


class _RateLimiter:
    """Simple per-key sliding-window rate limiter."""

    def __init__(self, max_messages: int, window_seconds: float) -> None:
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self._buckets: dict[str, deque[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = monotonic()
        bucket = self._buckets.setdefault(key, deque())
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_messages:
            return False
        bucket.append(now)
        return True


class MinecraftBridge:
    """Manages bidirectional communication between Minecraft and Discord.

    Parameters
    ----------
    config:
        The full application configuration dict (see ``nerdmc.config``).
    discord_send_callback:
        Async callable ``(username: str, message: str) -> None`` invoked
        whenever a chat message is received from Minecraft.
    """

    def __init__(
        self,
        config: dict,
        discord_send_callback: Callable[[str, str], Awaitable[None]],
    ) -> None:
        rcon_cfg = config["rcon"]
        self._rcon = RconClient(
            host=rcon_cfg["host"],
            port=rcon_cfg["port"],
            password=rcon_cfg["password"],
        )
        self._log_reader = LogReader(
            log_path=config["minecraft"]["log_path"],
            callback=self._on_minecraft_message,
        )
        self._discord_send = discord_send_callback
        self._active = False

        antispam_cfg = config.get("antispam", {})
        if antispam_cfg.get("enabled", True):
            self._limiter: _RateLimiter | None = _RateLimiter(
                max_messages=antispam_cfg.get("max_messages", 5),
                window_seconds=antispam_cfg.get("window_seconds", 10),
            )
        else:
            self._limiter = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """Return ``True`` when the bridge is running."""
        return self._active

    def start(self) -> None:
        """Start the bridge (begin reading logs)."""
        if not self._active:
            self._active = True
            self._log_reader.start()

    def stop(self) -> None:
        """Stop the bridge."""
        if self._active:
            self._active = False
            self._log_reader.stop()

    async def send_to_minecraft(self, username: str, message: str) -> None:
        """Send a Discord message to Minecraft via RCON.

        Applies rate-limiting keyed on *username* when the anti-spam
        feature is enabled.

        Raises ``RconError`` if the command could not be delivered.
        """
        if self._limiter is not None and not self._limiter.is_allowed(username):
            raise RateLimitError(
                f"Rate limit exceeded for user '{username}'. "
                "Please slow down."
            )
        command = f"say {username}: {message}"
        await self._rcon.send_command_async(command)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _on_minecraft_message(self, username: str, message: str) -> None:
        """Forwarded by the LogReader when a chat line is detected."""
        await self._discord_send(username, message)


class RateLimitError(Exception):
    """Raised when a user exceeds the configured message rate limit."""
