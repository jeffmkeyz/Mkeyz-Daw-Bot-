web: gunicorn server:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 60 --log-level warning
worker: python bot.py
