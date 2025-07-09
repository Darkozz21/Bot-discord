"""
Système keep-alive amélioré pour le Bot Chii.
Ce module maintient le bot en ligne 24h/24 grâce à:
- Un serveur Flask qui répond aux pings d'UptimeRobot
- Des URLs publiques clairement affichées dans la console
- Un système de vérification de santé pour surveiller le bot
"""

import os
import time
import logging
import threading
import signal
import sys
import json
import psutil
import subprocess
from datetime import datetime
from threading import Thread
from flask import Flask, jsonify, render_template_string

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('keep_alive')

# Variables globales
restart_count = 0
last_restart_time = None
health_check_active = False
health_check_thread = None
restart_stats = {"total_restarts": 0, "last_restart": None, "restart_history": []}
server_start_time = time.time()
bot_process = None

# Création de l'application Flask
app = Flask('')

@app.route('/')
def home():
    """Affiche une page de statut améliorée avec métriques en temps réel"""
    uptime = int(time.time() - server_start_time)
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Récupérer les métriques système
    metrics = measure_system_metrics()
    
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bot Chii - Statut</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: 'Arial', sans-serif;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                margin: 0;
                padding: 20px;
                color: #333;
                line-height: 1.6;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                padding: 20px;
            }
            h1 {
                color: #ff69b4;
                text-align: center;
                margin-bottom: 20px;
                border-bottom: 2px solid #eee;
                padding-bottom: 10px;
            }
            .status {
                display: inline-block;
                padding: 8px 15px;
                border-radius: 20px;
                font-weight: bold;
                margin-left: 10px;
            }
            .online {
                background-color: #d4edda;
                color: #155724;
            }
            .offline {
                background-color: #f8d7da;
                color: #721c24;
            }
            .metrics {
                display: flex;
                flex-wrap: wrap;
                justify-content: space-between;
                margin: 20px 0;
            }
            .metric-card {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                width: 48%;
                margin-bottom: 15px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #6c757d;
                margin: 10px 0;
            }
            .footer {
                text-align: center;
                margin-top: 20px;
                font-size: 12px;
                color: #6c757d;
            }
            @media (max-width: 600px) {
                .metric-card {
                    width: 100%;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Bot Chii <span class="status {{ 'online' if is_running else 'offline' }}">{{ 'En ligne' if is_running else 'Hors ligne' }}</span></h1>
            
            <p>Le bot Discord <strong>Chii</strong> est actuellement {{ 'actif' if is_running else 'inactif' }}. 
               Ce serveur gère les vérifications de santé et permet la surveillance par UptimeRobot.</p>
            
            <div class="metrics">
                <div class="metric-card">
                    <h3>Temps de fonctionnement</h3>
                    <div class="metric-value">{{ days }}j {{ hours }}h {{ minutes }}m {{ seconds }}s</div>
                    <p>Depuis le dernier démarrage</p>
                </div>
                
                <div class="metric-card">
                    <h3>Redémarrages</h3>
                    <div class="metric-value">{{ restart_count }}</div>
                    <p>{{ last_restart_time if last_restart_time else 'Aucun redémarrage récent' }}</p>
                </div>
                
                <div class="metric-card">
                    <h3>CPU</h3>
                    <div class="metric-value">{{ metrics['cpu_percent'] }}%</div>
                    <p>Utilisation du processeur</p>
                </div>
                
                <div class="metric-card">
                    <h3>Mémoire</h3>
                    <div class="metric-value">{{ metrics['memory_percent'] }}%</div>
                    <p>{{ metrics['memory_used'] }} Mo utilisés</p>
                </div>
            </div>
            
            <h3>Points de terminaison disponibles:</h3>
            <ul>
                <li><code>/</code> - Cette page</li>
                <li><code>/health</code> - Informations détaillées sur la santé du système (JSON)</li>
                <li><code>/ping</code> - Vérification simple de disponibilité</li>
                <li><code>/external-health-check</code> - Point de terminaison pour UptimeRobot</li>
            </ul>
            
            <div class="footer">
                <p>Bot Chii v1.0 | Mis à jour le {{ current_date }}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(
        html_template,
        is_running=is_bot_running(),
        restart_count=restart_stats["total_restarts"],
        last_restart_time=restart_stats["last_restart"],
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds,
        metrics=metrics,
        current_date=datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    )

@app.route('/health')
def health_check():
    """Endpoint JSON pour le monitoring de santé"""
    metrics = measure_system_metrics()
    
    # Calcul de l'uptime
    uptime = int(time.time() - server_start_time)
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_format = f"{days}j {hours}h {minutes}m {seconds}s"
    
    health_data = {
        "status": "online" if is_bot_running() else "offline",
        "uptime": uptime_format,
        "restart_count": restart_stats["total_restarts"],
        "last_restart": restart_stats["last_restart"],
        "system": {
            "cpu_percent": metrics["cpu_percent"],
            "memory_percent": metrics["memory_percent"],
            "memory_used_mb": metrics["memory_used"]
        },
        "ping": {
            "response_time_ms": measure_ping(),
        },
        "timestamp": datetime.now().isoformat()
    }
    
    return jsonify(health_data)

@app.route('/ping')
def ping():
    """Endpoint simple pour vérifier que le serveur répond"""
    return "pong"

@app.route('/external-health-check')
def external_health_check():
    """
    Point de terminaison dédié aux outils de surveillance externes comme UptimeRobot.
    Vérifie activement si le bot fonctionne et redémarre si nécessaire.
    """
    if not is_bot_running():
        logger.warning("Le bot n'est pas en cours d'exécution, tentative de redémarrage...")
        restart_bot()
        return jsonify({"status": "restarting", "message": "Bot redémarré"}), 503
    
    return jsonify({"status": "online", "message": "Bot Chii est en ligne"})

def run():
    """Exécute le serveur Flask avec gestion intelligente des ports"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def is_bot_running():
    """Vérifie si le processus du bot est en cours d'exécution"""
    try:
        # Vérifie si le thread principal du bot est actif
        for thread in threading.enumerate():
            if thread.name == "MainThread" and thread != threading.current_thread():
                return True
        return False
    except:
        return False

def measure_system_metrics():
    """Mesure les métriques système actuelles"""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used = round(memory.used / (1024 * 1024), 2)  # En MB
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_used": memory_used
        }
    except:
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "memory_used": 0
        }

