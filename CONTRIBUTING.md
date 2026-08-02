# Contribution

Merci de vouloir contribuer à NerdMC !

## Développement

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copiez `config.json.example` en `config.json` et renseignez vos informations (token Discord, connexion Minecraft). `config.json` est ignoré par git.

## Lancement

```bash
python main.py
```

Prérequis : `tmux` installé sur le système.

## Vérifications avant PR

```bash
python -m compileall -q .
```

## Licence

Ce projet est sous licence MIT.
