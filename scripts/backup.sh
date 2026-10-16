#!/usr/bin/env bash
# Backup diário do Etermory: banco (pg_dump) + fotos (tar.gz), 7 dias de
# retenção e cópia para outra máquina (vm-proxy).
# Onde roda: vm-db, como root, pelo etermory-backup.timer (02:00) ou à mão:
#   sudo /usr/local/sbin/etermory-backup
#
# Códigos de saída:
#   0 = sucesso
#   1 = não está rodando como root
#   2 = falha no pg_dump ou dump inválido
#   3 = falha ao compactar as fotos
#   4 = backup local OK, mas a cópia para a outra máquina falhou
set -euo pipefail
# shellcheck source=SCRIPTDIR/lib.sh
source "$(dirname "$(readlink -f "$0")")/lib.sh"
ARQUIVO_LOG="${PASTA_LOG}/backup.log"

BANCO="etermory"
PASTA_FOTOS="/srv/etermory-uploads"
DESTINO="/srv/backups/etermory"
RETENCAO_DIAS=7
COPIA_REMOTA="deploy@vm-proxy:/srv/backups-remotos/etermory/"
CHAVE_SSH="/root/.ssh/id_backup"

exigir_root
umask 077   # backups legíveis só pelo root
mkdir -p "${DESTINO}/db" "${DESTINO}/fotos"

data=$(date +%Y-%m-%d_%H%M)
inicio=$(date +%s)
dump="${DESTINO}/db/${BANCO}_${data}.dump"
fotos="${DESTINO}/fotos/fotos_${data}.tar.gz"

log INFO "Início do backup ${data}"

# 1. Banco: formato custom (-Fc) é compactado e permite restaurar com pg_restore.
if ! runuser -u postgres -- pg_dump -Fc "$BANCO" > "$dump"; then
    rm -f "$dump"
    falhar 2 "pg_dump falhou"
fi
# Confere se o arquivo é um dump legível antes de considerar o backup bom.
runuser -u postgres -- pg_restore --list "$dump" > /dev/null \
    || falhar 2 "o dump gerado não é válido: ${dump}"
log INFO "Banco: ${dump} ($(du -h "$dump" | cut -f1))"

# 2. Fotos
tar -czf "$fotos" -C "$(dirname "$PASTA_FOTOS")" "$(basename "$PASTA_FOTOS")" \
    || falhar 3 "falha ao compactar ${PASTA_FOTOS}"
log INFO "Fotos: ${fotos} ($(du -h "$fotos" | cut -f1))"

# 3. Somas de verificação (o restore.sh confere antes de restaurar)
(cd "$DESTINO" && sha256sum "db/$(basename "$dump")" "fotos/$(basename "$fotos")" \
    > "sha256_${data}.txt")

# 4. Retenção: apaga o que tiver mais de 7 dias
removidos=$(find "$DESTINO" -type f -mtime +"$RETENCAO_DIAS" -print -delete | wc -l)
log INFO "Retenção: ${removidos} arquivo(s) com mais de ${RETENCAO_DIAS} dias removido(s)"

duracao=$(( $(date +%s) - inicio ))

# 5. Cópia em outra máquina (espelho: a retenção vale lá também)
if rsync -a --delete -e "ssh -i ${CHAVE_SSH} -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
        "${DESTINO}/" "$COPIA_REMOTA"; then
    log INFO "Cópia remota OK em ${COPIA_REMOTA}"
else
    falhar 4 "backup local OK (${duracao}s), mas a cópia para ${COPIA_REMOTA} falhou"
fi

log INFO "Backup concluído em $(( $(date +%s) - inicio ))s"
