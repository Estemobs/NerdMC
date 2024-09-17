#!/bin/bash

# Définir le répertoire de travail
WORKDIR="/home/minecraft"

# Nom de la session tmux
SESSION_NAME="minecraft"

# Fonction pour afficher le menu principal
function afficher_menu() {
    echo "Menu Principal :"
    echo "1. Démarrer le serveur"
    echo "2. Redémarrer le serveur"
    echo "3. Accéder au terminal du serveur"
    echo "4. Ajouter une personne à la whitelist"
    echo "5. Arrêter le serveur"
    echo "0. Quitter"
    echo -n "Sélectionnez une option : "
}

# Fonction pour démarrer le serveur
function demarrer_serveur() {
    cd "$WORKDIR" || { echo "Échec de l'accès au répertoire $WORKDIR"; exit 1; }
    tmux new-session -d -s "$SESSION_NAME" "java -Xmx2G -Xms2G -jar server.jar nogui"
    echo "Serveur Minecraft lancé dans la session tmux '$SESSION_NAME'"
    retour_menu
}

# Fonction pour redémarrer le serveur (avec deux options)
function redemarrer_serveur() {
    echo "Options de redémarrage :"
    echo "1. Redémarrage immédiat"
    echo "2. Redémarrage dans 1 minute"
    echo -n "Sélectionnez une option : "
    read -r OPTION
    
    case $OPTION in
        1)
            redemarrage_imminent
            ;;
        2)
            redemarrage_une_minute
            ;;
        *)
            echo "Option invalide. Retour au menu principal."
            retour_menu
            ;;
    esac
}

# Fonction pour un redémarrage immédiat
function redemarrage_imminent() {
    cd "$WORKDIR" || { echo "Échec de l'accès au répertoire $WORKDIR"; exit 1; }

    echo "Redémarrage immédiat..."
    tmux send-keys -t "$SESSION_NAME" "/title @a title {\"text\":\"REDÉMARRAGE IMMINENT\",\"color\":\"red\",\"bold\":true}" C-m
    tmux send-keys -t "$SESSION_NAME" "/execute as @a at @s run playsound minecraft:entity.ender_dragon.growl master @a" C-m
	
	# Attendre 5 secondes pour permettre aux joueurs de voir le message
    sleep 5
	
    # Arrêter le serveur
    echo "Arrêt du serveur Minecraft..."
    tmux send-keys -t "$SESSION_NAME" "stop" C-m
    
    # Attendre que le serveur s'arrête complètement
    sleep 10
    
    # Redémarrer le serveur Minecraft
    echo "Redémarrage du serveur Minecraft dans la session tmux '$SESSION_NAME'..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    tmux new-session -d -s "$SESSION_NAME" "java -Xmx2G -Xms2G -jar server.jar nogui"
    
    echo "Serveur Minecraft redémarré dans la session tmux '$SESSION_NAME'"
    retour_menu
}

# Fonction pour un redémarrage dans 1 minute avec un compte à rebours final
function redemarrage_une_minute() {
    cd "$WORKDIR" || { echo "Échec de l'accès au répertoire $WORKDIR"; exit 1; }

    echo "Redémarrage dans 1 minute..."
    tmux send-keys -t "$SESSION_NAME" "/title @a title {\"text\":\"REDÉMARRAGE DANS 1 MINUTE\",\"color\":\"yellow\",\"bold\":true}" C-m
	tmux send-keys -t "$SESSION_NAME" "/execute as @a at @s run playsound minecraft:entity.ender_dragon.growl master @a" C-m
    # Attendre 55 secondes avant le compte à rebours
    sleep 55

    # Compte à rebours de 5 secondes dans la console avec /say
    for i in {5..1}; do
        tmux send-keys -t "$SESSION_NAME" "/say §c§lREDÉMARRAGE DANS $i SECONDES" C-m
        sleep 1
    done

    # Arrêter le serveur
    echo "Arrêt du serveur Minecraft..."
    tmux send-keys -t "$SESSION_NAME" "stop" C-m

    # Attendre que le serveur s'arrête complètement
    sleep 10
    
    # Redémarrer le serveur Minecraft
    echo "Redémarrage du serveur Minecraft dans la session tmux '$SESSION_NAME'..."
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    tmux new-session -d -s "$SESSION_NAME" "java -Xmx2G -Xms2G -jar server.jar nogui"
    
    echo "Serveur Minecraft redémarré dans la session tmux '$SESSION_NAME'"
    retour_menu
}

