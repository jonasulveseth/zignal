web: cd zignal && daphne -b 0.0.0.0 -p $PORT zignal.config.asgi:application
worker: cd zignal && celery -A zignal.config worker --without-gossip --without-mingle --loglevel=info 