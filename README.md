# NerdMC

NerdMC est un bot Discord. Il permet d'envoyer les messages du jeu en temps réel sur un canal Discord spécifique.

## Fonctionnalités principales

- Envoi le tchat Minecraft en temps réel sur un canal Discord
- Activation/désactivation du flux
- Formatage des messages pour une meilleure lisibilité

## Installation

### Clonage du dépôt

Clonnez le dépôt Git :
git clone https://github.com/estemobs/NerdMC.git


### Installation des dépendances

Installez les dépendances en exécutant :
pip install -r requirements.txt


### Configuration

Copiez le fichier d'exemple et remplissez vos informations :

```bash
cp config.json.example config.json
```

Paramètres disponibles dans `config.json` :

| Champ | Description |
|-------|-------------|
| `token` | Token de votre bot Discord |
| `command_prefix` | Préfixe des commandes (ex: `!`) |
| `minecraft_log_path` | Chemin vers le fichier `latest.log` de Minecraft |
| `minecraft_tmux_session` | Nom de la session tmux du serveur Minecraft |
| `use_sudo` | `true` si le bot nécessite sudo pour tail/tmux |

## Utilisation

Lancez le bot Discord :
python main.py

## Avertissements

- Assurez-vous que `tmux` est installé sur votre système et que votre serveur Minecraft tourne dans une session tmux nommée (par défaut `minecraft`).
- Si `use_sudo` est `true`, le bot doit pouvoir exécuter `sudo tail` et `sudo tmux` sans mot de passe. Ajoutez une règle sudoers si nécessaire.
- Vérifiez que votre compte Discord bot a les permissions nécessaires pour interagir avec les canaux.

## Contribution

Vous pouvez contribuer au développement de ce bot en soumettant des pull requests ou en participant aux discussions sur GitHub.


