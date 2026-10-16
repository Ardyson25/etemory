#!/usr/bin/env bash
# Funções comuns aos scripts do Etermory. Uso: source "$(dirname "$0")/lib.sh"

# Pasta de log padrão; cada script define ARQUIVO_LOG antes de usar log().
PASTA_LOG="${PASTA_LOG:-/var/log/etermory}"

# Escreve "data [nível] mensagem" na tela e no arquivo de log do script.
log() {
    local nivel="$1"; shift
    local linha
    linha="$(date '+%Y-%m-%d %H:%M:%S') [$nivel] $*"
    echo "$linha"
    if [[ -n "${ARQUIVO_LOG:-}" ]]; then
        echo "$linha" >> "$ARQUIVO_LOG" 2>/dev/null || true
    fi
}

# Encerra com mensagem de erro e o código de saída informado.
falhar() {
    local codigo="$1"; shift
    log ERRO "$*"
    exit "$codigo"
}

exigir_root() {
    [[ "$(id -u)" -eq 0 ]] || falhar 1 "Rode como root (sudo $0 ...)."
}

# Espera a URL responder "status": "ok" por até N segundos.
esperar_saude() {
    local url="$1" limite="${2:-30}" inicio
    inicio=$(date +%s)
    while (( $(date +%s) - inicio < limite )); do
        if curl -fsS -m 2 "$url" 2>/dev/null | grep -q '"status": *"ok"'; then
            return 0
        fi
        sleep 1
    done
    return 1
}
