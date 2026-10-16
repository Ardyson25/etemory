#!/usr/bin/env bash
# Verifica a saúde de cada instância e do site pelo Nginx.
# Onde roda: vm-proxy (timer a cada minuto e à mão durante o teste de failover).
#
# Códigos de saída:
#   0 = tudo no ar
#   1 = site no ar, mas alguma instância fora (degradado: o failover está agindo)
#   2 = site fora do ar
set -euo pipefail
# shellcheck source=SCRIPTDIR/lib.sh
source "$(dirname "$(readlink -f "$0")")/lib.sh"
ARQUIVO_LOG="${PASTA_LOG}/healthcheck.log"

INSTANCIAS=("vm-app1:8000" "vm-app2:8000")
URL_SITE="https://127.0.0.1/saude"

fora=0
for instancia in "${INSTANCIAS[@]}"; do
    if resposta=$(curl -fsS -m 3 "http://${instancia}/saude" 2>&1); then
        log OK "${instancia} -> ${resposta//[$'\n ']/}"
    else
        log FALHA "${instancia} não respondeu: ${resposta}"
        fora=$((fora + 1))
    fi
done

if resposta=$(curl -kfsS -m 5 "$URL_SITE" 2>&1); then
    log OK "site (Nginx) -> ${resposta//[$'\n ']/}"
else
    falhar 2 "site fora do ar pelo Nginx: ${resposta}"
fi

if (( fora > 0 )); then
    log AVISO "${fora} instância(s) fora; o site segue no ar pela outra."
    exit 1
fi
exit 0