# Fonction pour vérifier la session et proposer de relancer le serveur si elle n'existe pas
function verifier_session_tmux() {
    if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
        echo "La session tmux '$SESSION_NAME' n'existe pas. Assurez-vous que le serveur est en cours d'exécution."
        echo "Voulez-vous fermer toute ancienne session Java et redémarrer le serveur ? (oui/non)"
        read -r REPONSE
        if [[ "$REPONSE" == "oui" ]]; then
            echo "Fermeture des processus Java..."
            sudo killall java  # Fermeture de tous les processus Java
            redemarrer_serveur
        else
            retour_menu
        fi
    fi
}

# Fonction pour accéder au terminal du serveur avec boucle interactive
function acceder_terminal() {
    verifier_session_tmux  # Vérifie si la session existe, sinon propose de relancer

    echo "Accès au terminal du serveur. Tapez 'quit' pour revenir au menu principal."

    while true; do
        echo -n "> "
        read -r COMMAND
        
        if [[ "$COMMAND" == "quit" ]]; then
            echo "Retour au menu principal..."
            retour_menu
            break
        fi
        
        # Envoyer la commande au serveur Minecraft via tmux
        tmux send-keys -t "$SESSION_NAME" "$COMMAND" C-m
    done
}

# Fonction pour ajouter une personne à la whitelist et afficher un message dans le chat
function ajouter_whitelist() {
    verifier_session_tmux  # Vérifie si la session existe, sinon propose de relancer
    cd "$WORKDIR" || { echo "Échec de l'accès au répertoire $WORKDIR"; exit 1; }

    echo -n "Entrez le nom du joueur à ajouter à la whitelist : "
    read -r NOM_JOUEUR

    # Vérifier si le joueur est déjà dans la whitelist
    if tmux capture-pane -t "$SESSION_NAME" -pS -1000 | grep -q "$NOM_JOUEUR"; then
        echo "Le joueur '$NOM_JOUEUR' est déjà dans la whitelist."
        retour_menu
    else
        # Ajouter le joueur à la whitelist
        tmux send-keys -t "$SESSION_NAME" "/whitelist add $NOM_JOUEUR" C-m
        echo "Le joueur '$NOM_JOUEUR' a été ajouté à la whitelist."
        
        # Recharger la whitelist
        tmux send-keys -t "$SESSION_NAME" "/whitelist reload" C-m
		
        # Annonce dans le chat avec couleurs
        tmux send-keys -t "$SESSION_NAME" "/say §aLe joueur §e$NOM_JOUEUR §a a été ajouté à la whitelist" C-m

        retour_menu
    fi
}



# Fonction pour arrêter le serveur
function arreter_serveur() {
    verifier_session_tmux  # Vérifie si la session existe, sinon propose de relancer

    echo "Arrêt du serveur Minecraft..."
    tmux send-keys -t "$SESSION_NAME" "stop" C-m

    # Attendre que le serveur s'arrête complètement
    sleep 10

    # Optionnel : tuer la session tmux si nécessaire
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null
    
    echo "Serveur Minecraft arrêté."
    retour_menu
}

# Fonction pour retourner au menu principal
function retour_menu() {
    echo
    echo "Appuyez sur Entrée pour retourner au menu principal..."
    read
    afficher_menu
    traiter_option
}

# Fonction pour traiter les options du menu
function traiter_option() {
    read -r OPTION
    case $OPTION in
        1)
            demarrer_serveur
            ;;
        2)
            redemarrer_serveur
            ;;
        3)
            acceder_terminal
            ;;
        4)
            ajouter_whitelist
            ;;
        5)
            arreter_serveur
            ;;
        0)
            echo "Au revoir !"
            exit 0
            ;;
        *)
            echo "Option invalide, veuillez réessayer."
            afficher_menu
            traiter_option
            ;;
    esac
}

# Lancer le script
afficher_menu
traiter_option
