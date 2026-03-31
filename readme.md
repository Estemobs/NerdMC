# NerdMC

> Universal Discord ↔ Minecraft chat bridge — works with any server type (Vanilla, Paper, Spigot, Fabric, Forge…)

Messages sent in a Discord channel are forwarded to the Minecraft chat, and Minecraft chat messages appear in Discord in real time.

---

## How it works

| Direction | Method |
|-----------|--------|
| Minecraft → Discord | Tails `latest.log` and parses chat lines |
| Discord → Minecraft | Sends commands via **RCON** (recommended) or **tmux** |

Because the bridge reads the log file, it is compatible with any Minecraft server that writes standard logs.

---

## Requirements

- Python 3.10+
- A Discord bot token ([create one here](https://discord.com/developers/applications))
- A Minecraft server with either:
  - **RCON enabled** (recommended, any server type), or
  - The server running inside a **tmux** session

---

## Quick start

### 1 — Clone the repository

```bash
git clone https://github.com/Estemobs/NerdMC.git
cd NerdMC
```

### 2 — Install dependencies

```bash
pip install -r requirements.txt
```

### 3 — Configure the bot

Copy the example config and fill in your values:

```bash
cp config.json.example config.json
```

Edit `config.json`:

```json
{
  "token": "YOUR_DISCORD_BOT_TOKEN",
  "command_prefix": "!",
  "channel_id": 123456789012345678,
  "server_name": "My Minecraft Server",
  "minecraft_log": "/path/to/minecraft/logs/latest.log",
  "bridge_method": "rcon",
  "rcon": {
    "host": "localhost",
    "port": 25575,
    "password": "your_rcon_password"
  }
}
```

| Key | Description |
|-----|-------------|
| `token` | Discord bot token |
| `command_prefix` | Prefix for bot commands (default `!`) |
| `channel_id` | Discord channel ID where the bridge is active |
| `server_name` | Displayed in the bot's status |
| `minecraft_log` | Absolute path to `logs/latest.log` |
| `bridge_method` | `"rcon"` (recommended) or `"tmux"` |
| `rcon.host` | RCON host (usually `localhost`) |
| `rcon.port` | RCON port (default `25575`) |
| `rcon.password` | RCON password (set in `server.properties`) |
| `tmux.session` | tmux session name (only used when `bridge_method = "tmux"`) |

### 4 — Enable RCON on your Minecraft server

In `server.properties`:

```properties
enable-rcon=true
rcon.port=25575
rcon.password=your_rcon_password
```

Restart the server for the changes to take effect.

### 5 — Run the bot

```bash
python main.py
```

The bridge starts automatically as soon as the bot connects.

---

## Discord commands

All commands require **Administrator** permission.

| Command | Description |
|---------|-------------|
| `!bridge_enable` | Start the chat bridge |
| `!bridge_disable` | Stop the chat bridge |
| `!bridge_status` | Show current bridge status |

---

## Using tmux instead of RCON

If you prefer not to enable RCON, set `"bridge_method": "tmux"` and make sure:

1. The Minecraft server is running in a tmux session.
2. `tmux` is installed on the host machine.
3. `tmux.session` matches the name of your tmux session.

Start the server in tmux:

```bash
tmux new-session -d -s minecraft "java -Xmx2G -Xms2G -jar server.jar nogui"
```

---

## Server management script (optional)

`nerdmc_console.sh` is a helper shell script to manage your Minecraft server from the terminal:

```bash
chmod +x nerdmc_console.sh
./nerdmc_console.sh
```

Features: start, stop, restart (immediate or with countdown), whitelist management, and direct console access.

---

## Contributing

Pull requests and issues are welcome. Please open a PR against the `main` branch.
