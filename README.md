# Ninis Discord Bot

Un bot Discord pour configurer et gérer le serveur communautaire Ninis.

## Fonctionnalités

### Configuration du serveur
- Création automatique de tous les rôles avec couleurs personnalisées
- Configuration des catégories et salons prédéfinis
- Messages par défaut dans les salons importants
- Création de salons textuels et vocaux
- Système de vérification par acceptation des règles avec rôle-réaction

### Gestion des rôles
- Système de réactions pour attribuer des rôles
- Système de rôles organisés par catégories (Sexe et Âge)
- Rôles esthétiques avec hiérarchie correcte
- Permissions adaptées pour chaque type de rôle

### Modération
- Commandes pour bannir, expulser et rendre muet des membres
- Système de purge de messages
- Journal de modération détaillé pour suivre les actions
- Système anti-spam avec détection de liens et avertissements progressifs

### Système de tickets
- Création de tickets pour contacter le staff
- Interface utilisateur intuitive avec boutons Discord
- Transcription des tickets et options de fermeture
- Possibilité d'ajouter ou de retirer des utilisateurs d'un ticket

### Intégration IA
- Commande `!ask` pour interagir avec ChatGPT (modèle gpt-4o-mini)
- Réponses limitées à 2000 caractères pour respecter les limites Discord
- Gestion des erreurs d'API intelligente

### Musique
- Lecture de musique depuis YouTube dans les salons vocaux
- 5 salons vocaux dédiés à la musique
- Commandes complètes : play, skip, pause, resume, queue, etc.
- Affichage des informations de la piste en cours
- Gestion robuste de la file d'attente

### TikTok
- Notifications pour les nouveaux TikTok et lives
- Canal dédié aux notifications TikTok
- Commandes pour configurer les comptes à surveiller

### Emojis
- Ajout automatique d'émojis tendance au serveur
- Catégories d'émojis: anime et basique
- Commandes pour gérer et lister les émojis du serveur
- Respect des limites d'émojis selon le niveau de boost

### Statistiques et logging
- Canaux de statistiques du serveur mis à jour régulièrement
- Logging avancé des événements du serveur
- Surveillance de la connexion Discord avec vérification des heartbeats

## Configuration

