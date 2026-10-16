#!/usr/bin/env bash
# Atualiza UMA instância para a versão mais nova do repositório.
# Onde roda: vm-app1 / vm-app2, como usuário deploy. Normalmente é chamado
# pelo deploy.sh (na vm-proxy) via SSH, uma instância por vez.
#
# Uso: /srv/etermory/scripts/atualizar_instancia.sh [branch] [migrar: 0|1]
#
# Se a instância não responder depois de atualizar, volta para a versão
# anterior (rollback).
#
# Códigos de saída:
#   0 = atualizada e saudável
#   2 = falha no git ou no pip
#   3 = falha na migração do banco
#   4 = não subiu; rollback feito (instância de volta na versão anterior)
#   5 = não subiu e o rollback também falhou
set -euo pipefail
# shellcheck source=SCRIPTDIR/lib.sh
source "$(dirname "$(readlink -f "$0")")/lib.sh"
ARQUIVO_LOG="${PASTA_LOG}/deploy.log"

BRANCH="${1:-main}"
MIGRAR="${2:-0}"
PASTA="/srv/etermory"
SAUDE="http://127.0.0.1:8000/saude"

cd "$PASTA"
anterior=$(git rev-parse HEAD)
log INFO "$(hostname): versão atual ${anterior:0:8}; buscando ${BRANCH}"

git fetch --prune origin || falhar 2 "git fetch falhou"
git reset --hard "origin/${BRANCH}" || falhar 2 "git reset falhou"
nova=$(git rev-parse HEAD)
chmod 750 scripts/*.sh

.venv/bin/pip install --quiet -r requirements.txt || falhar 2 "pip install falhou"

if [[ "$MIGRAR" == "1" ]]; then
    .venv/bin/flask --app wsgi db upgrade || falhar 3 "migração falhou"
    log INFO "Migrações aplicadas"
fi

sudo systemctl restart etermory
if esperar_saude "$SAUDE" 30; then
    log INFO "$(hostname): ${anterior:0:8} -> ${nova:0:8} no ar"
    exit 0
fi

log ERRO "$(hostname) não respondeu em 30s; voltando para ${anterior:0:8}"
git reset --hard "$anterior"
.venv/bin/pip install --quiet -r requirements.txt
sudo systemctl restart etermory
if esperar_saude "$SAUDE" 30; then
    falhar 4 "rollback concluído; $(hostname) segue na versão ${anterior:0:8}"
fi
falhar 5 "rollback também falhou em $(hostname): veja journalctl -u etermory"
