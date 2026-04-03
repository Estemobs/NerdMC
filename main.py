"""NerdMC entry point – Discord ⇄ Minecraft Vanilla bridge."""

from nerdmc.config import load_config
from nerdmc.bot import NerdMCBot


def main() -> None:
    config = load_config("config.yml")
    token = config["discord"]["token"]
    if not token:
        raise ValueError(
            "Discord token is not set. "
            "Please fill in 'discord.token' in config.yml."
        )
    bot = NerdMCBot(config)
    bot.run(token)


if __name__ == "__main__":
    main()
