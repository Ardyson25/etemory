#!/usr/bin/env bash
# Conduz o teste de indisponibilidade da Fase 5 e registra horário de cada
# passo. Enquanto você executa os passos (em outros terminais), o
# teste_failover.sh fica medindo o site em segundo plano.
#
# Onde roda: no computador hospedeiro (Git Bash) ou na vm-proxy.
# Uso: ./teste_indisponibilidade.sh [url]
# Saída: docs/evidencias/teste_indisponibilidade/<data>/ (passos.log e failover.log)
set -euo pipefail

URL="${1:-http://192.168.56.10/saude}"
PASTA_SCRIPT="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PASTA="${PASTA_SCRIPT}/../docs/evidencias/teste_indisponibilidade/$(date +%Y-%m-%d_%H%M)"
mkdir -p "$PASTA"
PASSOS="${PASTA}/passos.log"
FAILOVER="${PASTA}/failover.log"

registrar() {
    echo "$(date '+%Y-%m-%d %H:%M:%S.%3N')  $*" | tee -a "$PASSOS"
}

passo() {
    local titulo="$1"; shift
    echo
    echo "=================================================================="
    echo " ${titulo}"
    echo "=================================================================="
    for linha in "$@"; do echo "   $linha"; done
    read -r -p "   Pressione Enter quando TERMINAR este passo... " _
    registrar "FIM: ${titulo}"
}

# Mede o site durante todo o teste (até 1 hora; é encerrado no fim).
bash "${PASTA_SCRIPT}/teste_failover.sh" "$URL" 0.5 3600 > "$FAILOVER" 2>&1 &
PID_MEDIDOR=$!
trap 'kill "$PID_MEDIDOR" 2>/dev/null || true' EXIT
registrar "INÍCIO do teste. Medindo ${URL} a cada 0,5 s (PID ${PID_MEDIDOR})."
echo "Acompanhe em outro terminal:  tail -f ${FAILOVER}"

passo "1. Sistema funcionando e /saude alternando" \
      "Mostre o site aberto em https://192.168.56.10 e o failover.log alternando app1/app2." \
      "(vm-proxy) sudo tail -f /var/log/nginx/etermory_access.log"

passo "2A. Derrubar a app1 pelo serviço" \
      "(vm-app1) sudo systemctl stop etermory" \
      "Espere ~20 s olhando o failover.log: só app2 deve responder, sem FALHA."

passo "3A. Site funcionando pela app2 + erro registrado no Nginx" \
      "Navegue no site: login, timeline, curtir, publicar." \
      "(vm-proxy) sudo grep 192.168.56.11 /var/log/nginx/etermory_error.log | tail -5" \
      "(vm-proxy) etermory-healthcheck   # esperado: FALHA vm-app1, OK site, código 1"

passo "4A. Religar a app1 e ver ela voltar ao balanceamento" \
      "(vm-app1) sudo systemctl start etermory" \
      "Espere até 15 s (fail_timeout): app1 volta a aparecer no failover.log."

passo "2B. Derrubar a VM app1 inteira (desligamento abrupto)" \
      "No hospedeiro:  VBoxManage controlvm vm-app1 poweroff" \
      "(ou VirtualBox > vm-app1 > Fechar > Desligar a máquina)" \
      "Observe respostas 'lentas (failover)' de ~2 s a cada ~15 s, e nenhuma FALHA."

passo "3B. Site funcionando pela app2 com a VM app1 desligada" \
      "Navegue no site e confira o erro 'connect() failed' ou 'upstream timed out' no error.log."

passo "4B. Ligar a VM app1 de novo" \
      "No hospedeiro:  VBoxManage startvm vm-app1 --type headless" \
      "O serviço sobe sozinho (systemctl enable). app1 volta ao failover.log."

passo "5. Simular perda de dados e restaurar o backup" \
      "(vm-db) sudo -u postgres psql etermory -c 'SELECT count(*) FROM polaroids;'   # anote" \
      "(vm-db) sudo systemctl start etermory-backup.service && sudo tail -3 /var/log/etermory/backup.log" \
      "(vm-db) sudo -u postgres psql etermory -c 'DELETE FROM polaroids;'   # timeline vazia" \
      "(vm-app1 e vm-app2) sudo systemctl stop etermory" \
      "(vm-db) sudo ls /srv/backups/etermory/db/   # pegue a DATA do backup mais novo" \
      "(vm-db) sudo etermory-restore --confirmar DATA" \
      "(vm-app1 e vm-app2) sudo systemctl start etermory" \
      "(vm-db) conte as Polaroids de novo: deve bater com o número anotado."

registrar "FIM do teste."
kill "$PID_MEDIDOR" 2>/dev/null || true
wait "$PID_MEDIDOR" 2>/dev/null || true

echo
echo "Resumo do medidor (failover.log):"
total=$(grep -cE '  (OK|FALHA) ' "$FAILOVER" || true)
falhas=$(grep -c '  FALHA ' "$FAILOVER" || true)
lentas=$(grep -c 'lenta (failover)' "$FAILOVER" || true)
echo "  pedidos: ${total}   falhas: ${falhas}   lentas: ${lentas}"
if (( falhas > 0 )); then
    echo "  primeira falha: $(grep '  FALHA ' "$FAILOVER" | head -1 | cut -c1-12)"
    echo "  última falha:   $(grep '  FALHA ' "$FAILOVER" | tail -1 | cut -c1-12)"
    echo "  (as falhas do passo 5 são esperadas: as apps foram paradas para restaurar)"
fi
echo
echo "Evidências salvas em: ${PASTA}"
