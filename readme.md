# NerdMC

NerdMC est un bot Discord qui assure une liaison bidirectionnelle propre entre un serveur **Minecraft Vanilla** et un canal **Discord**, sans dépendre de `tmux` ou de `sudo`.

Il utilise :
- **RCON** pour envoyer les messages Discord → Minecraft (commande `say`)
- Un **lecteur de logs asynchrone** pour relayer le chat Minecraft → Discord, avec gestion de la rotation des logs

---

## Fonctionnalités

- Relai en temps réel du chat Minecraft ↔ Discord
- Activation / désactivation depuis Discord (`!enable` / `!disable`)
- Commande `!status` pour connaître l'état du bridge
- Anti-spam configurable (limite de messages par utilisateur par fenêtre de temps)
- Gestion de la rotation des logs (redémarre automatiquement la lecture après un `latest.log` rechargé)
- Aucun besoin de `sudo`, `tmux` ou `screen`

---

## Structure du projet

```
NerdMC/
├── main.py                 # Point d'entrée
├── config.yml.example      # Modèle de configuration
├── requirements.txt
├── readme.md
├── nerdmc/
│   ├── __init__.py
│   ├── config.py           # Chargement de la config YAML
│   ├── rcon_client.py      # Client RCON (mcrcon)
│   ├── log_reader.py       # Lecteur de logs asynchrone
│   ├── bridge.py           # Service bridge (start/stop/anti-spam)
│   └── bot.py              # Bot Discord
└── test/
    └── test_bridge.py      # Tests unitaires
```

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Estemobs/NerdMC.git
cd NerdMC
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

Dépendances :

| Paquet | Rôle |
|---|---|
| `discord.py` | Client Discord |
| `mcrcon` | Client RCON Minecraft |
| `PyYAML` | Lecture du fichier de config |

### 3. Configurer le bot

Copiez le modèle et remplissez vos valeurs :

```bash
cp config.yml.example config.yml
```

Éditez `config.yml` :

```yaml
discord:
  token: "VOTRE_TOKEN_DISCORD"
  channel_id: 123456789012345678   # ID du canal Discord (mode développeur)
  command_prefix: "!"

rcon:
  host: "localhost"
  port: 25575                       # rcon.port dans server.properties
  password: "VOTRE_MOT_DE_PASSE"   # rcon.password dans server.properties

minecraft:
  log_path: "/home/minecraft/logs/latest.log"

antispam:
  enabled: true
  max_messages: 5      # messages maximum par utilisateur…
  window_seconds: 10   # …sur cette fenêtre de temps (secondes)
```

### 4. Activer RCON sur le serveur Minecraft Vanilla

Dans `server.properties` (dossier du serveur Minecraft) :

```properties
enable-rcon=true
rcon.port=25575
rcon.password=VOTRE_MOT_DE_PASSE
```

Redémarrez le serveur après la modification.

> **Sécurité :** utilisez un mot de passe fort et n'exposez jamais le port RCON sur Internet.  
> Si le bot tourne sur la même machine que le serveur, liez RCON à `localhost` uniquement
> (ce qui est le comportement par défaut).

---

## Utilisation

```bash
python main.py
```

Une fois le bot en ligne, dans le canal Discord souhaité :

| Commande | Effet | Permissions requises |
|---|---|---|
| `!enable` | Active le bridge dans le canal courant | Administrateur |
| `!disable` | Désactive le bridge | Administrateur |
| `!status` | Affiche l'état actuel du bridge | Tous |

Le `channel_id` dans `config.yml` permet de pré-configurer le canal au démarrage
(le bridge démarre automatiquement sans avoir à taper `!enable`).

---

## Tests

```bash
python -m unittest discover -s test -v
```

---

## Contribution

Les pull requests et issues sont les bienvenues.  
Merci de bien vouloir décrire vos modifications et de vous assurer que les tests passent.

