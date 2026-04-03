"""RCON client wrapper for sending commands to a Minecraft server."""

import asyncio

from mcrcon import MCRcon


class RconError(Exception):
    """Raised when an RCON command fails."""


class RconClient:
    """Thin wrapper around ``mcrcon.MCRcon``.

    Each call opens a short-lived connection, sends the command, and closes
    the connection – this keeps the implementation simple and avoids
    long-lived TCP state that could silently break after a server restart.
    """

    def __init__(self, host: str, port: int, password: str) -> None:
        self.host = host
        self.port = port
        self.password = password

    def send_command(self, command: str) -> str:
        """Send *command* synchronously and return the server response."""
        try:
            with MCRcon(self.host, self.password, port=self.port) as mcr:
                return mcr.command(command)
        except Exception as exc:
            raise RconError(f"RCON command failed: {exc}") from exc

    async def send_command_async(self, command: str) -> str:
        """Async wrapper – runs ``send_command`` in a thread-pool executor."""
        return await asyncio.to_thread(self.send_command, command)
