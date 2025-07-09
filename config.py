"""
Configuration file for the Ninis discord bot.
"""

# Bot configuration
VERSION = "1.0.0"
PREFIX = "!"
TOKEN = ""  # Prefer using environment variable DISCORD_TOKEN

# Message de règlement
RULES_MESSAGE_ID = None  # Sera mis à jour dynamiquement
RULES_CHANNEL_ID = None  # Sera mis à jour dynamiquement
RULES_EMOJI = "✅"

# List of cogs to load
COGS = [
    "setup",
    "moderation",
    "utils",
    "tiktok",
    "music",
    "roles",
    "emoji",
    "tickets",
    "logging",
    "chatgpt",
    "antilink",
    "giveaway",
    "daily_question",
    "levels",
    "invites"
]

# Server configuration
ROLES = {
    "Owner": {"color": 0xF1C40F, "permissions": True},  # Gold, owner
    "✦ ꒰ Nini Queen ꒱": {"color": 0xFFC0CB, "permissions": True},  # Pink, admin
    "Administrateur": {"color": 0xE74C3C, "permissions": True},  # Red, admin
    "Modérateur": {"color": 0x9B59B6, "permissions": True},  # Purple, moderator
    "Non vérifié": {"color": 0x95A5A6, "permissions": False},  # Gris, rôle par défaut pour les nouveaux membres
    "Membre": {"color": 0x3498DB, "permissions": False},  # Bleu, rôle après acceptation du règlement
    
    # Rôles de niveaux XP (du plus bas au plus élevé)
    "Nini Nouveau": {"color": 0xAED6F1, "permissions": False},  # Bleu clair (niveau 1)
    "Nini Curieux": {"color": 0x85C1E9, "permissions": False},  # Bleu moyen (niveau 5)
    "Nini Actif": {"color": 0x5DADE2, "permissions": False},    # Bleu foncé (niveau 10)
    "Nini Confirmé": {"color": 0x3498DB, "permissions": False}, # Bleu royal (niveau 20)
    "Nini Légende": {"color": 0x2874A6, "permissions": False}   # Bleu profond (niveau 30)
}

# Simplified roles configuration for setup_basic_roles command
BASIC_ROLES = {
    "Owner": {"color": 0xF1C40F, "permissions": True, "hoist": True, "mentionable": True},  # Gold, owner
    "✦ ꒰ Nini Queen ꒱": {"color": 0xFFC0CB, "permissions": True, "hoist": True, "mentionable": True},  # Pink, admin
    "Administrateur": {"color": 0xE74C3C, "permissions": True, "hoist": True, "mentionable": True},  # Red, admin
    "Modérateur": {"color": 0x9B59B6, "permissions": True, "hoist": True, "mentionable": True},  # Purple, moderator
    "Membre": {"color": 0x3498DB, "permissions": False, "hoist": True, "mentionable": False},  # Bleu, rôle après acceptation du règlement
    
    # Rôles de niveaux XP (du plus bas au plus élevé)
    "Nini Nouveau": {"color": 0xAED6F1, "permissions": False, "hoist": True, "mentionable": False},  # Bleu clair (niveau 1)
    "Nini Curieux": {"color": 0x85C1E9, "permissions": False, "hoist": True, "mentionable": False},  # Bleu moyen (niveau 5)
    "Nini Actif": {"color": 0x5DADE2, "permissions": False, "hoist": True, "mentionable": False},    # Bleu foncé (niveau 10)
    "Nini Confirmé": {"color": 0x3498DB, "permissions": False, "hoist": True, "mentionable": False}, # Bleu royal (niveau 20)
    "Nini Légende": {"color": 0x2874A6, "permissions": False, "hoist": True, "mentionable": False}   # Bleu profond (niveau 30)
}

# Channel structure
CHANNELS = {
    "୨୧・Bienvenue": {
        "📌・bienvenue": {
            "type": "text",
            "content": "♡ Bienvenue sur ୨୧﹒Ninis !\n\nUn petit coin chill, cute et bienveillant.\nIci on papote, on partage, on crée et on se détend.\nMerci de lire le #📖・règlement et de choisir tes rôles dans #✨・rôles."
        },
        "📖・règlement": {
            "type": "text",
            "content": "୨୧﹒RÈGLEMENT﹒୨୧\n1. Sois respectueux.se avec tout le monde.\n2. Pas de spam, pub ou flood.\n3. Aucun contenu choquant ou NSFW.\n4. Pseudos et photos doivent rester corrects.\n5. Pas d'auto-promo sans autorisation.\n6. Pour tout souci, contacte un membre du staff."
        },
        "✨・rôles": {
            "type": "text",
            "content": "Choisis ton rôle avec les réactions :\n🌸 Créatif.ve\n✨ Gamer\n☁ Chillax\n⋆ Baby Nini"
        },
        "📣・annonces": {
            "type": "text",
            "content": "Les annonces officielles du serveur seront postées ici."
        },
        "📱・notifications-tiktok": {
            "type": "text",
            "content": "Ce salon affichera automatiquement des notifications pour les nouveaux lives et vidéos TikTok des membres."
        }
    },
    "୨୧・Chat": {
        "💬・discussion-générale": {
            "type": "text",
            "content": "Bienvenue dans le chat principal de Ninis ! Papote librement ici."
        },
        "🌈・flood-zone": {
            "type": "text",
            "content": "Tu peux spammer, rigoler, tout casser ici — no stress !"
        },
        "📷・selfies": {
            "type": "text",
            "content": "Montre-nous ta belle tête, tes tenues ou tes vibes du jour !"
        },
        "☁️・humeurs-du-jour": {
            "type": "text",
            "content": "Tu veux partager comment tu te sens aujourd'hui ? Ce salon est fait pour ça."
        }
    },
    "୨୧・Créativité": {
        "🎨・créations-membres": {"type": "text"},
        "🎶・playlists": {"type": "text"},
        "🧸・déco-inspi": {"type": "text"},
        "📓・journaling": {"type": "text"}
    },
    "୨୧・Jeux & Fun": {
        "🎲・jeux-bots": {"type": "text"},
        "🎀・mini-défis": {"type": "text"},
        "❓・question-du-jour": {"type": "text"},
        "🤖・commande-bot": {
            "type": "text",
            "content": "Utilise ici les commandes pour le bot et consulte ton niveau avec !rank"
        }
    },
    "୨୧・Vocal": {
        "♡・papotage": {"type": "voice"},
        "☕・chill zone": {"type": "voice"},
        "🎧・musique": {"type": "voice"},
        "🎮・gaming": {"type": "voice"}
    },
    "୨୧・Staff": {
        "🔒・staff-chat": {"type": "text"},
        "📁・mod-log": {"type": "text"},
        "💡・idées-du-staff": {"type": "text"}
    }
}

# Welcome message template
WELCOME_MESSAGE = """
✨ Bienvenue {member.mention} sur le serveur **{guild.name}** ! ✨

💖 Nous sommes maintenant {member_count} membres !
"""

# Leave message template
LEAVE_MESSAGE = """
😢 **{member.name}** vient de quitter le serveur.

Nous sommes maintenant {member_count} membres.
"""
