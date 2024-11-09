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

Remplissez les champs du fichier `config.json` avec vos informations :
   - Token Discord
   - Commande préfixe pour les utilisateurs
   - Informations de connexion Minecraft

```json
   {
    "token": "votre token ",
    "command_prefix": "votre prefix"
  }
```

## Utilisation

Lancez le bot Discord :
python main.py

## Avertissements

- Assurez-vous que tmux est installé sur votre système avant d'exécuter le bot.
- Vérifiez que votre compte Discord bot a les permissions nécessaires pour interagir avec les canaux.
- Le bot nécessite une connexion constante à Discord et à votre serveur Minecraft.

## Contribution

Vous pouvez contribuer au développement de ce bot en soumettant des pull requests ou en participant aux discussions sur GitHub.


