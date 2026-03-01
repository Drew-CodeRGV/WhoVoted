import multiprocessing

bind = '127.0.0.1:5000'
workers = 5
worker_class = 'sync'
timeout = 3600  # 1 hour - processing large files can take a while
graceful_timeout = 120
accesslog = '/opt/whovoted/logs/gunicorn-access.log'
errorlog = '/opt/whovoted/logs/gunicorn-error.log'
loglevel = 'info'
