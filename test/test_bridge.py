"""Unit tests for NerdMC bridge components."""

import asyncio
import os
import tempfile
import time
import unittest
from unittest.mock import AsyncMock, patch

from nerdmc.config import load_config, _deep_merge, DEFAULT_CONFIG
from nerdmc.bridge import MinecraftBridge, RateLimitError, _RateLimiter
from nerdmc.log_reader import LogReader, CHAT_PATTERN


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------

class TestDeepMerge(unittest.TestCase):
    def test_merges_nested_dicts(self):
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 99, "z": 0}, "c": 4}
        result = _deep_merge(base, override)
        self.assertEqual(result["a"], {"x": 1, "y": 99, "z": 0})
        self.assertEqual(result["b"], 3)
        self.assertEqual(result["c"], 4)

    def test_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        override = {"a": {"x": 2}}
        _deep_merge(base, override)
        self.assertEqual(base["a"]["x"], 1)


class TestLoadConfig(unittest.TestCase):
    def test_raises_on_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/path/config.yml")

    def test_loads_and_merges_defaults(self):
        content = (
            "discord:\n"
            "  token: tok123\n"
            "  channel_id: 42\n"
            "rcon:\n"
            "  password: secret\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as tf:
            tf.write(content)
            path = tf.name
        try:
            cfg = load_config(path)
            self.assertEqual(cfg["discord"]["token"], "tok123")
            self.assertEqual(cfg["discord"]["channel_id"], 42)
            self.assertEqual(cfg["rcon"]["password"], "secret")
            # Defaults should still be present
            self.assertEqual(cfg["rcon"]["host"], DEFAULT_CONFIG["rcon"]["host"])
            self.assertEqual(
                cfg["minecraft"]["log_path"],
                DEFAULT_CONFIG["minecraft"]["log_path"],
            )
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Rate limiter tests
# ---------------------------------------------------------------------------

class TestRateLimiter(unittest.TestCase):
    def test_allows_up_to_max_messages(self):
        rl = _RateLimiter(max_messages=3, window_seconds=10)
        self.assertTrue(rl.is_allowed("alice"))
        self.assertTrue(rl.is_allowed("alice"))
        self.assertTrue(rl.is_allowed("alice"))
        self.assertFalse(rl.is_allowed("alice"))

    def test_different_users_have_independent_buckets(self):
        rl = _RateLimiter(max_messages=1, window_seconds=10)
        self.assertTrue(rl.is_allowed("alice"))
        self.assertFalse(rl.is_allowed("alice"))
        self.assertTrue(rl.is_allowed("bob"))

    def test_allows_after_window_expires(self):
        rl = _RateLimiter(max_messages=1, window_seconds=0.05)
        self.assertTrue(rl.is_allowed("alice"))
        self.assertFalse(rl.is_allowed("alice"))
        time.sleep(0.1)
        self.assertTrue(rl.is_allowed("alice"))


# ---------------------------------------------------------------------------
# Bridge tests
# ---------------------------------------------------------------------------

def _make_config(**overrides):
    cfg = {
        "discord": {"token": "t", "channel_id": 1, "command_prefix": "!"},
        "rcon": {"host": "localhost", "port": 25575, "password": "pw"},
        "minecraft": {"log_path": "/tmp/fake.log"},
        "antispam": {"enabled": True, "max_messages": 3, "window_seconds": 10},
    }
    cfg.update(overrides)
    return cfg


class TestMinecraftBridge(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.discord_cb = AsyncMock()
        with patch("nerdmc.bridge.RconClient"), patch("nerdmc.bridge.LogReader"):
            self.bridge = MinecraftBridge(_make_config(), self.discord_cb)

    def test_not_active_initially(self):
        self.assertFalse(self.bridge.is_active)

    def test_start_sets_active(self):
        self.bridge.start()
        self.assertTrue(self.bridge.is_active)

    def test_stop_clears_active(self):
        self.bridge.start()
        self.bridge.stop()
        self.assertFalse(self.bridge.is_active)

    async def test_send_to_minecraft_calls_rcon(self):
        self.bridge._rcon.send_command_async = AsyncMock(return_value="")
        await self.bridge.send_to_minecraft("Alice", "hello")
        self.bridge._rcon.send_command_async.assert_awaited_once_with(
            "say Alice: hello"
        )

    async def test_send_to_minecraft_rate_limited(self):
        self.bridge._rcon.send_command_async = AsyncMock(return_value="")
        for _ in range(3):
            await self.bridge.send_to_minecraft("Alice", "hi")
        with self.assertRaises(RateLimitError):
            await self.bridge.send_to_minecraft("Alice", "hi")

    async def test_send_to_minecraft_no_rate_limit_when_disabled(self):
        cfg = _make_config(antispam={"enabled": False})
        discord_cb = AsyncMock()
        with patch("nerdmc.bridge.RconClient"), patch("nerdmc.bridge.LogReader"):
            bridge = MinecraftBridge(cfg, discord_cb)
        bridge._rcon.send_command_async = AsyncMock(return_value="")
        for _ in range(10):
            await bridge.send_to_minecraft("Alice", "hi")
        self.assertEqual(bridge._rcon.send_command_async.await_count, 10)

    async def test_on_minecraft_message_calls_discord_cb(self):
        await self.bridge._on_minecraft_message("Steve", "Hello from MC!")
        self.discord_cb.assert_awaited_once_with("Steve", "Hello from MC!")


# ---------------------------------------------------------------------------
# Log reader tests
# ---------------------------------------------------------------------------

class TestChatPattern(unittest.TestCase):
    def test_matches_vanilla_chat(self):
        line = "[12:34:56] [Server thread/INFO]: <PlayerOne> hello world"
        m = CHAT_PATTERN.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "PlayerOne")
        self.assertEqual(m.group(2), "hello world")

    def test_does_not_match_non_chat(self):
        line = "[12:34:56] [Server thread/INFO]: PlayerOne joined the game"
        self.assertIsNone(CHAT_PATTERN.search(line))

    def test_matches_simple_chat(self):
        line = "<Alice> hi there"
        m = CHAT_PATTERN.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "Alice")
        self.assertEqual(m.group(2), "hi there")


class TestLogReaderIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_reads_new_lines(self):
        received: list = []

        async def cb(username: str, message: str) -> None:
            received.append((username, message))

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False
        ) as tf:
            path = tf.name

        try:
            reader = LogReader(path, cb, poll_interval=0.05)
            reader.start()
            await asyncio.sleep(0.1)  # let reader open and seek to end

            # Append a chat line
            with open(path, "a") as f:
                f.write("[12:00:00] [Server thread/INFO]: <Bob> test message\n")

            await asyncio.sleep(0.3)  # let reader pick it up
            reader.stop()

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0], ("Bob", "test message"))
        finally:
            os.unlink(path)

    async def test_ignores_non_chat_lines(self):
        received: list = []

        async def cb(username: str, message: str) -> None:
            received.append((username, message))

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False
        ) as tf:
            path = tf.name

        try:
            reader = LogReader(path, cb, poll_interval=0.05)
            reader.start()
            await asyncio.sleep(0.1)

            with open(path, "a") as f:
                f.write("[12:00:00] [Server thread/INFO]: Server started.\n")
                f.write("[12:00:01] [Server thread/INFO]: <Alice> hi\n")

            await asyncio.sleep(0.3)
            reader.stop()

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0], ("Alice", "hi"))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
