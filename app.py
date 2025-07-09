"""
App Flask pour exposer un point de terminaison d'état du Bot Chii.
Ce serveur est utilisé par UptimeRobot pour s'assurer que le bot reste en ligne.
Il utilise l'application de keep_alive.py pour garantir la cohérence.
"""

import os
import signal
import sys
import psutil
import logging
import time
import json
from flask import Flask, jsonify, render_template_string
from datetime import datetime

# Configuration du logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('app')

app = Flask(__name__)

# Variables globales
server_start_time = time.time()

@app.route('/')
def home():
    """Affiche la page d'accueil"""
    uptime = int(time.time() - server_start_time)
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    # Récupérer les métriques système
    metrics = {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used": round(psutil.virtual_memory().used / (1024 * 1024), 2)  # En MB
    }
    
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
            <h1>Bot Chii <span class="status online">En ligne</span></h1>
            
            <p>Le bot Discord <strong>Chii</strong> est disponible pour surveillance. 
               Ce serveur est utilisé par UptimeRobot pour maintenir le bot actif 24h/24.</p>
            
            <div class="metrics">
                <div class="metric-card">
                    <h3>Temps de fonctionnement</h3>
                    <div class="metric-value">{{ days }}j {{ hours }}h {{ minutes }}m {{ seconds }}s</div>
                    <p>Depuis le dernier démarrage</p>
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
                
                <div class="metric-card">
                    <h3>Statut</h3>
                    <div class="metric-value">200 OK</div>
                    <p>Serveur web actif</p>
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
    metrics = {
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used": round(psutil.virtual_memory().used / (1024 * 1024), 2)  # En MB
    }
    
    # Calcul de l'uptime
    uptime = int(time.time() - server_start_time)
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    uptime_format = f"{days}j {hours}h {minutes}m {seconds}s"
    
    health_data = {
        "status": "online",
        "uptime": uptime_format,
        "system": {
            "cpu_percent": metrics["cpu_percent"],
            "memory_percent": metrics["memory_percent"],
            "memory_used_mb": metrics["memory_used"]
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
    # Vérifier si le processus du bot est en cours d'exécution
    bot_running = False
    for process in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in process.info['name'] and 'main.py' in ' '.join(process.info['cmdline'] or []):
                bot_running = True
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if not bot_running:
        logger.warning("Le bot n'est pas en cours d'exécution, tentative de redémarrage...")
        try:
            # Redémarrer le bot en arrière-plan
            import subprocess
            subprocess.Popen([sys.executable, "restart_bot.py"])
            return jsonify({"status": "restarting", "message": "Bot redémarré"}), 503
        except Exception as e:
            logger.error(f"Erreur lors du redémarrage du bot: {str(e)}")
            return jsonify({"status": "error", "message": f"Erreur de redémarrage: {str(e)}"}), 500
    
    return jsonify({"status": "online", "message": "Bot Chii est en ligne"})

def signal_handler(sig, frame):
    """Gestionnaire pour arrêter proprement le serveur"""
    logger.info("Signal reçu, arrêt du serveur...")
    sys.exit(0)

if __name__ == "__main__":
    # Configurer les gestionnaires de signaux
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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
    
    if replit_url:
        logger.info(f"URL pour UptimeRobot: {replit_url}")
        logger.info("💡 CONSEIL: Utilisez cette URL exacte dans UptimeRobot.")
        logger.info("💡 CONSEIL: Configurez UptimeRobot pour faire un ping toutes les 5 minutes.")
    
    # Démarrer le serveur Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)