"""
Script Flask pour exposer l'application Flask pour Gunicorn.
Ce fichier importe simplement l'app de app.py.
"""

from app import app

# Cette variable sera utilisée par Gunicorn
app = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)