# Guide de configuration UptimeRobot pour le Bot Chii

Ce guide vous aide à configurer [UptimeRobot](https://uptimerobot.com) pour maintenir votre bot Discord en ligne 24h/24.

## Pourquoi utiliser UptimeRobot ?

Replit met les projets en veille après une période d'inactivité. UptimeRobot permet de "ping" régulièrement votre bot pour qu'il reste actif constamment.

## Étapes de configuration

### 1. Créer un compte UptimeRobot

- Visitez [uptimerobot.com](https://uptimerobot.com) et créez un compte gratuit

### 2. Ajouter un nouveau moniteur

1. Cliquez sur "**+ Add New Monitor**"
2. Sélectionnez le type "**HTTP(s)**"
3. Donnez un nom comme "**Bot Chii**"
4. Dans le champ URL, entrez l'URL de votre repl:
   ```
   https://fe3bf4a2-22cb-4075-ab1b-0dc69518bb1e-00-3aanjmc9p1ffc.kirk.replit.dev
   ```
5. Définissez l'intervalle de monitoring à "**Every 5 minutes**"
6. Cliquez sur "**Create Monitor**"

### 3. Ajouter un second moniteur (recommandé)

Pour plus de fiabilité, créez un deuxième moniteur qui utilise le point de terminaison de vérification de santé:

1. Cliquez à nouveau sur "**+ Add New Monitor**"
2. Donnez un nom comme "**Bot Chii Health Check**"
3. Dans le champ URL, entrez l'URL de vérification avec `/external-health-check`:
   ```
   https://fe3bf4a2-22cb-4075-ab1b-0dc69518bb1e-00-3aanjmc9p1ffc.kirk.replit.dev/external-health-check
   ```
4. Définissez aussi l'intervalle à "**Every 5 minutes**"
5. Cliquez sur "**Create Monitor**"

## Points de terminaison disponibles

Le Bot Chii offre plusieurs points de terminaison pour le monitoring:

- `/` - Page d'accueil avec informations visuelles sur l'état du bot
- `/ping` - Réponse simple "pong" pour vérifier la disponibilité
- `/health` - Données détaillées au format JSON sur l'état du système
- `/external-health-check` - Point de terminaison spécial pour UptimeRobot qui vérifie et redémarre le bot si nécessaire

## Résolution de problèmes

Si UptimeRobot ne parvient pas à ping votre bot:

1. **Vérifiez l'URL**: Assurez-vous d'utiliser l'URL correcte au format `replit.dev`
2. **Vérifiez que le bot est démarré**: Le workflow "Start application" doit être en cours d'exécution
3. **Redémarrez les deux workflows**: "Start application" pour le serveur web et "default" pour le bot Discord
4. **Vérifiez les ports**: Assurez-vous que le port 5000 est bien exposé et accessible

## Conseils supplémentaires

- Activez les notifications par email dans UptimeRobot pour être averti si votre bot tombe hors ligne
- Le plan gratuit d'UptimeRobot vous permet de surveiller jusqu'à 50 moniteurs avec un intervalle minimum de 5 minutes
- Pour une meilleure fiabilité, surveillez à la fois l'URL racine et l'endpoint `/external-health-check`

---

En suivant ces étapes, votre Bot Chii devrait rester en ligne en permanence. Le système de keep-alive amélioré inclut non seulement le ping d'UptimeRobot, mais aussi une vérification de santé et un redémarrage automatique en cas de problème.