1. Créez une application et un bot sur le [Portail des développeurs Discord](https://discord.com/developers/applications)
2. Invitez le bot sur votre serveur avec les permissions nécessaires
3. Configurez le token dans les variables d'environnement ou dans `config.py`
4. Lancez le bot avec `python main.py`

## Commandes principales

### Configuration et Setup
- `!setup_ninis` - Configure le serveur avec tous les éléments prédéfinis
- `!setup_verification` - Configure le système de vérification avec règlement
- `!setup_bot` - Crée les salons dédiés aux commandes du bot
- `!setup_basic_roles` - Configure les rôles de base simplifiés
- `!setup_role_reactions` - Configure le système de rôles-réaction
- `!update_rules` - Met à jour le règlement du serveur
- `!reset_server` - Réinitialise complètement le serveur (danger)

### Modération
- `!clear [nombre]` - Supprime un nombre de messages
- `!kick [@membre] [raison]` - Expulse un membre
- `!ban [@membre] [raison]` - Bannit un membre
- `!unban [ID] [raison]` - Débannit un utilisateur
- `!mute [@membre] [raison]` - Rend muet un membre
- `!unmute [@membre] [raison]` - Retire le mute d'un membre
- `!warnings [@membre]` - Affiche les avertissements d'un membre
- `!clearwarnings [@membre]` - Supprime les avertissements d'un membre
- `!addwarning [@membre] [raison]` - Ajoute un avertissement à un membre

### Gestion des rôles
- `!add_role_menu` - Crée un menu de sélection de rôles
- `!exemption_channel [#salon]` - Exempte un salon de la vérification anti-liens
- `!unexempt_channel [#salon]` - Retire l'exemption d'un salon

### Musique
- `!create_music_channels` - Crée 5 salons vocaux dédiés à la musique
- `!join` - Rejoint ton salon vocal
- `!play [lien/recherche]` - Joue une musique depuis YouTube
- `!pause` - Met en pause la musique
- `!resume` - Reprend la lecture
- `!skip` - Passe à la musique suivante
- `!stop` - Arrête la musique et vide la queue
- `!queue` - Affiche la file d'attente
- `!volume [0-100]` - Ajuste le volume

### TikTok
- `!set_tiktok [@membre]` - Connecte un membre aux notifications TikTok
- `!remove_tiktok [@membre]` - Retire les notifications TikTok d'un membre
- `!list_tiktok` - Liste tous les comptes TikTok enregistrés
- `!check_tiktok_now` - Force une vérification immédiate des updates TikTok
- `!set_tiktok_interval [minutes]` - Définit l'intervalle de vérification
- `!create_tiktok_channel` - Crée un canal dédié aux notifications TikTok

### Emoji
- `!add_emojis [anime/basic/all] [nombre]` - Ajoute des emojis au serveur
- `!list_emojis` - Liste tous les emojis du serveur
- `!emoji_limits` - Affiche les limites d'emojis du serveur

### Tickets
- `!setup_tickets` - Configure le système de tickets
- `!reset_tickets` - Réinitialise le système de tickets
- `!add_to_ticket [@membre]` - Ajoute un utilisateur à un ticket
- `!remove_from_ticket [@membre]` - Retire un utilisateur d'un ticket

### Divers
- `!help` - Affiche l'aide du bot
- `!info` - Affiche des informations sur le bot
- `!serverinfo` - Affiche des informations sur le serveur
- `!ask [question]` - Pose une question à ChatGPT
- `!setup_logs` - Configure un système de logs avancé
- `!create_stats_channels` - Crée les canaux de statistiques
- `!delete_stats_channels` - Supprime les canaux de statistiques
- `!reload_cogs` - Recharge tous les modules du bot (admin)

## Environnement requis

- Python 3.8+
- discord.py 2.0+

## Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-compte/ninis-bot.git
cd ninis-bot

# Installer les dépendances
pip install discord.py flask gunicorn

# Configurer le token
# Option 1: Variable d'environnement
export DISCORD_TOKEN=votre_token_ici

# Option 2: Modifier config.py
# Ouvrez config.py et modifiez la ligne TOKEN = "YOUR_TOKEN_HERE"

# Lancer le bot
python main.py
```

## Maintenir le Bot en ligne 24/7 avec Replit et UptimeRobot

Le Bot Chii utilise une configuration spéciale pour rester en ligne 24/7 sur Replit :

1. **Configuration sur Replit**
   - Le bot utilise deux workflows qui fonctionnent ensemble :
     - `default` : Lance le bot Discord avec `python main.py`
     - `Start application` : Lance le serveur web avec `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`
   - Ces deux workflows doivent toujours être activés

2. **Configuration d'UptimeRobot**
   - Créez un compte sur [UptimeRobot](https://uptimerobot.com/)
   - Ajoutez un nouveau moniteur de type "HTTP(S)"
   - Utilisez l'URL suivante comme URL à surveiller :
     ```
     https://fe3bf4a2-22cb-4075-ab1b-0dc69518bb1e-00-3aanjmc9p1ffc.kirk.replit.dev
     ```
   - Réglez l'intervalle de vérification sur 5 minutes
   - Activez les alertes par e-mail en cas de panne

3. **Vérification du bon fonctionnement**
   - Visitez l'URL ci-dessus pour voir l'état du bot
   - Vérifiez que le statut affiche "En ligne" avec un temps d'activité croissant
   - Consultez votre tableau de bord UptimeRobot pour confirmer que les pings sont réussis (200 OK)

Cette configuration permet au bot de rester en ligne même lorsque l'onglet Replit est fermé. UptimeRobot envoie des requêtes HTTP régulières qui empêchent le projet Replit de s'endormir.