def measure_ping():
    """Mesure le temps de réponse du bot pour les pings internes"""
    try:
        start_time = time.time()
        is_bot_running()  # Fonction simple pour vérifier le bot
        end_time = time.time()
        
        # Convertir en millisecondes
        response_time = round((end_time - start_time) * 1000, 2)
        return response_time
    except:
        return 999  # Valeur par défaut en cas d'erreur

def restart_bot():
    """Redémarre le bot en cas de problème détecté"""
    global restart_count, last_restart_time
    
    try:
        logger.info("Redémarrage du bot...")
        record_restart()
        
        # Utiliser le script dédié de redémarrage
        create_restart_script()
        subprocess.Popen([sys.executable, "restart_bot.py"])
        
        restart_count += 1
        last_restart_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors du redémarrage du bot: {str(e)}")
        return False

def health_check_loop():
    """Boucle de vérification de santé qui s'exécute en arrière-plan"""
    global health_check_active
    
    logger.info("Thread de vérification de santé démarré")
    
    while health_check_active:
        if not is_bot_running():
            logger.warning("Bot inactif détecté dans la vérification périodique")
            restart_bot()
        
        # Pause entre les vérifications
        time.sleep(60)  # Vérification toutes les minutes

def record_restart():
    """Enregistre un redémarrage du bot avec plus d'informations."""
    global restart_stats
    
    current_time = datetime.now().isoformat()
    
    # Mettre à jour les statistiques
    restart_stats["total_restarts"] += 1
    restart_stats["last_restart"] = current_time
    
    # Ajouter l'historique (limité aux 10 derniers redémarrages)
    restart_info = {
        "timestamp": current_time,
        "reason": "health_check"
    }
    
    restart_stats["restart_history"].append(restart_info)
    if len(restart_stats["restart_history"]) > 10:
        restart_stats["restart_history"] = restart_stats["restart_history"][-10:]
    
    # Enregistrer dans un fichier (optionnel)
    try:
        with open('restart_stats.json', 'w') as f:
            json.dump(restart_stats, f)
    except:
        pass

