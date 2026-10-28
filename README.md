# NerdMC

NerdMC est un bot Discord. Il permet d'envoyer les messages du jeu en temps réel sur un canal Discord spécifique.

## Fonctionnalités principales

- Envoi le tchat Minecraft en temps réel sur un canal Discord
- Activation/désactivation du flux
- Formatage des messages pour une meilleure lisibilité
- **Nouvelle commande `!status`** : Affiche l'état actuel du bot (canal Minecraft, lecture des logs, processus, configuration)
- Gestion améliorée des erreurs et des ressources
- Validation de la configuration au démarrage

## Installation

### Clonage du dépôt

Clonnez le dépôt Git :
```
git clone https://github.com/estemobs/NerdMC.git
```

### Installation des dépendances

Installez les dépendances en exécutant :
```
pip install -r requirements.txt
```

### Configuration

Copiez le fichier d'exemple et remplissez vos informations :

```bash
cp config.json.example config.json
```

Paramètres disponibles dans `config.json` :

| Champ | Description | Obligatoire |
|-------|-------------|-------------|
| `token` | Token de votre bot Discord | Oui |
| `command_prefix` | Préfixe des commandes (ex: `!`) | Oui |
| `minecraft_log_path` | Chemin vers le fichier `latest.log` de Minecraft | Non (défaut: `/home/minecraft/logs/latest.log`) |
| `minecraft_tmux_session` | Nom de la session tmux du serveur Minecraft | Non (défaut: `minecraft`) |
| `use_sudo` | `true` si le bot nécessite sudo pour tail/tmux | Non (défaut: `true`) |

> **Note** : Le bot valide la configuration au démarrage et quittera avec un message d'erreur clair si des champs obligatoires sont manquants ou si le JSON est invalide.

## Utilisation

Lancez le bot Discord :
```
python main.py
```

### Commandes Discord

Le bot répond aux commandes suivantes dans les canaux où il a la permission de lire et d'envoyer des messages :

- `!enable` : Active le relais entre Minecraft et Discord dans le canal actuel
- `!disable` : Désactive le relais entre Minecraft et Discord
- `!status` : Affiche l'état actuel du bot (disponible dans n'importe quel canal où le bot peut envoyer des messages)

> **Note** : Les commandes `!enable` et `!disable` nécessitent la permission d'administrateur sur le serveur Discord.

## Avertissements

- Assurez-vous que `tmux` est installé sur votre système et que votre serveur Minecraft tourne dans une session tmux nommée (par défaut `minecraft`).
- Si `use_sudo` est `true`, le bot doit pouvoir exécuter `sudo tail` et `sudo tmux` sans mot de passe. Ajoutez une règle sudoers si nécessaire.
- Vérifiez que votre compte Discord bot a les permissions nécessaires pour interagir avec les canaux.
- Le bot nécessite un accès en lecture au fichier de log Minecraft (`latest.log`). Assurez-vous que le bot a les permissions nécessaires pour lire ce fichier.

## Dépannage

### Le bot ne démarre pas

- Vérifiez que le fichier `config.json` existe et contient un JSON valide
- Assurez-vous que les champs obligatoires `token` et `command_prefix` sont présents et non vides
- Consultez les messages d'erreur affichés au démarrage pour plus de détails

### Aucun message Minecraft n'apparaît dans Discord

- Utilisez la commande `!status` pour vérifier l'état du bot
- Assurez-vous que le relais est activé (`!enable` dans le canal souhaité)
- Vérifiez que le fichier de log Minecraft existe au chemin spécifié dans la configuration
- Confirmez que le bot a la permission de lire le fichier de log
- Vérifiez que le processus de lecture des logs est actif (visible dans `!status`)

### Les messages Discord n'apparaissent pas dans Minecraft

- Utilisez la commande `!status` pour vérifier que le canal Minecraft est défini
- Assurez-vous que le serveur Minecraft tourne dans une session tmux nommée comme spécifié dans la configuration
- Vérifiez que le bot a la permission d'exécuter les commandes tmux (avec sudo si nécessaire)
- Consultez les logs du bot pour voir les erreurs lors de l'envoi des messages

## État du projet

Version 1.0.0 — les fonctionnalités décrites ci-dessus sont livrées et stables.
Aucun ticket fonctionnel ouvert ; les mises à jour de dépendances sont automatisées par Renovate.

## Contribution

Vous pouvez contribuer au développement de ce bot en soumettant des pull requests ou en participant aux discussions sur GitHub.

Lors de la soumission de pull requests :
1. Forkez le dépôt
2. Créez une branche pour votre fonctionnalité (`git checkout -b feature/amazing-feature`)
3. Commitez vos changements (`git commit -m 'Add some amazing feature'`)
4. Poussez vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrez une pull request

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.