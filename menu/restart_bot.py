
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
