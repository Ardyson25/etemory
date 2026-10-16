#!/usr/bin/env bash
# Chama /saude pelo Nginx em sequência e mostra qual instância respondeu e em
# quanto tempo. Usado no teste de indisponibilidade (Fase 5).
#
# Onde roda: no computador hospedeiro (Git Bash) ou em qualquer VM.
# Uso: ./teste_failover.sh [url] [intervalo_em_segundos] [duração_em_segundos]
#   ./teste_failover.sh http://192.168.56.10/saude 0.5 120 | tee failover.log
#
# Como ler: "OK app2 2.013s" = respondeu, mas demorou porque o Nginx esperou
# a app1 (desligada) por até 2 s antes de repassar o pedido. "FALHA" = o
# usuário teria visto erro: isso é indisponibilidade de verdade.
set -euo pipefail

URL="${1:-http://192.168.56.10/saude}"
INTERVALO="${2:-0.5}"
DURACAO="${3:-120}"

inicio=$(date +%s)
total=0
falhas=0
lentas=0
primeira_falha=""
ultima_falha=""
declare -A por_instancia=()

echo "Testando ${URL} a cada ${INTERVALO}s por ${DURACAO}s (Ctrl+C para parar)"
while (( $(date +%s) - inicio < DURACAO )); do
    agora=$(date '+%H:%M:%S.%3N')
    total=$((total + 1))
    if resposta=$(curl -fsS -m 5 -w ' %{time_total}' "$URL" 2>/dev/null); then
        tempo="${resposta##* }"
        instancia=$(echo "$resposta" | sed -n 's/.*"instancia": *"\([^"]*\)".*/\1/p')
        por_instancia[$instancia]=$(( ${por_instancia[$instancia]:-0} + 1 ))
        marca=""
        if [[ "${tempo%%.*}" -ge 1 ]]; then
            lentas=$((lentas + 1))
            marca="  <- lenta (failover)"
        fi
        echo "${agora}  OK     ${instancia}  ${tempo}s${marca}"
    else
        falhas=$((falhas + 1))
        [[ -z "$primeira_falha" ]] && primeira_falha="$agora"
        ultima_falha="$agora"
        echo "${agora}  FALHA  sem resposta"
    fi
    sleep "$INTERVALO"
done

echo
echo "Resumo: ${total} pedidos, ${falhas} falha(s), ${lentas} resposta(s) lenta(s) (>= 1 s)."
for instancia in "${!por_instancia[@]}"; do
    echo "  ${instancia}: ${por_instancia[$instancia]} resposta(s)"
done
if (( falhas > 0 )); then
    echo "  Falhas entre ${primeira_falha} e ${ultima_falha}"
fi
