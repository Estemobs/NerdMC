"""Async Minecraft log file watcher with log-rotation support."""

import asyncio
import os
import re
from typing import Callable, Awaitable

# Matches vanilla/Spigot chat lines, e.g.:
#   [12:34:56] [Server thread/INFO]: <PlayerName> hello world
CHAT_PATTERN = re.compile(r"<([^>]+)>\s+(.+)")


class LogReader:
    """Watches a Minecraft log file and calls *callback* for each chat line.

    Handles:
    * New lines appended to the current log file.
    * Log rotation: detects when the file is replaced (inode change or size
      shrink) and reopens it automatically.

    Parameters
    ----------
    log_path:
        Absolute path to the Minecraft log file (e.g. ``/path/to/logs/latest.log``).
    callback:
        Async callable ``(username: str, message: str) -> None`` invoked for
        every chat message detected.
    poll_interval:
        Seconds between consecutive reads (default: ``0.2``).
    """

    def __init__(
        self,
        log_path: str,
        callback: Callable[[str, str], Awaitable[None]],
        poll_interval: float = 0.2,
    ) -> None:
        self.log_path = log_path
        self.callback = callback
        self.poll_interval = poll_interval
        self._running = False
        self._task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start watching the log file (schedules an asyncio task)."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._watch(), name="log-reader")

    def stop(self) -> None:
        """Stop watching the log file."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _watch(self) -> None:
        try:
            fh = None
            last_inode: int | None = None
            last_size: int = 0

            while self._running:
                fh, last_inode, last_size = await self._reopen_if_needed(
                    fh, last_inode, last_size
                )
                if fh is None:
                    await asyncio.sleep(self.poll_interval)
                    continue

                # Read all available new lines
                while True:
                    line = fh.readline()
                    if not line:
                        break
                    last_size = fh.tell()
                    match = CHAT_PATTERN.search(line.rstrip())
                    if match:
                        username, message = match.groups()
                        try:
                            await self.callback(username, message)
                        except Exception as exc:
                            print(f"[LogReader] callback error: {exc}")

                await asyncio.sleep(self.poll_interval)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            print(f"[LogReader] unexpected error: {exc}")
        finally:
            if fh is not None:
                fh.close()

    async def _reopen_if_needed(self, fh, last_inode, last_size):
        """Return *(fh, last_inode, last_size)*, reopening the file when needed."""
        try:
            stat = os.stat(self.log_path)
        except FileNotFoundError:
            if fh is not None:
                fh.close()
            return None, None, 0

        rotated = (
            fh is None
            or stat.st_ino != last_inode
            or stat.st_size < last_size
        )

        if rotated:
            if fh is not None:
                fh.close()
            fh = open(self.log_path, "r", encoding="utf-8", errors="replace")
            # On first open: skip existing content to avoid replaying
            # old messages; on rotation: read from the beginning.
            if last_inode is None:
                fh.seek(0, 2)  # seek to end on first open
            last_inode = stat.st_ino
            last_size = stat.st_size

        return fh, last_inode, last_size
