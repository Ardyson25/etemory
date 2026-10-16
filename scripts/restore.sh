#!/usr/bin/env bash
# Restaura um backup do Etermory (banco e, opcionalmente, fotos) e mede o tempo.
# Onde roda: vm-db, como root.
#
# Uso:
#   sudo /usr/local/sbin/etermory-restore --confirmar DATA
#   DATA é o carimbo do backup, ex.: 2026-11-20_0200
#   (procura db/etermory_DATA.dump e fotos/fotos_DATA.tar.gz em /srv/backups/etermory)
#
# Antes de restaurar, pare as aplicações para ninguém gravar no meio:
#   (vm-app1 e vm-app2) sudo systemctl stop etermory
#
# Códigos de saída:
#   0 = sucesso
#   1 = uso incorreto ou não é root
#   2 = arquivo de backup não encontrado
#   3 = soma de verificação não confere (backup corrompido)
#   4 = falha ao restaurar o banco
#   5 = falha ao restaurar as fotos
set -euo pipefail
# shellcheck source=SCRIPTDIR/lib.sh
source "$(dirname "$(readlink -f "$0")")/lib.sh"
ARQUIVO_LOG="${PASTA_LOG}/restore.log"

BANCO="etermory"
ORIGEM="/srv/backups/etermory"
PASTA_FOTOS="/srv/etermory-uploads"

exigir_root
[[ "${1:-}" == "--confirmar" && -n "${2:-}" ]] \
    || falhar 1 "Uso: $0 --confirmar DATA   (ex.: 2026-11-20_0200). ATENÇÃO: substitui os dados atuais."
data="$2"

dump="${ORIGEM}/db/${BANCO}_${data}.dump"
fotos="${ORIGEM}/fotos/fotos_${data}.tar.gz"
somas="${ORIGEM}/sha256_${data}.txt"

[[ -f "$dump" ]] || falhar 2 "dump não encontrado: ${dump}"

inicio=$(date +%s)
log INFO "Início da restauração do backup ${data}"

# 1. Integridade
if [[ -f "$somas" ]]; then
    (cd "$ORIGEM" && sha256sum --check --quiet "$somas") \
        || falhar 3 "soma de verificação não confere: backup corrompido"
    log INFO "Somas de verificação conferidas"
else
    log AVISO "sem arquivo de somas (${somas}); seguindo sem conferir"
fi

# 2. Banco: --clean apaga e recria cada objeto do dump
runuser -u postgres -- pg_restore --clean --if-exists --exit-on-error -d "$BANCO" "$dump" \
    || falhar 4 "pg_restore falhou"
log INFO "Banco restaurado a partir de ${dump}"

# 3. Fotos: extrai numa pasta temporária e sincroniza (mantém dono e permissões)
if [[ -f "$fotos" ]]; then
    temporaria=$(mktemp -d)
    trap 'rm -rf "$temporaria"' EXIT
    tar -xzf "$fotos" -C "$temporaria" || falhar 5 "falha ao extrair ${fotos}"
    rsync -a --delete "${temporaria}/$(basename "$PASTA_FOTOS")/" "${PASTA_FOTOS}/" \
        || falhar 5 "falha ao copiar as fotos para ${PASTA_FOTOS}"
    log INFO "Fotos restauradas ($(find "$PASTA_FOTOS" -type f | wc -l) arquivo(s))"
else
    log AVISO "sem arquivo de fotos para ${data}; só o banco foi restaurado"
fi

duracao=$(( $(date +%s) - inicio ))
log INFO "Restauração concluída em ${duracao}s. Suba as aplicações: sudo systemctl start etermory"
