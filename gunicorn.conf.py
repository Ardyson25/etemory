"""Configuração do Gunicorn (servidor WSGI de produção).

Usada no Render (Fase 3) e nas VMs app1/app2 (Fase 4):
    gunicorn -c gunicorn.conf.py wsgi:app

Os valores vêm de variáveis de ambiente para a mesma configuração servir
nos dois lugares.
"""

import os

# O Render informa a porta em PORT; nas VMs usamos 8000 (liberada só ao Nginx).
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# Processos de trabalho. Regra comum: (2 x núcleos) + 1. O plano gratuito do
# Render tem 512 MB de RAM, por isso o padrão é 2.
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
worker_class = "sync"

# Um pedido que demore mais que isso é abortado e o worker é reiniciado.
timeout = 60
graceful_timeout = 20  # tempo para terminar pedidos ao receber SIGTERM
keepalive = 5

# Reinicia cada worker depois de N pedidos (evita vazamento de memória).
max_requests = 1000
max_requests_jitter = 100

# Logs na saída padrão: o Render e o journald (systemd) capturam.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# IPs do proxy em que o Gunicorn confia para os cabeçalhos X-Forwarded-*.
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")

proc_name = f"etermory-{os.environ.get('INSTANCIA', 'local')}"