def create_restart_script():
    """Crée un script python simple pour redémarrer le bot."""
    with open('restart_bot.py', 'w') as f:
        f.write("""
import os
import time
import psutil
import sys

def kill_process_by_name(name):
    # Recherche et tue tous les processus python en cours d'exécution
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Si c'est un processus python mais pas le script restart lui-même
            if proc.info['name'] == name and 'restart_bot.py' not in ' '.join(proc.info['cmdline']):
                proc.kill()
                print(f"Processus {name} (PID: {proc.info['pid']}) terminé")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

# Arrêter le bot actuel
kill_process_by_name('python')
kill_process_by_name('python3')

# Attendre un peu
time.sleep(2)

# Redémarrer le bot
os.system('python main.py &')
""")

def load_restart_stats():
    """Charge les statistiques de redémarrage depuis le fichier."""
    global restart_stats
    
    try:
        if os.path.exists('restart_stats.json'):
            with open('restart_stats.json', 'r') as f:
                restart_stats = json.load(f)
    except:
        # En cas d'erreur, conserver les valeurs par défaut
        pass

def start_health_check():
    """Démarre le thread de vérification de santé."""
    global health_check_active, health_check_thread
    
    if not health_check_active:
        health_check_active = True
        health_check_thread = Thread(target=health_check_loop)
        health_check_thread.daemon = True
        health_check_thread.start()

def stop_health_check():
    """Arrête le thread de vérification de santé."""
    global health_check_active
    
    if health_check_active:
        health_check_active = False
        if health_check_thread:
            health_check_thread.join(timeout=2)

def setup_signal_handlers():
    """Configure les gestionnaires de signaux pour un arrêt propre."""
    def signal_handler(sig, frame):
        logger.info("Signal d'arrêt reçu, nettoyage...")
        stop_health_check()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def keep_alive():
    """Fonction principale qui initialise et démarre le système keep-alive amélioré"""
    global server_start_time
    
    logger.info("Initialisation du système keep-alive...")
    
    # Charger les statistiques de redémarrage
    load_restart_stats()
    
    # Créer le script de redémarrage
    create_restart_script()
    logger.info("Script de redémarrage créé avec succès")
    
    # Afficher l'URL pour UptimeRobot basée sur REPLIT_DOMAINS
    replit_url = None
    if "REPLIT_DOMAINS" in os.environ:
        domains = os.environ["REPLIT_DOMAINS"].split(",")
        if domains:
            replit_url = f"https://{domains[0]}"
    elif "REPL_ID" in os.environ and "REPL_SLUG" in os.environ:
        # Fallback en utilisant REPL_ID et REPL_SLUG
        repl_id = os.environ["REPL_ID"]
        repl_slug = os.environ["REPL_SLUG"]
        replit_url = f"https://{repl_slug}.{repl_id}.repl.co"
    
    # Port du serveur
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Démarrage du serveur de keep-alive sur le port {port}")
    
    # Configurer les gestionnaires de signaux
    setup_signal_handlers()
    
    # Démarrer le thread de vérification de santé
    start_health_check()
    
    # Démarrer le serveur
    server_thread = Thread(target=run)
    server_thread.daemon = True
    server_thread.start()
    
    logger.info("Système keep-alive démarré avec succès!")
    
    if replit_url:
        logger.info(f"URL pour UptimeRobot: {replit_url}")
        logger.info("💡 CONSEIL: Utilisez cette URL exacte dans UptimeRobot.")
        logger.info("💡 CONSEIL: Configurez UptimeRobot pour faire un ping toutes les 5 minutes. Utilisez le type HTTP(S).")
        logger.info("💡 CONSEIL: Vérifiez que vos statistiques UptimeRobot montrent des pings réussis (200 OK).")