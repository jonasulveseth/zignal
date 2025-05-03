web: cd zignal && gunicorn zignal.config.wsgi --log-file -
worker: cd zignal && celery -A zignal.config worker --without-gossip --without-mingle --loglevel=info 