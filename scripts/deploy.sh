#!/usr/bin/env bash
# Deploy sem tirar o site do ar: atualiza uma instância por vez.
# Onde roda: vm-proxy, como usuário deploy. É chamado automaticamente pelo
# hook post-receive quando alguém faz "git push producao main", ou à mão:
#   /usr/local/bin/etermory-deploy main
#
# Enquanto a app1 reinicia, o Nginx manda todos os pedidos para a app2
# (failover); depois o mesmo acontece ao contrário.
#
# Códigos de saída:
#   0 = as duas instâncias atualizadas
#   2 = a app1 falhou: nada mudou na app2 (o site segue no ar pela app2)
#   3 = a app2 falhou depois da app1 ter sido atualizada (versões diferentes)
#   4 = o site não responde pelo Nginx no fim
set -euo pipefail
# shellcheck source=SCRIPTDIR/lib.sh
source "$(dirname "$(readlink -f "$0")")/lib.sh"
ARQUIVO_LOG="${PASTA_LOG}/deploy.log"

BRANCH="${1:-main}"
SCRIPT_REMOTO="/srv/etermory/scripts/atualizar_instancia.sh"
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new)

inicio=$(date +%s)
log INFO "=== Deploy da branch ${BRANCH} iniciado por ${SUDO_USER:-$USER} ==="

# 1ª instância: aplica as migrações (as duas usam o mesmo banco).
# As migrações precisam ser compatíveis com a versão antiga, que segue
# rodando na app2 até o passo seguinte.
log INFO "[1/2] vm-app1 (com migrações)"
"${SSH[@]}" deploy@vm-app1 "$SCRIPT_REMOTO $BRANCH 1" \
    || falhar 2 "vm-app1 falhou; vm-app2 não foi tocada e o site segue no ar por ela"

log INFO "[2/2] vm-app2"
"${SSH[@]}" deploy@vm-app2 "$SCRIPT_REMOTO $BRANCH 0" \
    || falhar 3 "vm-app2 falhou; vm-app1 já está na versão nova. Corrija e rode de novo."

curl -kfsS -m 5 https://127.0.0.1/saude | grep -q '"status": *"ok"' \
    || falhar 4 "o site não responde pelo Nginx"

log INFO "=== Deploy concluído em $(( $(date +%s) - inicio ))s ==="
